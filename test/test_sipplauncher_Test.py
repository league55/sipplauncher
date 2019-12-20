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

from sipplauncher.utils.Utils import gen_file_struct
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.Test import SIPpTest
from sipplauncher.utils.Defaults import (DEFAULT_SCRIPT_TIMEOUT,
                                         DEFAULT_TESTSUITE_TEMPLATES)
from sipplauncher.UA import UA

DUT_IP = "1.1.1.1"
TEST_NAME = "my_test_name"

@pytest.mark.parametrize(
    "mock_fs,args,expected", [
        (
            {
                TEST_NAME: {
                    "dummy_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.InitException(),
        ),
        (
            {
                TEST_NAME: {
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.InitException(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "",
            SystemExit(),  # no DUT specified
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dry-run",
            SystemExit(), # no DUT specified
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --dry-run".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "uas_ua0.xml": None,
                },
            },
            "--dut {0} --dry-run".format(DUT_IP),
            UA.DuplicateScenarioException(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                },
            },
            "--dut {0} --leave-temp".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "exit 0",
                    "after.sh": "exit 0",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "exit 0",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "after.sh": "exit 0",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "exit 1",
                    "after.sh": "exit 0",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.ScriptRunException(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "exit 0",
                    "after.sh": "exit 1",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.ScriptRunException(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "exit 1",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.ScriptRunException(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "after.sh": "exit 1",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.ScriptRunException(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "dummy1.sh": "exit 1",
                    "dummy2.sh": "exit 1",
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        # Issue-25: should be error when some of keywords are not replaced
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{keyword}}",
                    "uas_ua1.xml": "{{some_other_keyword}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"keyword": "replaced"}'),
            jinja2.exceptions.UndefinedError(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{keyword}}",
                    "before.sh": "echo {{some_other_keyword}} > /dev/null",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"keyword": "replaced"}'),
            jinja2.exceptions.UndefinedError(),
        ),
        # test absent template specified
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{% import 'options.jinja2' as options %}",
                },
            },
            "--dut {0}".format(DUT_IP),
            jinja2.exceptions.TemplateNotFound("options.jinja2"),
        ),
        # test present template specified
        (
            {
                DEFAULT_TESTSUITE_TEMPLATES: {
                    "options.jinja2": "{% macro send(transport) -%}\n" +
                                      "OPTIONS sip:[remote_ip]:{{transport}} SIP/2.0\n" +
                                      "{%- endmacro %}"
                },
                TEST_NAME: {
                    "uac_ua0.xml": "{% import 'options.jinja2' as options %}\n" +
                                   "{{ options.send(transport) }}\n",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"transport": "tcp"}'),
            SIPpTest.State.SUCCESS,
        ),
        # test templated script
        (
            {
                DEFAULT_TESTSUITE_TEMPLATES: {
                    "script.jinja2": "{% macro echo(val) -%}\n" +
                                      "exit {{val}}\n" +
                                      "{%- endmacro %}"
                },
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "{% import 'script.jinja2' as script %}\n" +
                                   "{{ script.echo(val) }}\n",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"val": "0"}'),
            SIPpTest.State.SUCCESS,
        ),
        # test templated script
        (
            {
                DEFAULT_TESTSUITE_TEMPLATES: {
                    "script.jinja2": "{% macro echo(val) -%}\n" +
                                      "exit {{val}}\n" +
                                      "{%- endmacro %}"
                },
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "{% import 'script.jinja2' as script %}\n" +
                                   "{{ script.echo(val) }}\n",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"val": "1"}'),
            SIPpTest.ScriptRunException(),
        ),
        # test undefined keyword
        (
            {
                DEFAULT_TESTSUITE_TEMPLATES: {
                    "options.jinja2": "{% macro send(transport) -%}\n" +
                                      "OPTIONS sip:[remote_ip]:{{transport}} SIP/2.0\n" +
                                      "{%- endmacro %}"
                },
                TEST_NAME: {
                    "uac_ua0.xml": "{% import 'options.jinja2' as options %}\n" +
                                   "{{ options.send(transport) }}\n",
                },
            },
            "--dut {0}".format(DUT_IP),
            jinja2.exceptions.UndefinedError(),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{keyword}}",
                    "dummy.xml": "{{some_other_keyword}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"keyword": "replaced"}'),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "while true; do cat; done", # emulate deadlock
                },
            },
            "--dut {0}".format(DUT_IP),
            subprocess.TimeoutExpired("subprocess.communicate", DEFAULT_SCRIPT_TIMEOUT),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "after.sh": "while true; do cat; done", # emulate deadlock
                },
            },
            "--dut {0}".format(DUT_IP),
            subprocess.TimeoutExpired("subprocess.communicate", DEFAULT_SCRIPT_TIMEOUT),
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "before.sh": "sleep {0}".format(DEFAULT_SCRIPT_TIMEOUT * 0.9),
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": None,
                    "after.sh": "sleep {0}".format(DEFAULT_SCRIPT_TIMEOUT * 0.9),
                },
            },
            "--dut {0}".format(DUT_IP),
            SIPpTest.State.SUCCESS,
        ),
    ]
)
def test(mocker, mock_fs, args, expected):
    """Testing SIPpTest basic sanity
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test")
    gen_file_struct(dirpath, mock_fs)

    mocker.patch('sipplauncher.PysippProcess.PysippProcess.run', new=lambda x: sys.exit(0))
    logging.getLogger("pysipp").propagate = 0

    def do_test(dirpath, args):
        test = SIPpTest(os.path.join(dirpath, TEST_NAME))
        test.pre_run(args)
        try:
            # First test __do_run() method. It can raise exception.
            if test.state == SIPpTest.State.READY:
                test._SIPpTest__do_run("", args)

            # Then test run() method. It shouldn't raise exception.
            test.run("", args)
        finally:
            # Always post_run after successful pre_run
            # to not to leave network config from previous run
            test.post_run(args)

        # Issue #9: Create dynamic execution test temp folder for each test execution
        exists = os.path.isdir(test._SIPpTest__temp_folder)
        assert(exists == args.leave_temp)

        return test.state

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath

    if isinstance(expected, BaseException):
        # Exception is expected
        with pytest.raises(type(expected)):
            check_and_patch_args(parsed_args)
            do_test(dirpath, parsed_args)
    else:
        # Exception is not expected
        check_and_patch_args(parsed_args)
        do_test(dirpath, parsed_args) == expected

    shutil.rmtree(dirpath)
