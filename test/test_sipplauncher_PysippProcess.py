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
import logging
import jinja2
import shlex
import pysipp
from multiprocessing import Queue

from sipplauncher.utils.Utils import gen_file_struct
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.Test import SIPpTest
from sipplauncher.utils.Defaults import (DEFAULT_SCRIPT_TIMEOUT,
                                         DEFAULT_TESTSUITE_TEMPLATES)

DUT_IP = "1.1.1.1"
TEST_NAME = "my_test_name"

@pytest.mark.parametrize(
    "mock_fs,args,expected", [
        # 1 ua, 1 default group
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "uac_ua0.xml" ],
            ],
        ),
        # test uas launched before uac
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "uas_ua1.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "uas_ua1.xml", "uac_ua0.xml" ],
            ],
        ),
        # 2 uas, 1 default group
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "uac_ua1.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "uac_ua0.xml", "uac_ua1.xml" ],
            ],
        ),
        # 2 uas, 1 group
        (
            {
                TEST_NAME: {
                    "1_uac_ua0.xml": None,
                    "1_uac_ua1.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "1_uac_ua0.xml", "1_uac_ua1.xml" ],
            ],
        ),
        # mix default and non-default group
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "1_uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "uac_ua0.xml" ],
                [ "1_uac_ua0.xml" ],
            ],
        ),
        # 1 ua, 2 groups
        (
            {
                TEST_NAME: {
                    "0_uac_ua0.xml": None,
                    "1_uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "0_uac_ua0.xml" ],
                [ "1_uac_ua0.xml" ],
            ],
        ),
        # test alphanumeric prefix
        (
            {
                TEST_NAME: {
                    "part000_uac_ua0.xml": None,
                    "part001_uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "part000_uac_ua0.xml" ],
                [ "part001_uac_ua0.xml" ],
            ],
        ),
        # 3 uas, 3 groups
        (
            {
                TEST_NAME: {
                    "0_uac_ua0.xml": None,
                    "0_uac_ua1.xml": None,
                    "1_uac_ua0.xml": None,
                    "1_uac_ua1.xml": None,
                    "2_uac_ua2.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            [
                [ "0_uac_ua0.xml", "0_uac_ua1.xml" ],
                [ "1_uac_ua0.xml", "1_uac_ua1.xml" ],
                [ "2_uac_ua2.xml" ],
            ],
        ),
        # 1 ua, 1 default group, 2 calls
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --sipp-max-calls 2".format(DUT_IP),
            [
                [ "uac_ua0.xml" ],
            ],
        ),
        # 1 ua, 2 groups, 2 calls
        (
            {
                TEST_NAME: {
                    "0_uac_ua0.xml": None,
                    "1_uac_ua0.xml": None,
                },
            },
            "--dut {0} --sipp-max-calls 2".format(DUT_IP),
            [
                [ "0_uac_ua0.xml" ],
                [ "1_uac_ua0.xml" ],
                [ "0_uac_ua0.xml" ],
                [ "1_uac_ua0.xml" ],
            ],
        ),
        # 3 uas, 3 groups. 2 calls
        (
            {
                TEST_NAME: {
                    "0_uac_ua0.xml": None,
                    "0_uac_ua1.xml": None,
                    "1_uac_ua0.xml": None,
                    "1_uac_ua1.xml": None,
                    "2_uac_ua2.xml": None,
                },
            },
            "--dut {0} --sipp-max-calls 2".format(DUT_IP),
            [
                [ "0_uac_ua0.xml", "0_uac_ua1.xml" ],
                [ "1_uac_ua0.xml", "1_uac_ua1.xml" ],
                [ "2_uac_ua2.xml" ],
                [ "0_uac_ua0.xml", "0_uac_ua1.xml" ],
                [ "1_uac_ua0.xml", "1_uac_ua1.xml" ],
                [ "2_uac_ua2.xml" ],
            ],
        ),
    ]
)
def test(mocker, mock_fs, args, expected):
    """Testing SIPpTest basic sanity
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test")
    gen_file_struct(dirpath, mock_fs)

    # mock_call() is called from spawned process.
    # Therfore, we need to use Queue to get data back to us.
    # Just list in memory won't work.
    q = Queue()

    def mock_call(self):
        q.put([ agent.scen_file for agent in self._agents ])

    mocker.patch('pysipp.agent.ScenarioType.__call__', new=mock_call)

    logging.getLogger("pysipp").propagate = 0
    logging.getLogger("scapy.runtime").setLevel(logging.ERROR) # to not to spoil test output with warnings

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath

    # Exception is not expected
    check_and_patch_args(parsed_args)

    test = SIPpTest(os.path.join(dirpath, TEST_NAME))
    test.pre_run(parsed_args)
    try:
        test.run("", parsed_args)
    finally:
        # Always post_run to not to leave network config from previous run
        test.post_run(parsed_args)

    res = []
    while not q.empty():
        res.append(q.get())

    assert(res == expected)

    shutil.rmtree(dirpath)
