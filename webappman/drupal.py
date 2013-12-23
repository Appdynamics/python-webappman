#coding: utf-8
"""For Drupal site deployment and management"""

from os import remove as rm
from os.path import isdir, join as path_join, realpath, basename
from pipes import quote as shell_quote
from sh import tar, unzip
from shlex import split as shell_split
from shutil import copy2 as copy_file, rmtree as rmdir_force
import json
import os
import re
import subprocess as sp

from osext.filesystem import sync as dir_sync, isfile
from osext.pushdcontext import pushd
import httpext as http
import langutil.php as php

CKEDITOR_URI = 'http://download.cksource.com/CKEditor/CKEditor/' + \
    'CKEditor%203.6.6.1/ckeditor_3.6.6.1.tar.gz'
FANCYBOX_URI = 'https://github.com/fancyapps/fancyBox/zipball/v2.1.5'
JQ_COLOR_PICKER_URI = 'http://www.eyecon.ro/colorpicker/colorpicker.zip'
JQ_CYCLE_URI = 'http://malsup.github.com/jquery.cycle.all.js'
PREDIS_URI = 'https://github.com/nrk/predis/zipball/v0.8.4'
SIMPLEPIE_URI = 'http://simplepie.org/downloads/simplepie_1.3.1.compiled.php'


def _install_ckeditor(stdout=None):
    """Callback to install necessary library for the IMCE module"""
    arg = 'xf'

    if stdout:
        arg += 'v'

    http.dl(CKEDITOR_URI, 'ckeditor.tar.gz')
    output = tar('xf', 'ckeditor.tar.gz')

    if stdout and output:
        stdout.write(str(output).strip() + '\n')

    rm('ckeditor.tar.gz')


def _install_jquery_colorpicker(stdout=None):
    """Callback to install necessary library for the module"""
    os.makedirs('./colorpicker')
    http.dl(JQ_COLOR_PICKER_URI, './colorpicker/colorpicker.zip')
    with pushd('./colorpicker'):
        output = unzip('colorpicker.zip')

        if stdout and output:
            stdout.write(str(output).strip() + '\n')

        rm('colorpicker.zip')


def _install_fancybox(stdout=None):
    """Callback to install necessary library for the Fancybox module"""
    http.dl(FANCYBOX_URI, 'fancybox.zip')
    output = unzip('fancybox.zip')

    if stdout and output:
        stdout.write(str(output).strip() + '\n')

    os.rename('fancyapps-fancyBox-18d1712', 'fancybox')
    rm('fancybox.zip')


def _install_jquery_cycle(stdout=None):
    """Callback to install necessary library for the Views Cycle module"""
    os.makedirs('./jquery.cycle')
    http.dl(JQ_CYCLE_URI, './jquery.cycle/jquery.cycle.all.js')


def _install_predis(stdout=None):
    """Callback to install Predis for the Redis module"""
    http.dl(PREDIS_URI, 'predis.zip')
    output = unzip('predis.zip')

    if stdout and output:
        stdout.write(str(output).strip() + '\n')

    os.rename('nrk-predis-d02e2e1', 'predis')
    rm('predis.zip')


def _install_simplepie(stdout=None):
    """Callback to install necessary file for the Simplepie module"""
    target = realpath(path_join(os.getcwd(), '..', 'modules', 'contrib',
                                'feeds', 'libraries',
                                'simplepie.compiled.php'))
    http.dl(SIMPLEPIE_URI, target)


# All callbacks must have stdout=None as the signature
_lib_hooks = {
    'ckeditor': _install_ckeditor,
    'colorpicker': _install_jquery_colorpicker,
    'fancybox': _install_fancybox,
    'jquery.cycle': _install_jquery_cycle,
    'predis': _install_predis,
    'simplepie': _install_simplepie,
}


class DrushError(Exception):
    pass


class DrupalError(Exception):
    pass


