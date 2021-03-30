#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pytest
import tempfile
import os
import shutil
import shlex
import sipplauncher.utils.Utils
import logging

from pytest_mock import mocker
from sipplauncher.utils.Utils import gen_file_struct
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.Test import SIPpTest, SIPpTestTemplate
from sipplauncher.GlobalTest import GlobalTest

DUT_IP = "1.1.1.1"
TEST_NAME = "my_test_name"
TEST_RUN_ID = sipplauncher.utils.Utils.generate_id(n=6, just_letters=True)

@pytest.mark.parametrize(
    "mock_fs,args,expected", [
        # basic test
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "",
                    "uas_ua1.xml": "",
                    "before.sh": "echo -n 1 > before.txt",
                    "after.sh": "echo -n 2 > after.txt",
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            {
                "before.txt" : "1",
                "after.txt" : "2",
            },
        ),
        # error exit code
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "",
                    "uas_ua1.xml": "",
                    "before.sh": "echo -n 1 > before.txt",
                    "after.sh": "echo -n 2 > after.txt\nexit -1",
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            {
                "before.txt" : "1",
                "after.txt" : "2",
            },
        ),
        # error exit code
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "",
                    "uas_ua1.xml": "",
                    "before.sh": "echo -n 1 > before.txt\nexit -1",
                    "after.sh": "echo -n 2 > after.txt",
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            {
                "before.txt" : "1",
                "after.txt": None
            },
        ),
        # dry run
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "",
                    "uas_ua1.xml": "",
                    "before.sh": "echo -n 1 > before.txt",
                    "after.sh": "echo -n 2 > after.txt",
                },
            },
            "--dut {0} --leave-temp --dry-run".format(DUT_IP),
            {
                "before.txt" : None,
                "after.txt" : None,
            },
        ),
    ]
)
def test(mocker, mock_fs, args, expected):
    """Testing SIPpTest keyword replacement
    """
    cur_path = os.getcwd()
    logging.getLogger("pysipp").propagate = 0
    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))

    def check_folder(fs_path, root):
        for a, b in iter(root.items()):
            tmp_fs_path = os.path.join(fs_path, a)
            if b:
                with open(tmp_fs_path, 'r') as f:
                    content = f.read()
                    assert(content == b)
            else:
                assert(not os.path.isfile(tmp_fs_path))

    # SIPpTest

    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test_chdir_")
    sipplauncher.utils.Utils.gen_file_struct(dirpath, mock_fs)
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    test = SIPpTestTemplate(os.path.join(dirpath, TEST_NAME)).build_SIPpTest()
    test.pre_run(TEST_RUN_ID, parsed_args)
    test.run(TEST_RUN_ID, parsed_args)
    test.post_run(TEST_RUN_ID, parsed_args)

    check_folder(test._SIPpTest__temp_folder, expected)
    shutil.rmtree(dirpath)
    assert(os.getcwd() == cur_path) # We should return to the current working directory

    # GlobalTest

    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test_chdir_")
    sipplauncher.utils.Utils.gen_file_struct(dirpath, mock_fs)
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    global_test = GlobalTest(os.path.join(dirpath, TEST_NAME))
    # Unlike SIPpTest, GlobalTest might raise an exception.
    try:
        global_test.pre_run(TEST_RUN_ID, parsed_args)
    except Exception as e:
        pass
    global_test.post_run(TEST_RUN_ID, parsed_args)

    check_folder(global_test._SIPpTest__temp_folder, expected)
    shutil.rmtree(dirpath)
    assert(os.getcwd() == cur_path) # We should return to the current working directory
