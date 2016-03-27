# TODO: Add an interface to do this from the CLI:
# conda-linting-service conda-forge/staged-recipes 123

import os
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.web

import requests
import os
from glob import glob
import tempfile
from git import Repo
import textwrap
import github
import conda_smithy.lint_recipe
import shutil
from contextlib import contextmanager


class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        token = os.environ.get('GH_TOKEN')
        headers = {'Authorization': 'token {}'.format(token)}

        url = 'https://api.github.com/repos/conda-forge/staged-recipes/hooks'

        payload = {
              "name": "web",
              "active": True,
              "events": [
                "pull_request"
              ],
              "config": {
                "url": "http://conda-linter.herokuapp.com/hook",
                "content_type": "json"
              }
            }

        r = requests.post(url, json=payload, headers=headers)


@contextmanager
def tmp_directory():
    tmp_dir = tempfile.mkdtemp('recipe_')
    yield tmp_dir
    shutil.rmtree(tmp_dir)


class HookHandler(tornado.web.RequestHandler):
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        if event == 'ping':
            self.write('pong')
        elif event == 'pull_request':
            from pprint import pprint
            body = tornado.escape.json_decode(self.request.body)
            repo_name = body['repository']['name']
            repo_url = body['repository']['clone_url']
            owner = body['repository']['owner']['login']
            pr_id = body['pull_request']['number']
            open = body['pull_request']['state'] == 'open'

            # Only do anything if we are working with conda-forge, and an open PR.
            if open and owner == 'conda-forge':
                gh = github.Github(os.environ['GH_TOKEN'])

                owner = gh.get_user(owner)
                repo = owner.get_repo(repo_name)

                issue = repo.get_issue(pr_id)

                with tmp_directory() as tmp_dir:
                    repo = Repo.clone_from(repo_url, tmp_dir)
                    repo.remotes.origin.fetch('pull/{pr}/head:pr/{pr}'.format(pr=pr_id))
                    repo.refs['pr/{}'.format(pr_id)].checkout()
                    recipes = [y for x in os.walk(tmp_dir)
                               for y in glob(os.path.join(x[0], 'meta.yaml'))]
                    all_pass = True
                    messages = []
                    recipe_dirs = [os.path.dirname(recipe) for recipe in recipes
                                   if os.path.basename(os.path.dirname(recipe)) != 'example']
                    rel_recipe_dirs = []
                    for recipe_dir in recipe_dirs:
                        rel_path = os.path.relpath(recipe_dir, tmp_dir)
                        rel_recipe_dirs.append(rel_path)
                        lints = conda_smithy.lint_recipe.main(recipe_dir)
                        if lints:
                            all_pass = False
                            messages.append("\nFor **{}**:\n\n{}".format(rel_path,
                                                                         '\n'.join(' * {}'.format(lint) for lint in lints)))

                # Put the recipes in the form "```recipe/a```, ```recipe/b```".
                recipe_code_blocks = ', '.join('```{}```'.format(r) for r in rel_recipe_dirs)

                good = textwrap.dedent("""
                Hi! This is the friendly conda-forge-admin automated user.

                I just wanted to let you know that I linted all conda-recipes in your PR ({}) and found it was in an excellent condition.

                """.format(recipe_code_blocks))

                bad = textwrap.dedent("""
                Hi! This is the friendly conda-forge-admin automated user.

                I wanted to let you know that I linted all conda-recipes in your PR ({}) and found some lint.

                Here's what I've got...

                {}
                """.format(recipe_code_blocks, textwrap.indent('\n'.join(messages), '                ', lambda line: True)))

                if not recipe_dirs:
                    issue.create_comment(textwrap.dedent("""
                        Hi! This is the friendly conda-forge-admin automated user.
                        
                        I was trying to look for recipes to lint for you, but couldn't find any.
                        Please ping the 'conda-forge/core' team (using the @ notation in a comment) if you believe this is a bug.
                        """))
                elif all_pass:
                    issue.create_comment(good)
                else:
                    issue.create_comment(bad)

        else:
            print('Unhandled event "{}".'.format(event))
            self.write_error(404)


def main():
    application = tornado.web.Application([
        #(r"/register", RegisterHandler),
        (r"/hook", HookHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
