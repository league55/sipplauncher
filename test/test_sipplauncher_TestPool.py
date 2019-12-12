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
import argparse

import sipplauncher.utils.Utils
from sipplauncher.TestPool import TestPool
from sipplauncher.Test import SIPpTest

fs_valid_1 = {
    "folder_root": {
        "folder_0000": {
            "uac_ua0.xml": None,
            "dummy_ua0.xml": None,
        },
        "folder_0001": {
            "uac_ua0.xml": None,
            "uac_ua1.xml": None,
            "uac_ua2.xml": None,
        },
        "file_users.csv": None
    }
}

fs_valid_2 = {
    "folder_root": {
        "folder_0000": {
            "uas_ua0.xml": None,
            "dummy_ua0.xml": None,
        },
        "folder_0001": {
            "uac_ua0.xml": None,
            "uas_ua1.xml": None,
            "uas_ua2.xml": None,
        },
        "file_users.csv": None
    }
}

fs_invalid_1 = {
    "folder_root": {
        "folder_0000": {
            "uac_ua0.xml": None,
            "dummy_ua0.xml": None,
        },
        "folder_0001": { # folder with neither uas nor uac xml files
        },
        "file_users.csv": None
    }
}

fs_invalid_2 = {
    "folder_root": {
        "folder_0000": {
            "uac_ua0.xml": None,
            "dummy_ua0.xml": None,
        },
        "folder_0001": { # folder with neither uas nor uac xml files
            "dummy_ua0.xml": None,
        },
        "file_users.csv": None
    }
}

fs_invalid_5 = {
    "folder_wrong": { # TestPool is being passed "folder_root" directory which doesn't match "folder wrong"
        "uac_ua0.xml": None,
    }
}

@pytest.mark.parametrize(
    "mock_fs,pattern_exclude,pattern_only,expected", [
        # test valid FS
        (
            fs_valid_1,
            [],
            [],
            [
                ("folder_0000", 1),
                ("folder_0001", 3),
            ]
        ),
        (
            fs_valid_2,
            [],
            [],
            [
                ("folder_0000", 1),
                ("folder_0001", 3),
            ]
        ),
        (
            fs_valid_1,
            [],
            ["folder_0000"],
            [
                ("folder_0000", 1),
            ]
        ),
        # test pattern_exclude
        (
            fs_valid_1,
            [".*0001"],
            [],
            [
                ("folder_0000", 1)
            ]
        ),
        (
            fs_valid_1,
            ["folder_000.*"],
            [],
            TestPool.CollectException()
        ),
        # test pattern_only
        (
            fs_valid_1,
            [],
            ["folder_000.*"],
            [
                ("folder_0000", 1),
                ("folder_0001", 3),
            ]
        ),
        (
            fs_valid_1,
            [],
            ["folder_nonexistent"],
            TestPool.CollectException()
        ),
        # test pattern_exclude and pattern_only
        (
            fs_valid_1,
            [".*0001"],
            [".*0000"],
            [
                ("folder_0000", 1)
            ]
        ),
        (
            fs_valid_1,
            ["nonexistent"],
            ["folder_000.*"],
            [
                ("folder_0000", 1),
                ("folder_0001", 3),
            ]
        ),
        (
            fs_valid_1,
            ["folder_000.*"],
            ["folder_000.*"],
            TestPool.CollectException()
        ),
        # test multiple pattern_exclude
        (
            fs_valid_1,
            ["nonexistent", "folder_000.*"],
            [],
            TestPool.CollectException()
        ),
        # test multiple pattern_only
        (
            fs_valid_1,
            [],
            ["nonexistent", ".*0000"],
            [
                ("folder_0000", 1)
            ]
        ),
        # test multiple pattern-exclude + multiple pattern_only
        (
            fs_valid_1,
            ["nonexistent", ".*0001"],
            [".*0000", ".*0001"],
            [
                ("folder_0000", 1)
            ]
        ),
        (
            fs_valid_1,
            [".*0000", ".*0001"],
            [".*0000", ".*0001"],
            TestPool.CollectException()
        ),
        # test invalid FS
        (
            fs_invalid_1,
            [],
            [],
            SIPpTest.InitException()
        ),
        (
            fs_invalid_2,
            [],
            [],
            SIPpTest.InitException()
        ),
        (
            fs_invalid_2,
            [],
            ["folder_0001"],
            SIPpTest.InitException()
        ),
        (
            fs_invalid_1,
            [],
            ["folder_0001"],
            SIPpTest.InitException()
        ),
        (
            fs_invalid_5,
            [],
            [],
            TestPool.CollectException()
        )
    ]
)
def test_test_pool(mock_fs, pattern_exclude, pattern_only, expected):
    """Testing over different FS layouts
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_test_pool_")
    sipplauncher.utils.Utils.gen_file_struct(dirpath, mock_fs)

    with sipplauncher.utils.Utils.cd(dirpath):
        args = argparse.Namespace(testsuite="folder_root", template_folder=None, pattern_exclude=pattern_exclude, pattern_only=pattern_only)
        if isinstance(expected, Exception):
            with pytest.raises(type(expected)):
                tests = TestPool.collect(args)
        else:
            tests = TestPool.collect(args)
            for a, b in zip(tests, expected):
                assert a.key == b[0]
                assert len(a._SIPpTest__uas) == b[1]

    shutil.rmtree(dirpath)
