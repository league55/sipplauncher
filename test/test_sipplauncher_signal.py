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
import shlex
import subprocess
import signal
import time

from sipplauncher.utils.Utils import gen_file_struct

@pytest.mark.parametrize(
    "command,signal_timeout,signal,expected", [
        (
            "sipplauncher --testsuite tmp-testsuite --dut 1.1.1.1 --group 3 --dry-run",
            1,
            signal.SIGINT,
            False
        ),
        # Immediate interrupt of python interpreter while it hasn't run main() and installed signal handler yet,
        # Should cause Traceback and return code != 0.
        # Exact return code seems to be dependant on platform.
        # On pure Centos-7 installation and running from bash I get retcode 1.
        # On Docker Centos-7 image and running from CI I get retcode -2.
        # https://docs.python.org/2/library/subprocess.html#subprocess.Popen.returncode
        # It's written that code -2 is valid for this case.
        # However retcode 1 doesn't look bad as well.
        # So we'd better expect not 0.
        (
            "sipplauncher --testsuite tmp-testsuite --dut 1.1.1.1 --group 3 --dry-run",
            0,
            signal.SIGINT,
            False
        ),
        (
            "sipplauncher --testsuite tmp-testsuite --dut 1.1.1.1 --group 3 --dry-run",
            1,
            signal.SIGTERM,
            False
        ),
        (
            "sipplauncher --testsuite tmp-testsuite --dut 1.1.1.1 --group 3 --dry-run",
            1,
            signal.SIGCHLD,
            True
        ),
    ]
)
def test_signal_1(command, signal_timeout, signal, expected):
    """Testing reaction to signal
    """
    args = shlex.split(command)
    p = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    time.sleep(signal_timeout)
    p.send_signal(signal)
    p.communicate()
    ret = (p.wait() == 0)
    assert(ret == expected)

def test_signal_2():
    """Testing if stop.sh is being run when handling signal
    """

    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_signal2_")
    expected_file = os.path.join(dirpath, "after_has_been_run")
    fs = {
        "test_0000" : {
            "before.sh": "sleep 10",
            "uac_ua0.xml": None,
            "after.sh": "touch " + expected_file
        }
    }
    gen_file_struct(dirpath, fs)

    args = shlex.split("sipplauncher --testsuite {0} --dut 1.1.1.1 --leave-temp".format(dirpath))
    p = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    time.sleep(5)
    p.send_signal(signal.SIGINT)
    p.communicate()
    retcode = p.wait()
    assert(os.path.isfile(expected_file))
