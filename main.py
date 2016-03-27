import os
import tornado.httpserver
import tornado.ioloop
import tornado.web

import requests


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello world")


class OAuthHandler(tornado.web.RequestHandler):
    def get(self):
        # want: write:repo_hook read:repo_hook

        auth_url = ("https://github.com/login/oauth/authorize?client_id={}&"
                    "redirect_url={}&state=abcd"
                    "".format(client_id, tornado.escape.url_escape('https://conda-forge.github.io')))
        print(auth_url)
        self.redirect(auth_url)
        # Some more handling to get the token, which we would need to store in a database somewhere.


class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        token = os.environ('GH_TOKEN')
        headers = {'Authorization': 'token {}'.format(token)}

        url = 'https://api.github.com/repos/pelson/conda-linter-webservice/hooks'

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

 
class HookHandler(tornado.web.RequestHandler):
    def post(self):
        print(self.request)
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        if event == 'ping':
            self.write('pong')
        else:
            print('event', event)
        print('handle:', headers['X-GitHub-Event'])
        print(self.request.__dict__)
        print(self.request.arguments)


def main():
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/register", RegisterHandler),
        (r"/hook", HookHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
