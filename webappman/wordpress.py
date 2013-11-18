#coding: utf-8

from os import remove as rm
from os.path import basename, dirname, join as path_join, realpath, isdir

from osext.filesystem import rmdir_force, sync as dir_sync
import sysext.archive as ar
import httpext as http
import os
import langutil.php as php

class WordPressError(Exception):
    pass


class WordPressConfigError(WordPressError):
    pass


class WordPress:
    """For installing and managing WordPress sites"""
    LATEST_URI = 'http://wordpress.org/latest.zip'
    DL_FORMAT = 'http://wordpress.org/wordpress-%s.zip'

    _path = None
    _basename = None
    _dirname = None
    _is_initialized = False

    def __init__(self, path):
        """

        Args:
            path (str): Path to installation. Does not have to exist as
              init_dir() can be used to initialise a new installation.
        """
        self._path = realpath(path)
        self._basename = basename(path)
        self._dirname = dirname(path)
        self._is_initialized = isdir(self._path)

    def _diff_list(self, a, b):
        return filter(lambda x: x not in a, b)

    def init_dir(self, version='latest', config={}, table_prefix='wp_'):
        """Initialises a new WordPress installation.

        Kwargs:
            version (str): Version number or ``'latest'``.
            config (dict): Configuration. Must have keys ``'db_name'``,
                             ``'db_user'``, ``'db_password'`` at minimum.
            table_prefix (str): Table prefix.

        Raises:
            WordPressError, WordPressConfigError

        Optional ``config`` keys (all str):
            db_host: Database host.
            db_charset: Database character set (MySQL).
            db_collate: Database collation ('' for default).
            wplang: Language code.
            auth_key: Authentication key.
            secure_auth_key: Secure authentication key.
            logged_in_key: Logged in key.
            nonce_key: Nonce key.
        """

        if self._is_initialized:
            raise WordPressError('Directory %s already exists' % (self._path))

        uri = self.LATEST_URI
        cache = True

        if version != 'latest':
            uri = self.DL_FORMAT % (version)
            cache = False

        prev_listing = os.listdir('.')

        http.dl(uri, '_wp.zip', cache=cache)
        ar.unzip('_wp.zip')
        rm('_wp.zip')

        new_listing = os.listdir('.')
        diff = self._diff_list(prev_listing, new_listing)

        if len(diff) == 0:
            raise WordPressError('Directory listing not changed after unzip operation')

        dir_name = diff[0]
        os.rename(dir_name, self._path)

        defaults = {
            'db_host': 'localhost',
            'db_charset': 'utf8',
            'db_collate': '',
            'wplang': '',
            'auth_key': ',Qi8F3A:ME>+!G*|a!>zbW!GWe,A9rHR@tL.4sFCE}LR0][j/995U+4*3H:i]]DH',
            'secure_auth_key': 'UjN_-SP+Whq/^taB31&lg$fj0-<XSgKy@UzK*B-k-4aiT9~m^s_vT[dE,5P;kx(E',
            'logged_in_key': '2dfV^z4rJqrSEdQc.ec)KJC UZv$#)OhJKRY~Vj9+]M-]CIBL(RvGZ|[C!S|]MOv',
            'nonce_key': '.Ue WG1NN/cKo^MC53$_U0!V>Mtdw-ar$rP8o+;rawQ)B$9LlAAL<@GLoXS_POaa',
        }
        keys = [
            'db_name',
            'db_user',
            'db_password',
            'db_host',
            'db_collate',
            'db_charset',
            'auth_key',
            'secure_auth_key',
            'logged_in_key',
            'nonce_key',
            'wplang',
        ]

        line_format = 'define(%s, %s);'
        wp_config_php = ['<?php']

        for key in keys:
            if key in config:
                value = config[key]
            elif key in defaults:
                value = defaults[key]
            else:
                raise WordPressConfigError('Configuration key %s is required' % (key))

            wp_config_php.append(line_format % (php.generate_scalar(key.upper()), php.generate_scalar(value)))

        wp_config_php.append('$table_prefix = %s;' % (php.generate_scalar(table_prefix)))

        lines = '\n'.join(wp_config_php) + '\n'
        lines += '''if (!defined('ABSPATH'))
  define('ABSPATH', dirname(__FILE__) . '/');
require_once(ABSPATH . 'wp-settings.php');'''
        lines += '\n'

        with open(path_join(self._path, 'wp-config.php'), 'wb+') as f:
            f.write(lines)

        os.remove(path_join(self._path, 'wp-config-sample.php'))

    def sync_assets(self, remote_path):
        raise Exception('Not implemented')
