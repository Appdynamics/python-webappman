from webappman.test import drupal
import unittest

suite = unittest.TestLoader().loadTestsFromModule(drupal)
unittest.TextTestRunner(verbosity=2).run(suite)
