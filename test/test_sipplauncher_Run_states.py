#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pytest
import tempfile
import sys
import shutil
import logging
import shlex

from sipplauncher.utils.Utils import gen_file_struct
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.Run import run
from sipplauncher.Test import SIPpTest
import sipplauncher.Test

DUT_IP = "1.1.1.1"
TEST_NAME = "my_test_name"

@pytest.mark.parametrize(
    "mock_fs,args,expected_states", [
        # basic sane test
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --dry-run".format(DUT_IP),
            [(TEST_NAME, SIPpTest.State.CREATED),
             (TEST_NAME, SIPpTest.State.PREPARING),
             (TEST_NAME, SIPpTest.State.READY),
             (TEST_NAME, SIPpTest.State.DRY_RUNNING),
             (TEST_NAME, SIPpTest.State.SUCCESS),
             (TEST_NAME, SIPpTest.State.CLEANING),
             (TEST_NAME, SIPpTest.State.CLEAN)],
        ),
    ]
)
def test(mocker, mock_fs, args, expected_states):
    """Testing SIPpTest basic sanity
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test")
    gen_file_struct(dirpath, mock_fs)

    states = []

    def my_test_set_state(self, state, orig_set_state=sipplauncher.Test.SIPpTest._SIPpTest__set_state):
        states.append((self.key, state))
        orig_set_state(self, state)

    mocker.patch('sipplauncher.Test.SIPpTest._SIPpTest__set_state', new=my_test_set_state)
    logging.getLogger("pysipp").propagate = 0

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    run(parsed_args)

    assert(states == expected_states)

    shutil.rmtree(dirpath)
