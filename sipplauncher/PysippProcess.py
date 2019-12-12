#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pysipp
import sys
import os
import logging
from multiprocessing import Process

import sipplauncher.utils.Log
from . import UA
from .Scenario import Scenario
from .utils.Signals import check_signal, SignalException
from .utils.Utils import is_tls_transport

# Tried following combinations:
#
# 1. Run SIPpTest as greenlet + direct invocation of pysipp:
# - pysipp doesn't support logging to several configurable log files
# - after applying gevent.monkey.patch_subprocess() it looks like working,
#   however when launching several pysipp processes concurrently I see random exceptions for random tests inside pysipp code,
#   from which it looks like pysipp is not thread-safe.
#
# 2. Run SIPpTest as greenlet + invocation of pysipp as Process:
# - Process inherits monkey-patched Python environment and I see random exceptions for random tests inside pysipp code.
#
# 3. Run SIPpTest as thread + direct invocation of pysipp:
# - pysipp doesn't support logging to several configurable log files
#
# 4. Run SIPpTest as Process + direct invocation of pysipp.
# - it works, however log file corruption is very likely to occur sooner or later,
#   because SIPpTest proceses might log to same log file (if this is configured).
#
# 5. Run SIPpTest as thread + invocation of pysipp as Process:
# - all's fine!
class PysippProcess(Process):
    def __init__(self, uas, folder, args):
        """
        :param uas: set of UA
        :type uas: set(UA)

        :param folder: temp folder of a test
        :type folder: str

        :param args: command-line arguments of application
        :type args: namespace
        """

        super().__init__()

        self.__uas = uas
        self.__folder = folder
        self.__args = args

        self.__pysipp_logger = pysipp.utils.get_logger()
        if self.__pysipp_logger.propagate:
            # User has configured log propagation to the upper layer.
            # Log propagation likely will end up writing to some single log file.
            # We will run in a multiprocessing.Process context.
            # This could lead to writing to the same log file concurrently from different processes.
            # This is not synchronized, so likely this will make log file full of garbage.
            # We don't want user to misinterpret results of such logging.
            raise Exception("Please specify propagate=0 in log config for pysipp module")

    def __init_logging(self):
        # https://bugs.python.org/issue6721
        # "The python logging module uses a lock to surround many operations.
        # This causes deadlocks in programs that use logging, fork and threading simultaneously."
        # For example, we have Process P1.
        # P1's thread T1 obtains logging lock L1 while logging.
        # Then P1's thread T2 forks a new multiprocessing.Process P2, which inherits L1 in locked state.
        # Then P2 tries to log, and stucks on L1, because noone will ever release it.
        # To workaround this, we acquire L1 before forking, and release L1 immediately after both in P1 and P2.
        logging._releaseLock()

        # Patch Pysipp logger to support DynamicFileHandler.
        # Patching should be done in the context of Process.run(),
        # Because pysipp's logger is not thread/multiprocess-safe.
        for h in self.__pysipp_logger.handlers[:]: # copy, because we may remove items inside cycle
            if not isinstance(h, sipplauncher.utils.Log.DynamicFileHandler):
                # DynamicFileHandler is specified by default in log config for "pysip" logger.
                # However, user has configured some other logging handler.
                # We are running in a multiprocessing.Process context.
                # Therefore user requests us to write to the same log file concurrently from different processes.
                # This is not synchronized, so likely this make log file full of garbage.
                # We don't want user to misinterpret results of such logging.
                # Therefore we explicitly exit and log an error to main log.
                raise Exception("Please specify class=sipplauncher.utils.Log.DynamicFileHandler in log config for pysipp module")
            h.set_folder(self.__folder)

    @staticmethod
    def __add_pysipp_args():
        """
        Adds new arguments, which vanilla Pysipp doesn't support.
        SIPp arguments, supported by Pysipp, are defined in pysipp.command.SippCmd._specparams.
        It's the static shared class member.
        Therefore we are able to patch it without having access to class instance.
        All UserAgent instances will inherit _specparams and will handle our new arguments.
        """
        def add_arg(fmtstr):
            # This is a copy-paste from pysipp.command.cmdstrtype()
            fieldname = list(pysipp.command.iter_format(fmtstr))[0][1]
            descr = pysipp.command.Field(fieldname, fmtstr)
            pysipp.command.SippCmd._specparams[fieldname] = descr
            setattr(pysipp.command.SippCmd, fieldname, descr)

        # Issue #50: Add TLS arguments
        add_arg(' -tls_cert {tls_cert}')
        add_arg(' -tls_key {tls_key}')
        add_arg(' -tls_ca {tls_ca}')
        add_arg(' -tls_crl {tls_crl}')
        add_arg(' -tls_version {tls_version}')

    def __run_scenario(self, run_id, call_count):
        """
        Run all UAs, which support given Run ID

        :param run_id: alphanumeric Run ID
        :type run_id: str

        :param call_count: a `-m` SIPp parameter
        :type call_count: int
        """
        agents = []
        for ua in self.__uas:
            scen = ua.get_scenario(run_id)
            if not scen:
               # This UA doesn't have scenario for this Run ID.
               # This is not an issue.
               # Just skip this UA for this Run ID.
               continue

            kwargs = {
                "logdir": ".", # we already did chdir()
                "scen_file": scen.get_filename(),
                "remote_host": self.__args.dut,
                "transport": self.__args.sipp_transport,
                "rate": self.__args.sipp_call_rate,
                "call_count": call_count,
                "recv_timeout": self.__args.sipp_recv_timeout,
                "local_host": ua.ip,
                "trace_message": True,
                "trace_error": True,
                "trace_calldebug": True,
                "trace_error_codes": True,
            }
            if self.__args.sipp_info_file:
                kwargs["info_file"] = self.__args.sipp_info_file

            # TLS
            if ua.get_tls_cert():
                kwargs["tls_cert"] = ua.get_tls_cert()
            if ua.get_tls_key():
                kwargs["tls_key"] = ua.get_tls_key()
            if self.__args.sipp_tls_version:
                kwargs["tls_version"] = self.__args.sipp_tls_version
            if is_tls_transport(self.__args.sipp_transport):
                kwargs["local_port"] = 5061
                kwargs["remote_port"] = 5061
            # end TLS

            if scen.get_role() == Scenario.Role.uac:
                client = pysipp.agent.client(**kwargs)
                agents.append(client)
            elif scen.get_role() == Scenario.Role.uas:
                server = pysipp.agent.server(**kwargs)
                agents.insert(0, server)  # servers are always launched first
            else:
                assert(False)

        assert(agents) # We shouln't even attempt to run Run ID, on which there are no UAs
        scen = pysipp.agent.Scenario(agents)
        scen()

    def __run_scenarios(self):
        # Collect all possible Run IDs among UAs
        run_ids = set()
        for ua in self.__uas:
            run_ids |= ua.get_run_ids()
        run_ids = sorted(run_ids)

        # Change directory to make extra sipp logs and sipp coredump appear in the test directory.
        # We're running in the context of spawned dedicated process, so changing directory won't affect other concurrently running tests.
        os.chdir(self.__folder)

        if len(run_ids) == 1:
            # We can rely on SIPp to repeat calls.
            self.__run_scenario(run_ids.pop(), self.__args.sipp_max_calls)
        else:
            # We can't rely on SIPp to repeat calls.
            # We should restart all run_ids for each new call.
            for i in range(self.__args.sipp_max_calls):
                for run_id in run_ids:
                    self.__run_scenario(run_id, 1)

    def run(self):
        ret = 0
        try:
            self.__init_logging()
        except:
            # We don't want to run without logging.
            # We can't log error to indicate the issue, because we are likely to cause deadlock or other disaster.
            # We can only return error code.
            ret = 1
        else:
            try:
                self.__add_pysipp_args()
                self.__run_scenarios()
                # Issue #39: This is an interruption point.
                # If user hits CTRL+C during sipp running, SIGINT is handled in sipplauncher: just global variable is set.
                # Then the signal is propagated to all processes in the same process group: both to PysippProcess and to sipp.
                # Sipp exits.
                # PysippProcess inherits signal handlers from sipplaucnher: just global variable is set.
                # Therefore we need to implicitly check this variable to react on a signal.
                check_signal() # throws SignalException if we got signal
            except pysipp.SIPpFailure as e:
                # Expected exception
                self.__pysipp_logger.info(e)
                ret = 2
            except SignalException as e:
                # Expected exception
                self.__pysipp_logger.info("Captured signal {0}".format(e))
                ret = 3
            except BaseException as e:
                # Unexpected exception
                self.__pysipp_logger.error(e, exc_info = True)
                ret = 4
        sys.exit(ret)