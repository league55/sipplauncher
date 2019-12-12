#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import signal
from functools import partial

DEFAULT_IGNORE_SIGNALS=[signal.SIGCHLD, signal.SIGCONT, signal.SIGURG, signal.SIGWINCH]

last_signal = None

# Issue #7: Capturing ALL possible POSIX signals.
class SignalException(Exception):
    pass

class SignalDesc:
    def __init__(self, name, num):
        self.name = name
        self.num = num

def capture_all_signals():
    def __sighandler(signame, signum, frame):
        # Issue #30: Sometimes deadlock happens on logging inside sighandler.
        # Application logs something, holding logging lock.
        # At this time it receives SIGCHLD.
        # Sighandler -> log -> tries to obtain logging lock -> deadlock.
        #
        # This is confirmed here: https://docs.python.org/2.7/library/logging.html#thread-safety
        # "If you are implementing asynchronous signal handlers using the signal module, you may not be able to use logging from within such handlers.
        # This is because lock implementations in the threading module are not always re-entrant, and so cannot be invoked from such signal handlers."
        #
        # NEVER LOG INSIDE SIGHANDLER!
        #
        # I was unable to print Traceback using 'frame' argument on Python-2.7.5.
        # 'frame' argument contains last stack frame.
        # However frame.f_back is None, so I was unable to loop and print over previous stack frames.
        # Maybe in Python-3 the things have changed, so we could get Traceback from frame argument.
        # Tried workaround: to raise the SignalException, which is caught in my_main_fun(),
        # and Traceback is printed from the exception - this works fine and produces meaningful output.
        # However, this caused deadlocks (see Issue #35).
        #
        # So, at the end:
        # 1. We cannot log here.
        # 2. We cannot raise exception here.
        # 3. We cannot get stacktrace of the moment when signal has bee caught.
        #
        # What we can do - is just to set global variable (last_signal).
        # This seems to be safe, and doesn't cause deadlocks.
        # The variable is checked outside of this module using check_signal().
        global last_signal
        last_signal = SignalDesc(signame, signum)

    # The idea is taken from
    # https://stackoverflow.com/questions/2148888/python-trap-all-signals
    # and slightly modified
    for i in [x for x in dir(signal) if x.startswith("SIG") and not x.startswith("SIG_")]:
        try:
            signum = getattr(signal, i)
            if signum in DEFAULT_IGNORE_SIGNALS:
                continue
            partial_sighandler = partial(__sighandler, i) # use partial to bind signal name as 1st argument of signal handler
            signal.signal(signum, partial_sighandler)
        except (OSError, RuntimeError, ValueError): # OSError for Python3, RuntimeError for 2, ValueError for SIG_IGN
            pass

def check_signal():
    """
    Issue #35: to fix deadlock issue, we disallow interrupting with a signal at any Python instruction.
    Instead, we have only a few interruption points in application, which check for a pending signal with check_signal(),
    """
    if last_signal:
        raise SignalException("{0}({1})".format(last_signal.name, last_signal.num))
