#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import fcntl
import termios
import struct
import string
import random

def which(program):
    # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def my_read_file(f_name):
    """ DRY helper """
    ret = None
    with open(f_name, "r") as fh:
        ret = fh.read()
    return ret


def indent(lines, amount=4, ch=' '):
    """ From http://stackoverflow.com/
    8234274/how-to-indent-the-content-of-a-string-in-python
    """
    padding = amount * ch
    return padding + ('\n' + padding).join(lines.split('\n'))


def any2bool(s):
    """ Detects any truth in the given str
    """
    true_list = ['true', '1', 't', 'y', 'yes', True, 'True', 1]
    return s in true_list


def overrides(interface_class):
    """Decorator to make sure the method is overriding
    a valid method from its super cls.
    """

    def overrider(method):
        assert (method.__name__ in dir(interface_class))
        return method

    return overrider


def walk_folder_recur(dest, walkable, level=0):
    """ Walks through @walkable and generates
    a list of tuples (folder, [files in folder])
    for all the folders found in the walkable.
    The @dest prefix is attached to every folder.

    :param dest: Path of a valid prefix
    :type state: str

    :param walkable:: Path to the walkable folder
    :type state: str

    :param level: Number of root levels to crop
                  from the walkable dirfolder when
                  joining to the dest.
    :type level: int
    :default level: 0

    :returns: [(str, [str])]
    :raises: TypeError

    Example1:
    - dest: '/usr/local/'
    - walkable: 'resources/test/'
    - level: 0
    - returns:
    | [
    |    ('/usr/local/resources/test/',
    |        [
    |            'resources/test/file1.txt',
    |            'resources/test/file2.txt'
    |        ]
    |    ),
    |    ('/usr/local/resources/test/subtest',
    |        [
    |            'resources/test/subtest/file1.txt',
    |            'resources/test/subtest/file2.txt'
    |        ]
    |    ),
    | ]

    Example2:
    - dest: '/usr/local/'
    - walkable: 'resources/test/'
    - level: 1
    - returns:
    | [
    |    ('/usr/local/test/',
    |        [
    |            'resources/test/file1.txt',
    |            'resources/test/file2.txt'
    |        ]
    |    ),
    |    ('/usr/local/test/subtest',
    |        [
    |            'resources/test/subtest/file1.txt',
    |            'resources/test/subtest/file2.txt'
    |        ]
    |    ),
    | ]

    """

    ret = []

    for dirpath, _, filenames in os.walk(walkable):
        tmp = []

        # Grab all the files from the folder
        for f in filenames:
            tmp.append(os.path.join(dirpath, f))

        try:
            dirpath_tmp = os.path.join(*dirpath.split(os.sep)[level:])
            to = os.path.join(dest, dirpath_tmp)
        except Exception as msg:
            dirpath_tmp = None
            to = dest
        finally:
            ret.append((to, tmp))

    return ret


def gen_file_struct(fs_path, root):
    """Generates a file structure from a Python dict (keys are files
    if the value is str or None, they are folder if the value is dict
    @p_folder).
    """
    for k, v in iter(root.items()):
        tmp_fs_path = os.path.join(fs_path, k)
        if os.path.exists(tmp_fs_path):
            msg = 'Already exists: %s' % tmp_fs_path
            raise Exception(msg)
        elif isinstance(v, dict):
            os.makedirs(tmp_fs_path)
            # Recurse into subfolder
            gen_file_struct(tmp_fs_path, v)
        elif isinstance(v, str) or v == None:
            with open(tmp_fs_path, 'w+') as f:
                if v:
                    f.write(v)
        else:
            raise Exception(str(v) + " is neither dict(folder) nor str/None(file)")

def check_file_struct(fs_path, root):
    """Checks the existance of a file structure in disk, the file
    structure definition is given by a Python dict (keys are files
    if the value is str or None, they are folder if the value is dict).
    """

    for k, v in iter(root.items()):
        tmp_fs_path = os.path.join(fs_path, k)
        if not os.path.exists(tmp_fs_path):
            raise Exception('Not found: %s' % tmp_fs_path)
        elif os.path.isfile(tmp_fs_path) and not (isinstance(v, str) or v == None):
            raise Exception('Found a file instead of folder: %s' %
                            tmp_fs_path)
        elif os.path.isdir(tmp_fs_path) and not isinstance(v, dict):
            raise Exception('Found a folder instead of a file: %s' %
                            tmp_fs_path)
        elif isinstance(v, dict):
            # Recurse into subfolder
            check_file_struct(tmp_fs_path, v)

    return True


def get_terminal_size():
    """ Returns the terminal size, modified from
    http://stackoverflow.com/a/3010495/851428

    :returns: (int, int)
    """
    # Defaults
    w, h = 70, 30
    try:
        h, w, hp, wp = \
            struct.unpack('HHHH',
                          fcntl.ioctl(0,
                                      termios.TIOCGWINSZ,
                                      struct.pack('HHHH',
                                                  0,
                                                  0,
                                                  0,
                                                  0)))
    except:
        pass
    return w, h


def generate_id(n=10, just_digits=False, just_letters=False):
    if just_digits:
        pool = string.digits
    elif just_letters:
        pool = string.ascii_lowercase
    else:
        pool = string.ascii_lowercase + string.digits
    tmp = ''.join(random.choice(pool) for x in range(n))
    return tmp


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def is_tls_transport(transport):
    return transport in ["l1", "ln"]
