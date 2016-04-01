from __future__ import print_function
from collections import OrderedDict
from contextlib import contextmanager
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from conda_forge_webservices.linting import compute_lint_message


@contextmanager
def tmp_directory():
    tmp_dir = tempfile.mkdtemp('recipe_')
    yield tmp_dir
    shutil.rmtree(tmp_dir)


class Test_compute_lint_message(unittest.TestCase):
    def test_good_recipe(self):
        expected_message = textwrap.dedent("""
        Hi! This is the friendly conda-forge-admin automated user.
        
        I just wanted to let you know that I linted all conda-recipes in your PR (```good_recipe```) and found it was in an excellent condition.

        """)

        msg = compute_lint_message('conda-forge', 'conda-forge-linting-service', 4)
        self.assertMultiLineEqual(expected_message, msg)

    def test_bad_recipe(self):
        expected_message = textwrap.dedent("""
        Hi! This is the friendly conda-forge-admin automated user.
        
        I wanted to let you know that I linted all conda-recipes in your PR (```bad_recipes/bad_recipe```, ```good_recipe```) and found some lint.
        
        Here's what I've got...
        
        
        For **bad_recipes/bad_recipe**:
        
         * The home item is expected in the about section.
         * The license item is expected in the about section.
         * The summary item is expected in the about section.
         * The recipe could do with some maintainers listed in the "extra/recipe-maintainers" section.
         * The recipe must have some tests.
        """)

        msg = compute_lint_message('conda-forge', 'conda-forge-linting-service', 5)
        self.assertMultiLineEqual(expected_message, msg)

    def test_no_recipe(self):
        expected_message = textwrap.dedent("""
        Hi! This is the friendly conda-forge-admin automated user.

        I was trying to look for recipes to lint for you, but couldn't find any.
        Please ping the 'conda-forge/core' team (using the @ notation in a comment) if you believe this is a bug.
        """)

        msg = compute_lint_message('conda-forge', 'conda-forge-linting-service', 6)
        self.assertMultiLineEqual(expected_message, msg)


if __name__ == '__main__':
    unittest.main()
