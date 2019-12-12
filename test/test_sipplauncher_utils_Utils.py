#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pytest
import tempfile
import sys
import os
import shutil

import sipplauncher.utils.Utils

# File system - 1
fs1 = {
    'sipplauncher_folder_resources': {
        'sipplauncher_folder_test': {
            'sipplauncher_file_1': None,
            'sipplauncher_file_2': None,
            'sipplauncher_file_3': None,
            'sipplauncher_folder_1': {
                'sipplauncher_file_4': None,
                'sipplauncher_file_5': None,
                'sipplauncher_file_6': None
            },
            'sipplauncher_folder_2': {
                'sipplauncher_file_7': None,
                'sipplauncher_file_8': None
            },
            'sipplauncher_folder_4': {}
        }
    }
}


@pytest.mark.parametrize(
    "mock_fs,dest,walkable,level,expected", [

        # Test
        (
            fs1,
            os.path.join(sys.prefix, 'usr', 'local'),
            os.path.join('sipplauncher_folder_resources', 'sipplauncher_folder_test'),
            0,
            [
                (
                    os.path.join(sys.prefix,
                                 'usr',
                                 'local',
                                 'sipplauncher_folder_resources',
                                 'sipplauncher_folder_test'),
                    [os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_file_1'),
                     os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_file_2'),
                     os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_file_3')]
                ),
                (
                    os.path.join(sys.prefix,
                                 'usr',
                                 'local',
                                 'sipplauncher_folder_resources',
                                 'sipplauncher_folder_test',
                                 'sipplauncher_folder_1'),
                    [os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_folder_1',
                                  'sipplauncher_file_4'),
                     os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_folder_1',
                                  'sipplauncher_file_5'),
                     os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_folder_1',
                                  'sipplauncher_file_6')]
                ),
                (
                    os.path.join(sys.prefix,
                                 'usr',
                                 'local',
                                 'sipplauncher_folder_resources',
                                 'sipplauncher_folder_test',
                                 'sipplauncher_folder_2'),
                    [os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_folder_2',
                                  'sipplauncher_file_7'),
                     os.path.join('sipplauncher_folder_resources',
                                  'sipplauncher_folder_test',
                                  'sipplauncher_folder_2',
                                  'sipplauncher_file_8')]
                ),
                (
                    os.path.join(sys.prefix,
                                 'usr',
                                 'local',
                                 'sipplauncher_folder_resources',
                                 'sipplauncher_folder_test',
                                 'sipplauncher_folder_4'), []
                )
            ]
        )
    ]
)
def test_walk_folder_recur(mock_fs, dest, walkable, level, expected):
    """Testing over different walkable tests
    """

    dirpath = tempfile.mkdtemp(prefix="sipplauncher_folder_")
    sipplauncher.utils.Utils.gen_file_struct(dirpath, mock_fs)

    with sipplauncher.utils.Utils.cd(dirpath):
        ret = sipplauncher.utils.Utils.walk_folder_recur(dest, walkable, level=level)

        for r_item, e_item in zip(sorted(ret), sorted(expected)):
            r_tmp, r_tmp_list = r_item
            e_tmp, e_tmp_list = e_item
            assert r_tmp == e_tmp
            assert set(r_tmp_list) == set(e_tmp_list)

    shutil.rmtree(dirpath)


@pytest.mark.parametrize(
    "mock_fs", [
        (fs1)
    ]
)
def test_gen_file_struct(mock_fs):
    """
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_folder_")
    sipplauncher.utils.Utils.gen_file_struct(dirpath, mock_fs)
    assert sipplauncher.utils.Utils.check_file_struct(dirpath, mock_fs)
    shutil.rmtree(dirpath)


def test_check_file_struct():
    """Manually creating files/folders and setting the mock_fs
    properly so the function must trigger this is a valid existing
    file structure.
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_folder_")
    dirpath2 = tempfile.mkdtemp(dir=dirpath, prefix="sipplauncher_folder_")
    dirpath3 = tempfile.mkdtemp(dir=dirpath, prefix="sipplauncher_folder_")
    dirpath4 = tempfile.mkdtemp(dir=dirpath3, prefix="sipplauncher_folder_")
    dirpath5 = tempfile.mkdtemp(dir=dirpath3, prefix="sipplauncher_folder_")

    _, file1 = tempfile.mkstemp(dir=dirpath, prefix="sipplauncher_file_")
    _, file2 = tempfile.mkstemp(dir=dirpath, prefix="sipplauncher_file_")
    _, file3 = tempfile.mkstemp(dir=dirpath2, prefix="sipplauncher_file_")
    _, file4 = tempfile.mkstemp(dir=dirpath2, prefix="sipplauncher_file_")
    _, file5 = tempfile.mkstemp(dir=dirpath2, prefix="sipplauncher_file_")
    _, file6 = tempfile.mkstemp(dir=dirpath4, prefix="sipplauncher_file_")

    mock_fs_good = {
        dirpath: {
            file1: None,
            file2: None,
            dirpath2: {
                file3: None,
                file4: None,
                file5: None
            },
            dirpath3: {
                dirpath4: {
                    file6: None
                },
                dirpath5: {}
            }
        }
    }

    # Missing file noexists
    mock_fs_bad = {
        dirpath: {
            file1: None,
            file2: None,
            dirpath2: {
                file3: None,
                file4: None,
                file5: None,
                'noexists': None
            },
            dirpath3: {
                dirpath4: {
                    file6: None
                },
                dirpath5: {}
            }
        }
    }

    assert sipplauncher.utils.Utils.check_file_struct(dirpath, mock_fs_good)
    tmp = "sipplauncher.utils.Utils.check_file_struct(dirpath, %s)" % mock_fs_bad
    pytest.raises(Exception, tmp)

    shutil.rmtree(dirpath)
