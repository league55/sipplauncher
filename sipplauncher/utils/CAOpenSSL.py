#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
CAOpenSSL.py
Generates a CA certificate and 509 certificates
- Needs PyOpenSSL (pip install PyOpenSSL)
- Inspired by https://gist.github.com/eskil/2338529
- https://www.programcreek.com/python/example/83358/OpenSSL.crypto.X509Extension
@author:  Luis Martin Gil
@contact: martingil.luis@gmail.com
https://github.com/luismartingil
www.luismartingil.com
'''

import logging
from OpenSSL import crypto, SSL
from time import gmtime, mktime
from .Defaults import DEFAULT_CA_CN

BYTES=2048
TIME_UNIT=24 * 60 * 60
HASH_ALGORITHM='sha256'
SERIAL_NUMBER=1000
VALID_DAYS_BEFORE=5 # Valid starting X days ago (helps when inmediatly validating)
VALID_YEARS_AFTER=10 # Valid until now + X number of years

EXT_CERT='crt'
EXT_KEY='key'

CA_C="ES" # countryName
CA_ST='Madrid' # stateOrProvinceName
CA_L='Madrid' # localityName
CA_O='ca.sipplauncher' # organizationName
CA_OU='ca.sipplauncher' # organizationalUnitName

class CAOpenSSL(object):
    def __init__(self, ca_cert_filepath=None, ca_key_filepath=None):
        if ca_cert_filepath and ca_key_filepath:
            with open(ca_cert_filepath, 'r') as f:
                buf = f.read()
                self.__ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, buf)

            with open(ca_key_filepath, 'r') as f:
                buf = f.read()
                self.__ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, buf)
        else:
            self.__ca_cert, self.__ca_key = self.__create_cert_key_pair(DEFAULT_CA_CN)
            self.__ca_cert.add_extensions([
                crypto.X509Extension(b'basicConstraints', True, b'CA:TRUE'),
                crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', subject=self.__ca_cert)
            ])
            logging.info("Auto-generated TLS CA certificate and key")

    @staticmethod
    def __create_cert_key_pair(cn):
        """ Generates a given cert and key using the CN (commonName) param
        """
        # Generate 509 cert
        cert = crypto.X509()
        cert.get_subject().C = CA_C
        cert.get_subject().ST = CA_ST
        cert.get_subject().L = CA_L
        cert.get_subject().O = CA_O
        cert.get_subject().OU = CA_OU
        cert.get_subject().CN = cn
        cert.set_serial_number(SERIAL_NUMBER)
        cert.gmtime_adj_notBefore(- TIME_UNIT * VALID_DAYS_BEFORE)
        cert.gmtime_adj_notAfter(TIME_UNIT * 365 * VALID_YEARS_AFTER)
        cert.set_issuer(cert.get_subject())
        # Generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, BYTES)
        # Signing certificate using key
        cert.set_pubkey(key)
        cert.sign(key, HASH_ALGORITHM)
        return cert, key

    @staticmethod
    def __write_cert_key_pair(cert, key, filename):
        """ Writes to disk the cert and key
        """
        cert_filename = '{0}.{1}'.format(filename, EXT_CERT)
        key_filename = '{0}.{1}'.format(filename, EXT_KEY)
        with open(cert_filename, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        logging.debug('Saved cert file: "{0}"'.format(cert_filename))

        with open(key_filename, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        logging.debug('Saved key file: "{0}"'.format(key_filename))

        return cert_filename, key_filename

    def gen_cert_key(self, cn, filename):
        """ Creates cert and key which are CA-signed
        """
        server_cert, server_key = self.__create_cert_key_pair(cn)
        # Signing server certificate using ca key
        server_cert.set_issuer(self.__ca_cert.get_subject())
        server_cert.sign(self.__ca_key, HASH_ALGORITHM)
        return self.__write_cert_key_pair(server_cert, server_key, filename)
