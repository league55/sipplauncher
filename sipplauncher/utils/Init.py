#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import argparse
import json
import sys
import os
import logging

from . import Log
from .Defaults import (VERSION,
                      log_config_paths,
                      DEFAULT_GROUP,
                      DEFAULT_GROUP_PAUSE,
                      DEFAULT_NETWORK_MASK,
                      DEFAULT_TESTSUITE,
                      DEFAULT_TESTSUITE_TEMPLATES,
                      DEFAULT_SIPP_INFO_FILE)

from .Utils import (which, is_tls_transport)
from .CAOpenSSL import CAOpenSSL


def get_stamped_id():
    ret = '{0} {1}'.format('sipplauncher', VERSION)
    return ret


def init_logging(stamped_id):
    # Lets init the log handlers
    try:
        Log.init_log(log_config_paths, stamped_id)
    except Exception as err:
        msg = 'Logging setup error. %s\n' % (err)
        sys.stderr.write(msg)
        sys.exit(1)


def generate_parser():
    """ Defines the input parameters parsing argc/argv
    """
    def valid_file_path(path):
        """
        Checks if file path is a valid path to file.
        """
        if not os.path.isfile(path):
            parser.error('File "{0}" doesnt exist'.format(path))
        return path

    def valid_abs_file_path(path):
        """
        Checks if file path (possibly relative path) is a valid path to file.
        Converts to absolute path.
        It's useful when need to convert user-supplied argument to abspath,
        for example, before chdir().

        :param file_path: User-supplied command-line argument
        :type file_path: str

        :return: absolute path of file_path
        :rtype: str
        """
        if not os.path.isfile(path):
            parser.error('File "{0}" doesnt exist'.format(path))
        return os.path.abspath(path)

    prog_name = 'sipplauncher'

    usage = prog_name + ' TODO'

    parser = argparse.ArgumentParser(prog=prog_name, description=usage)
    parser.add_argument("-v", "--version", help="product version", action="version", version=get_stamped_id())

    # Mandatory args
    parser.add_argument("--dut", help="device under test IP address")
    parser.add_argument("--testsuite", help="path to the SIPp testpool folder. Default: \"<current_working_directory>/{0}\"".format(DEFAULT_TESTSUITE))

    # Other args
    parser.add_argument("--template-folder", help="path to folder with templates. Default: \"<testsuite>/{0}\"".format(DEFAULT_TESTSUITE_TEMPLATES))
    parser.add_argument("--pattern-exclude", action="append", help="regular expression to exclude tests (if used with \"only\" arg, and a test name matches both, the test is excluded)")
    parser.add_argument("--pattern-only", action="append", help="regular expression to specify the only tests which should be run (if used with \"exclude\" arg, and a test name matches both, the test is excluded)")
    parser.add_argument("--network-mask", type=int, default=DEFAULT_NETWORK_MASK,
                        help="network mask. Default: \"{0}\"".format(DEFAULT_NETWORK_MASK))
    parser.add_argument("--group", type=int, default=DEFAULT_GROUP,
                        help="number of SIPp tests to be run at the same time. Default: \"{0}\"".format(DEFAULT_GROUP))
    parser.add_argument("--group-pause", type=int, default=DEFAULT_GROUP_PAUSE,
                        help="pause between group executions. Default: \"{0}\"".format(DEFAULT_GROUP_PAUSE))
    parser.add_argument("--group-stop-first-fail", help="stops after any test of the group fails", action="store_true")
    parser.add_argument("--total", type=int, help="total number of SIPp tests to run")
    parser.add_argument("--random", help="selects randomly tests from the testpool (instead of alphabetical consecutive ordering)", action="store_true")
    parser.add_argument("--dry-run", help="dry run, simulates an execution", action="store_true")
    parser.add_argument("--fail-expected", help="ok if the execution fails", action="store_true")
    parser.add_argument("--leave-temp", help="Leave temporary directories in which tests are executed", action="store_true")
    parser.add_argument("--keyword-replacement-values", type=json.loads, help="Custom keyword values in JSON object format to be used to replace values in scripts and SIPp scenarios (sed-like)")
    parser.add_argument("--no-pcap", help="Disable capturing to pcap files", action="store_true")
    parser.add_argument("--tls-ca-root-cert", help="TLS CA root certificate file (.pem format). Must be used together with \"tls-ca-root-key\" arg", type=valid_file_path)
    parser.add_argument("--tls-ca-root-key", help="TLS CA root key file (.pem format). Must be used together with \"tls-ca-root-key\" arg", type=valid_file_path)

    # SIPp args
    parser.add_argument("--sipp-transport", help="SIPp -t param. Default is 'l1' if TLS is requested, otherwise 'u1'", choices=['u1', 'un', 'ui', 't1', 'tn', 'l1', 'ln'])
    parser.add_argument("--sipp-info-file", help="SIPp -inf param", type=valid_abs_file_path)
    parser.add_argument("--sipp-call-rate", help="SIPp -r param", type=float, default=1.0)
    parser.add_argument("--sipp-max-calls", help="SIPp -m param", type=int, default=1)
    parser.add_argument("--sipp-recv-timeout", help="SIPp -recv_timeout param", type=int, default=5000)
    parser.add_argument("--sipp-tls-version", help="SIPp -tls_version param", choices=['1.0', '1.1', '1.2'], default=None)

    return parser