class Drush:
    """Interface to Drush from Python"""
    _path = None
    _verbose = False
    _stdout = None
    _uris = []

    def __init__(self, path, verbose=False, stdout=None):
        """

        Arguments:
        path -- Path to target Drupal installation. Does not have to exist as
                  init_dir() can be used to initialise

        Keyword Arguments:
        verbose -- If verbose mode should be used with the drush command.
        stdout  -- Where standard output should be written to. None for
                    current terminal.
        """
        self._path = realpath(path)
        self._verbose = verbose
        self._stdout = stdout

        if isdir(self._path) and isdir(path_join(self._path, 'sites')):
            with pushd(self._path):
                site_dirs = [x
                            for x in os.listdir('sites')
                            if isdir(os.path.join('sites', x)) and
                            x not in ['all', 'default']]
                for item in site_dirs:
                    self._uris.append('http://%s' % (item))

                self._uris.sort()

    def command(self, string_as_is, ignore_errors=False):
        """Runs a drush command string. If the class is not in verbose mode,
            -q argument will be added
           ignore_errors may want to be used for commands that exit with
             non-zero status but are not always errors (like reverting a view
             that may not exist)

        command('en -y module_name')
        command('views-revert my_nonexisting_view', ignore_errors=True)
        """
        with pushd(self._path):
            split = shell_split(string_as_is)
            command_line = ['drush']

            if not self._verbose:
                command_line.append('-q')

            command_line.extend(split)
            if self._verbose and self._stdout:
                self._stdout.write(' '.join(command_line) + '\n')

            try:
                sp.check_call(command_line, stdout=self._stdout)
            except sp.CalledProcessError as e:
                if not ignore_errors:
                    raise e

            for uri in self._uris:
                if re.match(r'^https?\://default$', uri):
                    continue

                command_line = ['drush', '--uri=%s' % (uri)]

                if not self._verbose:
                    command_line.append('-q')

                command_line.extend(split)

                if self._verbose and self._stdout:
                    self._stdout.write(' '.join(command_line) + '\n')

                try:
                    sp.check_call(command_line, stdout=self._stdout)
                except sp.CalledProcessError as e:
                    if not ignore_errors:
                        raise e

    def add_uri(self, uri):
        if uri in self._uris:
            return

        self._uris.append(uri)

    def init_dir(self, major_version=7, minor_version=24, cache=True):
        """Initialises a Drupal root with a version specified.

        Kwargs:
            ``major_version`` (int): major version of Drupal\n
            ``minor_version`` (int): minor version of Drupal\n
            cache (bool): if Drush's cache should be used
        """
        with pushd(realpath(path_join(self._path, '..'))):
            module_name = 'drupal-%d.%s' % (major_version, minor_version)
            dir_name = module_name

            if minor_version == 'x':
                dir_name += '-dev'

            if isdir(dir_name):
                rmdir_force(dir_name)

            command_line = ['drush', 'dl', '-y']

            if cache:
                command_line.append('--cache')

            if not self._verbose:
                command_line.append('-q')

            command_line.append(module_name)

            sp.check_call(command_line)

            if not isdir(dir_name):
                raise Exception('Failed to download Drupal 7.x correctly')

            os.rename(dir_name, self._path)

            with pushd(self._path):
                os.makedirs('./sites/all/modules/contrib')
                os.makedirs('./sites/all/themes/contrib')

            os.makedirs(path_join(self._path, 'sites', 'default', 'files',
                                  'tmp'),
                        0770)

    def create_libraries_dir(self):
        """Creates the sites/all/libraries directory. Root path must exist."""
        path = path_join(self._path, 'sites', 'all', 'libraries')

        if isdir(path):
            return

        os.makedirs(path_join(self._path, 'sites', 'all', 'libraries'))

    def _handle_dl(self, command_line):
        try:
            sp.check_call(command_line)
        except sp.CalledProcessError as e:
            # Most of the time this is caused by a bad checksum
            if ignore_errors:
                pass

            raise DrushError('Non-zero status %d. Run in verbose mode and'
                                'check output for [error] line' %
                                (e.returncode))

    def dl(self, module_names, cache=True, ignore_errors=False):
        """Downloads modules.

        Arguments:
        module_names -- str or list, a module name or a list of module names

        Keyword Arguments:
        cache         -- boolean, if Drush's cache should be used
        ignore_errors -- boolean, ignore hash errors

        Raises DrushError if an error occurs when downloading, unless
          ignore_errors is True.
        """
        if type(module_names) is str:
            module_names = shell_split(module_names)

        command_line = ['drush', 'dl', '-y']

        if cache:
            command_line.append('--cache')

        if not self._verbose:
            command_line.append('-q')

        command_line.extend(module_names)

        dir_exceptions = [
            'registry_rebuild',
        ]

        if len(module_names) == 1 and module_names[0].lower() in dir_exceptions:
            return self._handle_dl(command_line)

        with pushd(self._path):
            self._handle_dl(command_line)

    def rr(self):
        """Rebuild registry front-end method."""
        return self.command('rr')

    def cc(self, which='all'):
        """Cache-clear front-end method.

        :param which: Type of cache to clear.
        :type which: ``str``.
        :returns: ``int`` -- the return code.
        """
        return self.command('cc %s' % (which))

    def vset(self, variable_name, value):
        """Variable set front-end method. If the type of the value is str,
             then --format=string will be used. Otherwise the value will be
             converted to json and --format=json will be used.

        Arguments:
        variable_name -- str, variable name to set
        value         -- Any type that is JSON-encodable or str.
        """
        if type(value) is str:
            format = 'string'
        else:
            format = 'json'
            value = json.dumps(value)

        args = (format, shell_quote(variable_name), shell_quote(value))

        return self.command('vset --exact -y --format=%s %s %s' % args)

    def vset_many(self, dict_of_vars, mysql_connection):
        """Set many variables at once using a MySQL connection object and a
             dictionary of values. Use this instead of vset() when many values
             need to be set quickly.

        Arguments:
        dict_of_vars     -- dict, dictionary of variables to values to set
        mysql_connection -- MySQLdb.connection, open connection to MySQL to
                            correct Drupal database
        """
        c = mysql_connection.cursor()

        for (key, value) in dict_of_vars.items():
            value = php.serialize(value)
            c.execute('INSERT INTO variable (name, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value=%s', args=(key, value, value,))

        mysql_connection.commit()


    def updb(self):
        """Update database front-end method. Use with caution."""
        return self.command('updb -y')

    def en(self, module_name):
        """Enable module front-end method.

        Arguments:
        module_name -- str, system module name
        """
        return self.command('en -y %s' % (module_name))

    def dis(self, module_name):
        """Disable module front-end method.

        Arguments:
        module_name -- str, system module name
        """
        self.command('dis -y %s' % (module_name))

    def install_lib(self, library_name, stdout=None):
        """Installs a library into sites/all/libraries (usually).

        Arguments:
        library_name -- library name, must be registerd as a hook in
          _lib_hooks. This name is also the same as the directory name in
          sites/all/libraries.

        Keyword Arguments:
        stdout -- None or file handle
        """
        self.create_libraries_dir()

        with pushd(path_join(self._path, 'sites', 'all', 'libraries')):
            # library_name is also supposed to be the directory target
            if isdir(library_name):
                rmdir_force(library_name)
            _lib_hooks[library_name](stdout=stdout)

    def fix_registry_table(self,
                           connection,
                           search='sites/all/modules',
                           replace='sites/all/modules/contrib',
                           like='sites/all/modules/%',
                           not_like='%/contrib%'):
        """Not intended for general use, but called with default arguments this
             method fixes an older database that may have modules' registered
             files with paths at sites/all/modules instead of the more proper
             path sites/all/modules/contrib.

        Arguments:
        connection -- MySQLdb connection object

        Keyword Arguments:
        search  -- str, path to search for
        replace -- str, replacement string
        like    -- str, filter
        """
        c = connection.cursor()

        args = (
            search,
            replace,
            like,
            not_like,
        )
        c.execute('UPDATE registry SET filename = REPLACE(filename, %s, %s)'
                  'WHERE filename LIKE %s AND filename NOT LIKE %s', args=args)
        connection.commit()

        c.close()

    def sync_assets(self, remote_path, domain='default', local_domain=None):
        """Sync assets from a remote or local directory. This is intended to
          sync sites/all/default/files or sites/all/somedomain.com/files
          directories.

          Arguments:
          remote_path  -- str, remote path in SSH format or a local path
          domain       -- directory in sites to write to
          local_domain -- ???
        """
        if local_domain:
            domain_path = path_join(self._path, 'sites', local_domain, 'files')
        else:
            domain_path = path_join(self._path, 'sites', domain, 'files')

        if not isdir(domain_path):
            os.makedirs(domain_path)
            os.makedirs(path_join(domain_path, 'tmp'))

        with pushd(domain_path):
            dir_sync(remote_path, domain_path)

    def install_favicon(self, favicon_path):
        """Installs favicon into the root and at /misc/favicon.ico

        Arguments:
        favicon_path - Path to favicon.
        """
        favicon_filename = basename(favicon_path)
        paths = [
            path_join(self._path, favicon_filename),
            path_join(self._path, 'misc', favicon_filename),
        ]

        for target_path in paths:
            if isfile(target_path):
                os.remove(target_path)

            copy_file(favicon_path, target_path)

    def remove_extraneous_files(self):
        """Mainly for production. Removes junk files from the root. For the
             most part this should not be necessary as a server configuration
             on production should block access to *.txt, *.config by default
             anyway.
        """
        extra_files = [
            'CHANGELOG.txt',
            'COPYRIGHT.txt',
            'INSTALL.txt',
            'INSTALL.mysql.txt',
            'INSTALL.pgsql.txt',
            'INSTALL.sqlite.txt',
            'LICENSE.txt',
            'MAINTAINERS.txt',
            'README.txt',
            'UPGRADE.txt',
            'web.config',
        ]

        for file_name in extra_files:
            path = path_join(self._path, file_name)
            os.remove(path)


