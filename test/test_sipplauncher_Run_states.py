#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import os
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
VALID_XML = """<?xml version="1.0" encoding="ISO-8859-1" ?>
<scenario name="">
<send>
<![CDATA[
ACK SIP/2.0
]]>
</send>
<pause milliseconds="1000" />
</scenario>"""

def _test_helper(mocker, mock_fs, args, expected_states):
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test")
    gen_file_struct(dirpath, mock_fs)

    states = []

    def my_test_set_state(self, state, orig_set_state=sipplauncher.Test.SIPpTest._set_state):
        states.append((self.key, state))
        orig_set_state(self, state)

    mocker.patch('sipplauncher.Test.SIPpTest._set_state', new=my_test_set_state)
    logging.getLogger("pysipp").propagate = 0

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    run(parsed_args)

    assert(states == expected_states)

    shutil.rmtree(dirpath)



@pytest.mark.parametrize(
    "mock_fs,args,expected_states", [
        # basic dry-run test
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
        # basic sane test
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [(TEST_NAME, SIPpTest.State.CREATED),
             (TEST_NAME, SIPpTest.State.PREPARING),
             (TEST_NAME, SIPpTest.State.READY),
             (TEST_NAME, SIPpTest.State.STARTING),
             (TEST_NAME, SIPpTest.State.FAIL),
             (TEST_NAME, SIPpTest.State.CLEANING),
             (TEST_NAME, SIPpTest.State.CLEAN)],
        ),
        # 2 consecutive tests
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEAN),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
        # before.sh failure
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "exit -1",
                },
            },
            "--dut {0}".format(DUT_IP),
            [(TEST_NAME, SIPpTest.State.CREATED),
             (TEST_NAME, SIPpTest.State.PREPARING),
             (TEST_NAME, SIPpTest.State.NOT_READY)],
        ),
        # after.sh failure
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "after.sh": "exit -1",
                },
            },
            "--dut {0}".format(DUT_IP),
            [(TEST_NAME, SIPpTest.State.CREATED),
             (TEST_NAME, SIPpTest.State.PREPARING),
             (TEST_NAME, SIPpTest.State.READY),
             (TEST_NAME, SIPpTest.State.STARTING),
             (TEST_NAME, SIPpTest.State.FAIL),
             (TEST_NAME, SIPpTest.State.CLEANING),
             (TEST_NAME, SIPpTest.State.DIRTY)],
        ),
        # 2 consecutive tests, before.sh failure
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                    "before.sh": "exit -1",
                },
                "{0}_2".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.NOT_READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
    ]
)
def test_sequential(mocker, mock_fs, args, expected_states):
    """Testing SIPpTest basic sanity
    """
    _test_helper(mocker, mock_fs, args, expected_states)
    


@pytest.mark.skipif(
    'CI' in os.environ,
    reason="Group tests sometimes fail due to slightly different state order produced by concurrently executing states. Not reliable enough for CI"
)
@pytest.mark.parametrize(
    "mock_fs,args,expected_states", [
        # 2 concurrent tests
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uas_ua0.xml": VALID_XML,
                },
            },
            "--dut {0} --group 2".format(DUT_IP),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.SUCCESS),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEAN),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
        # 2 concurrent tests, before.sh failure
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                    "before.sh": "exit -1",
                },
                "{0}_2".format(TEST_NAME): {
                    "uas_ua0.xml": VALID_XML,
                },
            },
            "--dut {0} --group 2".format(DUT_IP),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.NOT_READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.SUCCESS),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
        # 2 concurrent tests + 1 consecutive, before.sh failure
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                    "before.sh": "exit -1",
                },
                "{0}_2".format(TEST_NAME): {
                    "uas_ua0.xml": None,
                },
                "{0}_3".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group 2".format(DUT_IP),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.NOT_READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEAN),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
    ]
)
def test_group(mocker, mock_fs, args, expected_states):
    """Testing SIPpTest basic sanity
    """
    _test_helper(mocker, mock_fs, args, expected_states)
    

@pytest.mark.skipif(
    'CI' in os.environ,
    reason="Group tests sometimes fail due to slightly different state order produced by concurrently executing states. Not reliable enough for CI"
)
@pytest.mark.parametrize(
    "mock_fs,args,expected_exception_at,expected_states", [
        # 2 concurrent tests + 1 consecutive, exception in 1st test before.sh
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uas_ua0.xml": None,
                },
                "{0}_3".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group 2".format(DUT_IP),
            ("{0}_1".format(TEST_NAME), "before.sh"),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.NOT_READY)],
        ),
        # 1 test, exception in after.sh
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            (TEST_NAME, "after.sh"),
            [(TEST_NAME, SIPpTest.State.CREATED),
             (TEST_NAME, SIPpTest.State.PREPARING),
             (TEST_NAME, SIPpTest.State.READY),
             (TEST_NAME, SIPpTest.State.STARTING),
             (TEST_NAME, SIPpTest.State.FAIL),
             (TEST_NAME, SIPpTest.State.CLEANING),
             (TEST_NAME, SIPpTest.State.DIRTY)],
        ),
        # 2 concurrent tests + 1 consecutive, exception in 2nd test after.sh
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uas_ua0.xml": VALID_XML,
                },
                "{0}_3".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group 2".format(DUT_IP),
            ("{0}_2".format(TEST_NAME), "after.sh"),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.STARTING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.FAIL),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.SUCCESS),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.DIRTY),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
        # 2 concurrent tests + 1 consecutive, exception in 2nd test before.sh
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uas_ua0.xml": None,
                },
                "{0}_3".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group 2".format(DUT_IP),
            ("{0}_2".format(TEST_NAME), "before.sh"),
            [("{0}_1".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_3".format(TEST_NAME), SIPpTest.State.CREATED),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.READY),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.PREPARING),
             ("{0}_2".format(TEST_NAME), SIPpTest.State.NOT_READY),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEANING),
             ("{0}_1".format(TEST_NAME), SIPpTest.State.CLEAN)],
        ),
    ]
)
def test_exception(mocker, mock_fs, args, expected_exception_at, expected_states):
    """Testing SIPpTest basic sanity
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test")
    gen_file_struct(dirpath, mock_fs)

    states = []

    def my_test_set_state(self, state, orig_set_state=sipplauncher.Test.SIPpTest._set_state):
        states.append((self.key, state))
        orig_set_state(self, state)

    class MockException(Exception):
        pass

    def my_run_script(self, script, args):
        if self.key == expected_exception_at[0] and script == expected_exception_at[1]:
            raise MockException

    mocker.patch('sipplauncher.Test.SIPpTest._set_state', new=my_test_set_state)
    mocker.patch('sipplauncher.Test.SIPpTest._run_script', new=my_run_script)
    logging.getLogger("pysipp").propagate = 0

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    with pytest.raises(MockException):
        run(parsed_args)

    assert(states == expected_states)

    shutil.rmtree(dirpath)
