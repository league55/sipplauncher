#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pytest
import tempfile
import os
import shlex
import OpenSSL

from sipplauncher.utils.Utils import (cd,
                                      gen_file_struct)
from sipplauncher.utils.Init import (generate_parser,
                                     check_and_patch_args)
from sipplauncher.utils.Defaults import DEFAULT_TESTSUITE

DUT_IP = "1.1.1.1"

CERT = """-----BEGIN CERTIFICATE-----
MIICmjCCAgMCAgPoMA0GCSqGSIb3DQEBCwUAMHsxCzAJBgNVBAYTAkVTMQ8wDQYD
VQQIDAZNYWRyaWQxDzANBgNVBAcMBk1hZHJpZDEYMBYGA1UECgwPY2Euc2lwcGxh
dW5jaGVyMRgwFgYDVQQLDA9jYS5zaXBwbGF1bmNoZXIxFjAUBgNVBAMMDWNhLnph
bGVvcy5uZXQwHhcNMTkxMDIzMTQwMDIwWhcNMjkxMDI1MTQwMDIwWjB7MQswCQYD
VQQGEwJFUzEPMA0GA1UECAwGTWFkcmlkMQ8wDQYDVQQHDAZNYWRyaWQxGDAWBgNV
BAoMD2NhLnNpcHBsYXVuY2hlcjEYMBYGA1UECwwPY2Euc2lwcGxhdW5jaGVyMRYw
FAYDVQQDDA1jYS56YWxlb3MubmV0MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKB
gQDWZCSRPiv09N+t/YkjoaDsPUvCKQ2uSHGbxxgOb1qLAKUMUf/bQ1Y8oqv3zb4T
ompa6Mv6pd+bozJ9cjz/vTZOBs3flCcXPGea/0fEXmYAyqbFMi2zhA6uOc0y2CF+
bIvp9uZjU9zAMBezruJmOhln/cWfxR4RHF3aDeIH+xb4CwIDAQABozIwMDAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBSVNMKssIRABlONi0X0YHnS3fi9yzANBgkq
hkiG9w0BAQsFAAOBgQDWDcbsrDvn9xdaWJPH/QqLidUKqm3bvuQrcGm6AD04wQiR
+n61HIJyvTaT6L/9hiysQTIZcri79Vso+VpLZ+r/lWCCt6H2YtVco+1JK5eXRR/r
Jqsaq2hNjv+mW+IAMwoi84Z2o9WeYt09Jjj0XT/hznyWp4ujmDdo0BHrACQEPQ==
-----END CERTIFICATE-----"""

KEY = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBANZkJJE+K/T03639
iSOhoOw9S8IpDa5IcZvHGA5vWosApQxR/9tDVjyiq/fNvhOialroy/ql35ujMn1y
PP+9Nk4Gzd+UJxc8Z5r/R8ReZgDKpsUyLbOEDq45zTLYIX5si+n25mNT3MAwF7Ou
4mY6GWf9xZ/FHhEcXdoN4gf7FvgLAgMBAAECgYEA1llBhkXWxQ6fJOI8XveWYRvX
xsQs/XdIvysLjkMfD6MRYYQKfzqP2gf6T8PQqujT1Riz+GIncwBz1qCFBFw1EXEx
Q5aG60UaP62mC6qkgBUm6tdAglpfwA8bdQ0ZHKIHEz9vXJQLSqIHwYCg1WkY41TZ
C1oYJcSxJ9YQEQKstoECQQD0doesldrOlIso008FRgbJl3FTh0a6B8lkaqnmxQ4M
824A+XiNEUuxkG72nhvr/l9sr8LxGrmZM3IHLM5m0mqbAkEA4IJNI0WHFU1kyoot
DQw+WpyGftqVoQ7exj5PFhf/bymBe6yTv087/o7hizvX3s+EmSndkOiyZpYkjFOV
7dsHUQJAC1b0NC0/WRXK3rnukHAPIIrF1voPbdGupdnMx8ecPz2LfMAVt3V17Wal
vwrWgLvr8T617DkxIsogH/UUHfDkwQJAYkvqpiTM7iDCnoM9Eldn/ZhGssfVd3zh
QP8K9WtwZSVREesPjVWNuPip+6Ip8937+muAHPAlHBFk0yPNoySg4QJBAIwqn3i/
gfBzdTrDBHYChV2vIHnlJbzpzEx7ho7Te/hTWROCBpHVdZ86FPh6MxJVJSWxLyLx
dzgzpq2UrIxvZ8Q=
-----END PRIVATE KEY-----"""

@pytest.mark.parametrize(
    "mock_fs,args,expected", [
        # basic case
        (
            {},
            "--dut {0} --testsuite {1}".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            None,
        ),
        # basic case
        (
            {},
            "--dut {0} --testsuite nonexistent".format(DUT_IP),
            SystemExit(),
        ),
        # auto-generate TLS certificate and key
        (
            {},
            "--dut {0} --testsuite {1} --sipp-transport l1".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            None,
        ),
        # auto-generate TLS certificate and key
        (
            {},
            "--dut {0} --testsuite {1} --sipp-transport ln".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            None,
        ),
        # lack of TLS args
        (
            {},
            "--dut {0} --testsuite {1} --sipp-tls-version '1.0'".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            SystemExit(),
        ),
        # lack of TLS args
        (
            {
                "cert.pem": CERT,
            },
            "--dut {0} --testsuite {1} --tls-ca-root-cert cert.pem".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            SystemExit(),
        ),
        # lack of TLS args
        (
            {
                "key.pem": KEY,
            },
            "--dut {0} --testsuite {1} --tls-ca-root-key key.pem".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            SystemExit(),
        ),
        # wrong transport
        (
            {
                "cert.pem": CERT,
                "key.pem": KEY,
            },
            "--dut {0} --testsuite {1} --tls-ca-root-cert cert.pem --tls-ca-root-key key.pem --sipp-transport u1".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            SystemExit(),
        ),
        # sufficient TLS args
        (
            {
                "cert.pem": CERT,
                "key.pem": KEY,
            },
            "--dut {0} --testsuite {1} --tls-ca-root-cert cert.pem --tls-ca-root-key key.pem --sipp-transport l1".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            None,
        ),
        # sufficient TLS args, but mixed up certs
        (
            {
                "cert.pem": KEY,
                "key.pem": CERT,
            },
            "--dut {0} --testsuite {1} --tls-ca-root-cert cert.pem --tls-ca-root-key key.pem --sipp-transport l1".format(DUT_IP, os.path.abspath(DEFAULT_TESTSUITE)),
            OpenSSL.crypto.Error(),
        ),
    ]
)
def test(mock_fs, args, expected):
    """Testing command-line argument combinations
    """
    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_args_")
    gen_file_struct(dirpath, mock_fs)

    with cd(dirpath):
        parser = generate_parser()
        if isinstance(expected, BaseException):
            with pytest.raises(type(expected)):
                parsed_args = parser.parse_args(shlex.split(args))
                check_and_patch_args(parsed_args)
        else:
            parsed_args = parser.parse_args(shlex.split(args))
            check_and_patch_args(parsed_args)
