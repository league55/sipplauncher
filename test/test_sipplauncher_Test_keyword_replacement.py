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
import shlex
import sipplauncher.utils.Utils
import sipplauncher.Network

from pytest_mock import mocker
from sipplauncher.utils.Utils import gen_file_struct
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.Test import SIPpTest
from sipplauncher.utils.Defaults import DEFAULT_TESTSUITE_TEMPLATES

# Currently we are unit-testing keyword replacement for 2 UAs max.
# Therefore we define 2 IP address for tests.
# If you need to test more UAs - feel free to extend the list.
UA_IP = ["10.22.22.100", "10.22.22.101"]
DUT_IP = "1.1.1.1"
TEST_NAME = "my_test_name"
TEST_RUN_ID = sipplauncher.utils.Utils.generate_id(n=6, just_letters=True)

@pytest.mark.parametrize(
    "mock_fs,args,expected", [
        # basic test
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{placeholder1}}",
                    "uas_ua1.xml": "{{placeholder2}}",
                    "before.sh": "echo {{placeholder1}} > /dev/null",
                    "after.sh": "echo {{placeholder2}} > /dev/null",
                    "{0}.sh".format(TEST_RUN_ID): "echo {{placeholder1}} > /dev/null",
                    "dummy.txt": "{{placeholder1}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"placeholder1": "replaced1", "placeholder2" : "replaced2"}'),
            {
                "uac_ua0.xml": "replaced1",
                "uas_ua1.xml": "replaced2",
                "before.sh": "echo replaced1 > /dev/null",
                "after.sh": "echo replaced2 > /dev/null",
                "{0}.sh".format(TEST_RUN_ID): "echo replaced1 > /dev/null",
                "dummy.txt": "{{placeholder1}}",
            },
        ),
        # test several replacements of the same key
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{placeholder1}} {{placeholder1}}",
                    "before.sh": "echo {{placeholder2}} {{placeholder2}} > /dev/null",
                    "dummy.txt": "{{placeholder1}} {{placeholder1}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"placeholder1": "replaced1", "placeholder2" : "replaced2"}'),
            {
                "uac_ua0.xml": "replaced1 replaced1",
                "before.sh": "echo replaced2 replaced2 > /dev/null",
                "dummy.txt": "{{placeholder1}} {{placeholder1}}",
            },
        ),
        # test several replacements of different keys
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{placeholder1}} {{placeholder2}}",
                    "before.sh": "echo {{placeholder2}} {{placeholder1}} > /dev/null",
                    "dummy.txt": "{{placeholder1}} {{placeholder2}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"placeholder1": "replaced1", "placeholder2" : "replaced2"}'),
            {
                "uac_ua0.xml": "replaced1 replaced2",
                "before.sh": "echo replaced2 replaced1 > /dev/null",
                "dummy.txt": "{{placeholder1}} {{placeholder2}}",
            },
        ),
        # test several replacements of different keys on different lines
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{placeholder1}}\n{{placeholder2}}",
                    "before.sh": "echo {{placeholder2}} > /dev/null\necho {{placeholder1}} > /dev/null",
                    "dummy.txt": "{{placeholder1}}\n{{placeholder2}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"placeholder1": "replaced1", "placeholder2" : "replaced2"}'),
            {
                "uac_ua0.xml": "replaced1\nreplaced2",
                "before.sh": "echo replaced2 > /dev/null\necho replaced1 > /dev/null",
                "dummy.txt": "{{placeholder1}}\n{{placeholder2}}",
            },
        ),
        # test single UA IP replacement
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{ua0.host}}",
                    "uas_ua1.xml": "{{ua0.host}}",
                    "before.sh": "echo {{ua0.host}} > /dev/null",
                    "after.sh": "echo {{ua0.host}} > /dev/null",
                },
            },
            "--dut {0}".format(DUT_IP),
            {
                "uac_ua0.xml": UA_IP[0],
                "uas_ua1.xml": UA_IP[0],
                "before.sh": "echo {0} > /dev/null".format(UA_IP[0]),
                "after.sh": "echo {0} > /dev/null".format(UA_IP[0]),
            },
        ),
        # test multiple UA IP replacement
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{ua0.host}}",
                    "uas_ua1.xml": "{{ua1.host}}",
                    "before.sh": "echo {{ua0.host}} > /dev/null",
                    "after.sh": "echo {{ua1.host}} > /dev/null",
                },
            },
            "--dut {0}".format(DUT_IP),
            {
                "uac_ua0.xml": UA_IP[0],
                "uas_ua1.xml": UA_IP[1],
                "before.sh": "echo {0} > /dev/null".format(UA_IP[0]),
                "after.sh": "echo {0} > /dev/null".format(UA_IP[1]),
            },
        ),
        # test multiple UA IP replacement with single cross-reference
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{ua1.host}}",
                    "uas_ua1.xml": "{{ua0.host}}",
                },
            },
            "--dut {0}".format(DUT_IP),
            {
                "uac_ua0.xml": UA_IP[1],
                "uas_ua1.xml": UA_IP[0],
            },
        ),
        # test multiple UA IP replacement with multiple cross-reference
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{ua0.host}} {{ua1.host}}",
                    "uas_ua1.xml": "{{ua1.host}} {{ua0.host}}",
                },
            },
            "--dut {0}".format(DUT_IP),
            {
                "uac_ua0.xml": "{0} {1}".format(UA_IP[0], UA_IP[1]),
                "uas_ua1.xml": "{0} {1}".format(UA_IP[1], UA_IP[0]),
            },
        ),
        # test multiple UA IP replacement with multiple cross-reference + DUT
        (
            {
                TEST_NAME: {
                    "uac_ua0.xml": "{{ua0.host}} {{ua1.host}} {{dut.host}}",
                    "uas_ua1.xml": "{{ua1.host}} {{ua0.host}} {{dut.host}}",
                    "before.sh": "echo {{dut.host}} > /dev/null",
                    "after.sh": "echo {{dut.host}} > /dev/null",
                },
            },
            "--dut {0}".format(DUT_IP),
            {
                "uac_ua0.xml": "{0} {1} {2}".format(UA_IP[0], UA_IP[1], DUT_IP),
                "uas_ua1.xml": "{0} {1} {2}".format(UA_IP[1], UA_IP[0], DUT_IP),
                "before.sh": "echo {0} > /dev/null".format(DUT_IP),
                "after.sh": "echo {0} > /dev/null".format(DUT_IP),
            },
        ),
        # test script macro
        (
            {
                DEFAULT_TESTSUITE_TEMPLATES: {
                    "script.jinja2": "{% macro echo(test_name) -%}\n" +
                                      "echo {{test_name}}\n" +
                                      "{%- endmacro %}"
                },
                TEST_NAME: {
                    "uac_ua0.xml": "",
                    "before.sh": "{% import 'script.jinja2' as script %}\n" +
                                   "{{ script.echo(test.name) }}\n",
                },
            },
            "--dut {0}".format(DUT_IP),
            {
                "uac_ua0.xml": "",
                "before.sh": "\necho " + TEST_NAME,
            },
        ),
        # test scenario macro
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
            {
                "uac_ua0.xml": "\nOPTIONS sip:[remote_ip]:tcp SIP/2.0",
            },
        ),
        # test macro + keyword
        (
            {
                DEFAULT_TESTSUITE_TEMPLATES: {
                    "options.jinja2": "{% macro send(transport) -%}\n" +
                                      "OPTIONS sip:[remote_ip]:{{transport}} SIP/2.0\n" +
                                      "{%- endmacro %}"
                },
                TEST_NAME: {
                    "uac_ua0.xml": "{% import 'options.jinja2' as options %}\n" +
                                   "{{ options.send(transport) }}\n" +
                                   "{{keyword}}",
                },
            },
            "--dut {0} --keyword-replacement-values '{1}'".format(DUT_IP, '{"transport": "tcp", "keyword": "replaced"}'),
            {
                "uac_ua0.xml": "\nOPTIONS sip:[remote_ip]:tcp SIP/2.0\n" +
                               "replaced",
            },
        ),
    ]
)
def test(mocker, mock_fs, args, expected):
    """Testing SIPpTest keyword replacement
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_Test_keyword_replacement_")
    sipplauncher.utils.Utils.gen_file_struct(dirpath, mock_fs)

    test = SIPpTest(os.path.join(dirpath, TEST_NAME))

    def gen_ua_ip():
        for ip in UA_IP:
            yield ip

    ip_gen = gen_ua_ip()

    # Replace original random IP generator with the custom generator.
    # The latter generates IP consecutively from UA_IP list.
    # Therefore IP allocation happens not randomly, but in known order.
    # Knowing generated IP addresses beforehand allows us to unit-test the functionality.
    mocker.patch('sipplauncher.Network.SIPpNetwork.add_random_ip', new=lambda x: next(ip_gen))
    mocker.patch('sipplauncher.utils.Utils.generate_id', return_value=TEST_RUN_ID)

    parser = generate_parser()
    parsed_args = parser.parse_args(shlex.split(args))
    parsed_args.testsuite = dirpath
    check_and_patch_args(parsed_args)

    test.pre_run(parsed_args)

    assert(test._SIPpTest__state == SIPpTest.State.READY)

    def check_folder(fs_path, root):
        for a, b in iter(root.items()):
            tmp_fs_path = os.path.join(fs_path, a)
            with open(tmp_fs_path, 'r') as f:
                content = f.read()
                assert(content == b)

    check_folder(test._SIPpTest__temp_folder, expected)

    test.post_run(parsed_args)

    shutil.rmtree(dirpath)
