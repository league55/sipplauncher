#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pytest
import tempfile
from OpenSSL import crypto
from sipplauncher.utils.CAOpenSSL import CAOpenSSL
from sipplauncher.utils.Utils import (cd,
                                      gen_file_struct)

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

CN="1.1.1.1"

def test():
    """Testing SSL cert generation
    """
    mock_fs = {
        "ca_cert.pem": CERT,
        "ca_key.pem": KEY,
    }

    dirpath = tempfile.mkdtemp(prefix="sipplauncher_test_CAOpenSSL_")
    gen_file_struct(dirpath, mock_fs)

    def verify_cert(cert_path, ca_cert_path):
        cert_file = open(cert_path, 'r')
        cert_data = cert_file.read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)

        ca_cert_file = open(ca_cert_path, 'r')
        ca_cert_data = ca_cert_file.read()
        ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_cert_data)

        store = crypto.X509Store()
        store.add_cert(ca_cert)

        store_ctx = crypto.X509StoreContext(store, cert)
        store_ctx.verify_certificate()

        subject = cert.get_subject()
        assert(subject.CN == CN)

    with cd(dirpath):
        ca = CAOpenSSL("ca_cert.pem", "ca_key.pem")
        cert, key = ca.gen_cert_key(CN, "cert")
        verify_cert(cert, "ca_cert.pem")
