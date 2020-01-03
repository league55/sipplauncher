#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import logging
import time
import os
import random

#from sipplauncher.utils.Exceptions import (UriNotFound,
#                                           UriDoesntMatch,
#                                           UnableReadResponse)

from sipplauncher.TestPool import (TestPool)
from .utils.Signals import check_signal
from .utils.Utils import is_pcap


import threading
import copy
import collections

Task = collections.namedtuple('Task', ['thread', 'test', 'run_id_prefix'])

logger = logging.getLogger(__name__)

PCAP_SYNC_TIMEOUT = 1 # sec

def _sep(char='='):
    """DRY helper to print a terminal separator"""
    logger.info(char * 80)


def run(args):
    """ Collects and runs all the tests. Main function
    """

    # Lets grab a proper log
    logger = logging.getLogger(__name__)

    # Init ret code - optimistic
    ret_code = 0

    # Collect all the tests
    try:
        start = time.time()
        test_pool = TestPool.collect(args)
    except Exception as err:
        logger.error('Error when collecting tests. {0}'.format(err))
        logger.debug(err, exc_info = True)
        ret_code = 1
    else:
        count_group = 0
        count_total, count_fail = 0, 0

        # We need to execute total number of SIPpTest in groups
        # (group contains several SIPpTest and are executed at the same time)
        total = args.total if args.total else len(test_pool)
        group = args.group

        # Fancy logging wording
        postfix =  'tests (in groups of {0})'.format(group) if group < total else 'tests in one group'
        msg = 'Ready to run {0} {1}'.format(total, 'test' if total == 1 else postfix)
        logger.info(msg)

        # Fancy logging output
        _sep()
        needs_group_sep_printed = False

        while count_total < total:
            # Issue #35: This is an interruption point.
            check_signal() # throws SignalException if we got signal since last check

            # Fancy logging output
            if needs_group_sep_printed:
                _sep(char='-')
            needs_group_sep_printed = True

            # We dont want to execute more tests than the total set by the user
            if count_total + group > total:
                range_helper = total - count_total
            else:
                range_helper = group

            msg = 'Starting new group execution #{0} (tests from {1} to {2} - '.format(count_group,
                                                                                       count_total,
                                                                                       count_total + range_helper)
            msg += ' total {0})'.format(total)
            logger.debug(msg)
            tasks = []

            for block in range(range_helper):

                # Selects proper test based on order strategy chosen (random or linear/ring)
                if args.random:
                    test_from_testpool = random.choice(test_pool)
                    msg = 'Picked random test from test pool due to command-line argument, key:"{0}"'.format(test_from_testpool.key)
                    logger.debug(msg)
                else:
                    test_from_testpool = test_pool[count_total % len(test_pool)]

                # Getting a local copy of the test from the testpool
                test = copy.copy(test_from_testpool)

                thread = threading.Thread(target=test.run, args=(count_total, args))

                # We have several reasons to make thread a daemon:
                # 1. We want thread to automatically exit when main thread ends - this is the feature of daemon threads.
                # 2. Scapy creates daemon thread too, and we don't want to mix daemon and non-daemon threads for the sake of simplicity.
                thread.setDaemon(True)

                tasks.append(Task(thread, test, count_total))
                count_total += 1

            try:
                # Pre run hook for each test
                for task in tasks:
                    task.test.pre_run(task.run_id_prefix, args)

                # Issue #69: Need to wait a bit after sniffing thread has been started.
                # Otherwise we might miss first SIP packets.
                if is_pcap(args):
                    time.sleep(PCAP_SYNC_TIMEOUT)

                # Need to start all the threads
                for task in tasks:
                    task.thread.start()

                # And patiently wait for them
                for task in tasks:
                    task.thread.join()
            finally:
                # Issue #59: Need to defer a bit sniffing thread stopping to catch last packets, if any.
                # Otherwise following cases sometime happens:
                # 1) last packets are read by sipp from TCP/IP socket
                # 2) sipp exits
                # 3) we regain control and stop sniffing (inside post_run())
                # 4) last packets (from i.1) arrive at BPF socket with few milliseconds delay - but we don't catch them!
                # We can't synchronize BPF and TCP/IP socket, so we can only defer stopping sniffing...
                if is_pcap(args):
                    time.sleep(PCAP_SYNC_TIMEOUT)

                # Post run hook for each test.
                # Issue #12: We need to ALWAYS run this hook if pre_run() has been run,
                # in order to cleanup in case of exception or signal caught.
                # We can't rely on ContextManagers inside SIPpTest for this,
                # because SIPpTest.run() runs in the context of a thread.
                # If exception happens after SIPpTest.run() has yielded control,
                # under scope of ContextManager (for ex. "with ContextManager():"), ContextManager.__exit__ isn't called.
                #
                # Issue #4: reverse the list to have proper cleanup order when provisioning some global DUT options.
                # For ex., we have been requested by a user to have 2 concurrent tests running with the "--group 2" command-line argument.
                # Both tests are going to save, alter and restore same global DUT option, say OptionA, which has some original value ValueOrig.
                # We need to restore the global DUT option at the aplication exit.
                # Thus, we need to have the following order in this case:
                # 1. TestA pre-run. OptionA: ValueOrig -> ValueA
                # 2. TestB pre-run. OptionA: ValueA -> ValueB
                # 3. TestA run + TestB run
                # 4. TestB post-run. OptionA: ValueB -> ValueA
                # 5. TestA post-run: OptionB: ValueA -> ValueOrig
                last_exception = None
                for task in reversed(tasks):
                    try:
                       task.test.post_run(task.run_id_prefix, args)
                    except BaseException as e:
                       last_exception = e
                if last_exception:
                    # Notify user and stop
                    raise last_exception

            # Calculating failed tests
            for task in tasks:
                if task.test.failed():
                    count_fail += 1

            # Checking stop if any failed test found arg
            if args.group_stop_first_fail and count_fail:
                logging.error('Failed test detected, leaving due to command-line argument')
                break

            # Giving some pause, if this is not the last iteration
            if count_total < total:
                time.sleep(args.group_pause)

            count_group += 1

        # Wrap up timing
        end = time.time()
        elapsed = end - start

        # Print summary and exit
        _sep()
        logger.info('TOTAL: {0}'.format(count_total))
        if not args.dry_run:
            logger.info('SUCCESS: {0}'.format(count_total - count_fail))
            logger.info('FAILED: {0}'.format(count_fail))
        _sep()
        logger.info('Total time elapsed %.0fs' % (elapsed))

        # Returning proper exit code if required
        if count_fail:
            ret_code = 1

        # Are we expecting this execution to fail?
        if args.fail_expected:
            ret_code = 0 if ret_code > 0 else 1

    # Exit with proper return code
    return ret_code
