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
import time

from sipplauncher.utils.Utils import gen_file_struct
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.Run import (run,
                              PCAP_SYNC_TIMEOUT)
from sipplauncher.utils.Defaults import DEFAULT_GROUP_PAUSE

DUT_IP = "1.1.1.1"
TEST_NAME = "my_test_name"

# How long the mock SIPp process will run.
SIPP_MOCK_RUN_TIME = 6 # sec

# Maximum duration which the sipplaucncher code should run in OK case.
# This includes:
# - thread/process synchronization
# - ARP ping
# - syscalls (including Netlink)
# - actual Python code execution
# This was tested on Virtualbox VM.
# On physical server this may be faster.
SIPPLAUNCHER_RUN_TIME_OK = 3 # sec
# Maximum duration which the sipplaucncher code should run in FAIL case.
SIPPLAUNCHER_RUN_TIME_FAIL = 0.1 # sec

ZERO_RUN_TIME = 0

SIPP_RET_OK = 0
SIPP_RET_FAIL = 1

RUN_RET_OK = 0
RUN_RET_FAIL = 1

@pytest.mark.parametrize(
    "mock_fs,args,sipp_retcode,expected_ret,expected_elapsed_min,expected_elapsed_delta", [
        # basic sane test
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_OK,
            SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT,
            SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # --no-pcap should be faster
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --no-pcap".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_OK,
            SIPP_MOCK_RUN_TIME,
            SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # sipp fails
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            SIPP_RET_FAIL,
            RUN_RET_FAIL,
            SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT,
            SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # sipp fails and fail is expected
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --fail-expected --leave-temp".format(DUT_IP),
            SIPP_RET_FAIL,
            RUN_RET_OK,
            SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT,
            SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # basic insane test
        (
            {
                TEST_NAME: {
                    "dummy_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_FAIL,
            ZERO_RUN_TIME,
            SIPPLAUNCHER_RUN_TIME_FAIL,
        ),
        (
            {
                TEST_NAME: {
                    "dummy_ua0.xml": None,
                },
            },
            "--dut {0} --fail-expected".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_FAIL,
            ZERO_RUN_TIME,
            SIPPLAUNCHER_RUN_TIME_FAIL,
        ),
        # 2 sane consecutive tests
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_OK,
            2 * (SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT) + DEFAULT_GROUP_PAUSE,
            2 * SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # 2 sane consecutive tests + --group-pause
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group-pause 5 --leave-temp".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_OK,
            2 * (SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT) + 5,
            2 * SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # 2 sane concurrent tests
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group 2 --leave-temp".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_OK,
            SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT,
            2 * SIPPLAUNCHER_RUN_TIME_OK,
        ),
        # 2 sane concurrent tests v2
        (
            {
                "{0}_1".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
                "{0}_2".format(TEST_NAME): {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --group 3 --leave-temp".format(DUT_IP),
            SIPP_RET_OK,
            RUN_RET_OK,
            SIPP_MOCK_RUN_TIME + 2 * PCAP_SYNC_TIMEOUT,
            2 * SIPPLAUNCHER_RUN_TIME_OK,
        ),
    ]
)
def test(mocker, mock_fs, args, sipp_retcode, expected_ret, expected_elapsed_min, expected_elapsed_delta):
    """Testing SIPpTest basic sanity
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test")
    gen_file_struct(dirpath, mock_fs)

    def my_pysipp_process_run(self):
        time.sleep(SIPP_MOCK_RUN_TIME) # emulate SIPp run
        sys.exit(sipp_retcode)

    mocker.patch('sipplauncher.PysippProcess.PysippProcess.run', new=my_pysipp_process_run)
    logging.getLogger("pysipp").propagate = 0

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    start = time.time()
    ret = run(parsed_args)
    end = time.time()
    elapsed = end - start

    assert(ret == expected_ret)
    assert(expected_elapsed_min <= elapsed and elapsed <= expected_elapsed_min + expected_elapsed_delta)

    shutil.rmtree(dirpath)
