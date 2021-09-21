#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import pysipp
import sys
import os
import logging
import resource
import copy
from multiprocessing import Process

import sipplauncher.utils.Log
from . import UA
from .Scenario import Scenario
from .utils.Signals import check_signal, SignalException
from .utils.Utils import is_tls_transport
from .utils.Defaults import log_config_paths
from .utils.Init import get_stamped_id

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

        # Issue #51: We can't pass `CAOpenSSL` instance as a `Process` member to a Forkserver,
        # because it contains `ca_cert/ca_key` members, which are not sendable via a Unix socket.
        # We get this exception: "can't pickle _cffi_backend.CDataGCP objects" on sending `Process` to a Forkserver.
        # And actually we don't need to pass `CAOpenSSL` instance to a forked child process - it's not used there.
        # Therefore we can just remove it from the `args` Namespace.
        self.__args = copy.copy(args)  # copy to not to remove `sipplauncher_ca` from the original `args` Namespace
        self.__args.sipplauncher_ca = None

        pysipp_logger = pysipp.utils.get_logger()
        if pysipp_logger.propagate:
            # User has configured log propagation to the upper layer.
            # Log propagation likely will end up writing to some single log file.
            # We will run in a multiprocessing.Process context.
            # This could lead to writing to the same log file concurrently from different processes.
            # This is not synchronized, so likely this will make log file full of garbage.
            # We don't want user to misinterpret results of such logging.
            raise Exception("Please specify propagate=0 in log config for pysipp module")
        for h in pysipp_logger.handlers:
            if not isinstance(h, sipplauncher.utils.Log.DynamicFileHandler):
                # DynamicFileHandler is specified by default in log config for "pysip" logger.
                # However, user has configured some other logging handler.
                # We are running in a multiprocessing.Process context.
                # Therefore user requests us to write to the same log file concurrently from different processes.
                # This is not synchronized, so likely this make log file full of garbage.
                # We don't want user to misinterpret results of such logging.
                # Therefore we explicitly exit and log an error to main log.
                raise Exception("Please specify class=sipplauncher.utils.Log.DynamicFileHandler in log config for pysipp module")

    def __init_logging(self):
        # Issue #45: We're running in a fresh Process.
        # Logging handles haven't been copied from parent process,
        # because we're using 'forkserver' Process start method.
        # Therefore we need to initialize logging once again.
        sipplauncher.utils.Log.init_log(log_config_paths,
                                        get_stamped_id(),
                                        quiet=True)   # don't report again about logging has been initialized

        # Issue #45: We're running in a fresh Process now.
        # Therefore, we can initialize self.__pysipp_logger now.
        # We can't initialize self.__pysipp_logger in __init__(), because `Logger` contains locks.
        # `Multiprocessing`, when used in 'forkserver' start method, sends `Process` object to a Forkserver.
        # Sending an embedded lock object to a Forkserver could cause deadlock.
        # `Multiprocessing` raises an exception when we try to do it.
        self.__pysipp_logger = pysipp.utils.get_logger()

        # Patch Pysipp logger to support DynamicFileHandler.
        # Patching should be done in the context of Process.run(),
        # Because pysipp's logger is not thread/multiprocess-safe.
        for h in self.__pysipp_logger.handlers:
            assert(isinstance(h, sipplauncher.utils.Log.DynamicFileHandler))  # checked at __init__()
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
        def add_arg(item):
            # This is a copy-paste from pysipp.command.cmdstrtype()
            if isinstance(item, tuple):
                fmtstr, descrtype = item
            elif isinstance(item, pysipp.command.Field):
                fieldname = item.name
                pysipp.command.SippCmd._specparams[fieldname] = item
                setattr(pysipp.command.SippCmd, fieldname, item)
                return
            else:
                fmtstr, descrtype = item, pysipp.command.Field

            fieldname = list(pysipp.command.iter_format(fmtstr))[0][1]
            descr = descrtype(fieldname, fmtstr)
            pysipp.command.SippCmd._specparams[fieldname] = descr
            setattr(pysipp.command.SippCmd, fieldname, descr)

        # Issue #50: Add TLS arguments
        add_arg(' -tls_cert {tls_cert}')
        add_arg(' -tls_key {tls_key}')
        add_arg(' -tls_ca {tls_ca}')
        add_arg(' -tls_crl {tls_crl}')
        add_arg(' -tls_version {tls_version}')

        # Issue #23: Need for TCP tests to work
        add_arg(' -max_socket {max_socket}')

        # Monitor stats
        add_arg((' -trace_stat {trace_stat}', pysipp.command.BoolField))
        add_arg(' -stf {trace_file}')
        add_arg(' -fd {trace_frequency}')

        # 3pcc Extended support
        add_arg(' -master {master_no}')
        add_arg(' -slave {slave_no}')
        add_arg(' -slave_cfg {slave_cfg}')


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
            delayed_uac_start = False
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

            # Issue #23: We need to adjust SIPp's "max_socket" argument to pass SIPp's internal check.
            # We use the same formula as it exists in the SIPp's source code.
            #
            # Otherwise SIPp exits with the following error message:
            # "Maximum number of open sockets (50000) should be less than the maximum number of open files (1024).
            # Tune this with the `ulimit` command or the -max_socket option.
            # Maximum number of open sockets (1024) plus number of open calls (1) should be less than the maximum number of open files (1024) to allow for media support."
            kwargs["limit"] = self.__args.sipp_concurrent_calls_limit
            soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
            if soft <= self.__args.sipp_concurrent_calls_limit:
                raise Exception("Open files limit {0} is too small. Please increase the limit to at least {1} (ulimit -n {1})".format(soft, sipp_concurrent_calls_limit + 1))
            kwargs["max_socket"] = soft - self.__args.sipp_concurrent_calls_limit
            kwargs["trace_stat"] = True
            kwargs["trace_file"] = scen.get_tracefile()
            kwargs["trace_frequency"] = "60"

            if self.__args.sipp_info_file:
                kwargs["info_file"] = self.__args.sipp_info_file

            if self.__args.default_behaviors:
                kwargs["default_behaviors"] = self.__args.default_behaviors

            # 3pcc Extended support
            _3pcc_id = ua.get_3pcc_id()
            if _3pcc_id is not None:
                self.__pysipp_logger.debug('Current ua {0} is using 3pcc extended mode with id {1}'.format(ua.get_scenario, _3pcc_id))
                kwargs["slave_cfg"] = ua.get_3pcc_file()
                if _3pcc_id == 'm':
                    kwargs["master_no"] = _3pcc_id
                else:
                    kwargs["slave_no"] = _3pcc_id
                    delayed_uac_start = True


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
                if delayed_uac_start:
                    # It's a uac, but there might be a 3PCC master uac that must be the last one started
                    agents.insert(-1, client)
                else:
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
            run_ids |= ua.get_part_ids()
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
