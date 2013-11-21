from distutils.core import setup

setup(
    name='WebAppManager',
    version='0.1.5',
    author='Andrew Udvare',
    author_email='audvare@gmail.com',
    packages=['webappman'],
    url='https://github.com/Appdynamics/python-webappman',
    license='LICENSE.txt',
    description='Management of common web apps (Drupal, WordPress).',
    long_description=open('README.rst').read(),
    scripts=['bin/wam-install-drupal', 'bin/wam-install-wordpress'],
)
