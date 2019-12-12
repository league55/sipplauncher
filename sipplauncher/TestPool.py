#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import glob
from sipplauncher.Test import SIPpTest
import logging
import re
import os
import sys

import sipplauncher.utils.Utils

class TestPool(object):
    class CollectException(Exception):
        pass

    @staticmethod
    def collect(args):
        # Layout:
        # folder/
        # |--test1/
        # |  |-- uac_ua0.xml
        # |  |-- uac_ua0.xml
        # |  |-- uac_ua1.xml
        # |  |-- uas_ua0.xml
        # |--test2/
        #    |-- uac_ua0.xml
        #    |-- uas_ua0.xml
        array_regex_exclude = [re.compile(regex) for regex in args.pattern_exclude] if args.pattern_exclude else None
        array_regex_only = [re.compile(regex) for regex in args.pattern_only] if args.pattern_only else None

        if not os.path.isdir(args.testsuite):
            raise TestPool.CollectException('"{0}" is not a directory'.format(args.testsuite))

        test_pool = []

        logging.debug("Looking for tests at '{0}'".format(args.testsuite))
        root, dirs, files = next(os.walk(args.testsuite))
        for dir in sorted(dirs):
            test_folder = os.path.join(args.testsuite, dir)

            if args.template_folder:
                if os.path.abspath(test_folder) == os.path.abspath(args.template_folder):
                    # Don't treat folder with templates as a regular test.
                    # Skip it.
                    continue

            def is_test_allowed(test_name):
                def does_test_match_regex_array(regex_array, test_name):
                    matched = False
                    # If test name matches any of patterns -
                    # it's considered matched
                    for regex in regex_array:
                        if regex.match(test_name):
                            matched = True
                            break
                    return matched

                allowed = True
                if array_regex_exclude:
                    allowed = not does_test_match_regex_array(array_regex_exclude, test_name)
                if allowed and array_regex_only:
                    allowed = does_test_match_regex_array(array_regex_only, test_name)
                return allowed

            if not is_test_allowed(dir):
                # Not allowed by pattern-exclude or pattern-only option
                continue

            test_pool.append(SIPpTest(test_folder))

        if not test_pool:
            raise TestPool.CollectException("No tests found")

        return test_pool