def is_sipp_installed():
    ret = which("sipp")
    return ret


def _exit_with_error(msg):
    sys.stdout.write(msg + '\n')
    sys.stderr.write(msg + '\n')
    sys.exit(1)


def check_and_patch_args(args):
    def _check_is_dir(path):
        if not os.path.isdir(path):
            msg = 'Folder "{0}" doesnt exist\n'.format(path)
            _exit_with_error(msg)

    if args.testsuite:
        _check_is_dir(args.testsuite)
    elif os.path.isdir(DEFAULT_TESTSUITE):
        args.testsuite = DEFAULT_TESTSUITE
        logging.info("Auto-selected test suite: {0}".format(args.testsuite))
    else:
        _exit_with_error("Please provide test suite location (--testsuite arg)\n")

    if not args.dut:
        _exit_with_error('Please provide device under test (--dut arg)\n')

    if args.template_folder:
        _check_is_dir(args.template_folder)
    else:
        template_folder = os.path.join(args.testsuite, DEFAULT_TESTSUITE_TEMPLATES)
        if os.path.isdir(template_folder):
            args.template_folder = template_folder

    if not args.sipp_info_file:
        info_file = os.path.join(args.testsuite, DEFAULT_SIPP_INFO_FILE)
        if os.path.isfile(info_file):
            args.sipp_info_file = os.path.abspath(info_file)

    if not args.sipp_transport:
        args.sipp_transport = "l1" if args.tls_ca_root_cert else "u1"
        logging.info("Auto-selected transport: {0}".format(args.sipp_transport))

    # check TLS arguments
    args.sipplauncher_ca = None
    if args.tls_ca_root_cert:
        if not args.tls_ca_root_key:
            _exit_with_error('--tls-ca-root-cert requires tls-ca-root-key arg')
        elif not is_tls_transport(args.sipp_transport):
            _exit_with_error('--sipp-transport {0} is not compatible with --tls-ca-root-cert arg'.format(args.sipp_transport))
        args.sipplauncher_ca = CAOpenSSL(args.tls_ca_root_cert, args.tls_ca_root_key)
    elif args.tls_ca_root_key:
        _exit_with_error('--tls-ca-root-key requires tls-ca-root-cert arg')
    elif args.sipp_tls_version:
        _exit_with_error('--sipp-tls-version requires --tls-ca-root-cert arg')
    elif is_tls_transport(args.sipp_transport):
        args.sipplauncher_ca = CAOpenSSL()


def setup():
    """ Performs the initial setup for the project: inits logging and parses
    command-line arguments.

    :returns:  opts, conf.

    """

    stamped_id = get_stamped_id()

    # Let's parse input params
    parser = generate_parser()
    args = parser.parse_args()

    init_logging(stamped_id)

    if not is_sipp_installed():
        _exit_with_error('Error. sipp executable not found. Please verify it is installed\n')

    check_and_patch_args(args)

    return args


if __name__ == '__main__':
    pass
