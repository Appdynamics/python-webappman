from distutils.core import setup

setup(
    name='WebAppManager',
    version='0.2.5',
    author='Andrew Udvare',
    author_email='audvare@gmail.com',
    packages=['webappman'],
    url='https://github.com/Appdynamics/python-webappman',
    license='LICENSE.txt',
    description='Management of common web apps (Drupal, WordPress).',
    long_description=open('README.rst').read(),
    scripts=['bin/wam-install-drupal', 'bin/wam-install-wordpress'],
    install_requires=[
        'beautifulsoup4==4.3.2',
        'httpext>=0.1.3',
        'langutil>=0.1.4',
        'osextension>=0.1.2',
        'sh==1.09',
    ],
)