def is_production():
    """Based on DRUPAL_ENV environment variable, determines if the server is in
         production mode."""
    try:
        if os.environ['DRUPAL_ENV'] == 'prod':
            return True
    except KeyError:
        pass

    return False


def generate_settings_files(data):
    """Generates settings.php files

    Arguments:
    data -- Configuration hash. Each key in the hash is a domain. So there
              should be at least the 'default' key. From there are three
              hashes: databases, conf, ini_set.

    Example:
    data = {
        'default': {
            'databases': {
                'default': {
                    'database': 'my database',
                    ...
                },
            },
            'conf': {
                # Anything that goes in the $conf array
                '404_fast_paths_exclude': '/\/(?:styles)\//',
                'blocked_ips': [list of IPs],
            },

            # Do note any scalar value (non-array, non-object) can be used here
            #   and it will become a global variable as in this one:
            #     $drupal_hash_salt = 'salt string';
            'drupal_hash_salt': 'salt string',

            'ini_set': { # Any ini_set() directives
                'session.gc_probability': 1,
            }
        }
    }

    Returns a list of tuples: (path (str), data (PHP code, str))
    """
    if not 'default' in data:
        raise DrupalError('"default" key must exist')

    ret = []

    for site_name, settings in data.items():
        php_code = ''
        for key in ('databases', 'conf',):
            php_code += '$%s = %s\n' % (key, php.generate_array(settings[key]))

        for ini_name, ini_setting in settings['ini_set'].items():
            php_code += 'ini_set(%s, %s);\n' % (
                php.generate_scalar(ini_name),
                php.generate_scalar(ini_setting))

        for key, value in settings.items():
            if key in ('databases', 'conf', 'ini_set'):
                continue

            php_code += '$%s = %s;\n' % (key, php.generate_scalar(value))

        file_name = path_join('sites', site_name, 'settings.php')
        ret.append([file_name, php_code.strip()])

    return ret
