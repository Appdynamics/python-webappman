from webappman import drupal
from osext import filesystem as fs
import os
import unittest

class TestFunctions(unittest.TestCase):
    def test_is_production_env(self):
        old_val = None

        try:
            old_val = os.environ['DRUPAL_ENV']
        except KeyError:
            pass

        os.environ['DRUPAL_ENV'] = 'prod'
        self.assertTrue(drupal.is_production())

        if old_val:
            os.environ['DRUPAL_ENV'] = old_val

    def test_is_production_file(self):
        info_file = './info_file'

        with open(info_file, 'w+') as f:
            f.write('prod\n')

        self.assertTrue(drupal.is_production(info_file=info_file))
        os.remove(info_file)
