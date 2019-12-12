#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import logging
import threading
import pyroute2
from scapy.sendrecv import AsyncSniffer
from scapy.utils import wrpcap
from . import Network

class SIPpSniffer(object):
    """
    Provides functionality to provide network capturing traffic based on a 
    network interface and capturing filter
    """
    def __init__(self, interface):
        self.__interface = interface
        self.__folder = None
        # Delegate implementation to scapy.AsyncSniffer.
        # We don't inherit from scapy.AsyncSniffer, because scapy.AsyncSniffer requires more arguments on construction,
        # than we are ready to provide on construction of SIPpSniffer.
        self.__impl = None
        logging.debug('Created sniffer for interface {0}'.format(interface))

    def start(self, filter, folder):
        logging.debug('Starting sniffer for interface {0} and filter {1}'.format(self.__interface, filter))
        assert(not self.__impl)

        # Although Scapy docs say we could pass iface=None to sniff on all, this doesn't actually work.
        # Scapy listens on 1st available interface.
        # Therefore we need to collect list of interfaces by ourselves.
        ifaces = Network.SIPpNetwork.get_interfaces()
        if ifaces:
            class started:
                flag = False
                cond = threading.Condition()

            def started_callback():
                with started.cond:
                    started.flag = True
                    started.cond.notify()
                logging.debug('Started sniffer for interface {0}'.format(self.__interface))

            self.__folder = folder
            self.__impl = AsyncSniffer(filter=filter,
                                       iface=list(ifaces), # scapy waits for list(str), while we have set(str)
                                       started_callback=started_callback)
            self.__impl.start()
            # Need to wait for sniffing thread actually to start.
            # Otherwise we might start SIP dialogs when thread is not capturing yet,
            # and therefore miss to capture some initial messages.
            with started.cond:
                # Issue #35: Busy-loop wait.
                # Otherwise we could wait forever if Scapy threads terminates before setting the started.flag.
                # For example, due to exception inside it.
                while not started.flag:
                    started.cond.wait(1)
                    if not self.__impl.thread.is_alive():
                        raise Exception("Scapy thread has terminated while waiting for it to start")
        else:
            logging.debug('Found no available real interfaces to sniff for dummy interface {0}'.format(self.__interface))

    def stop(self):
        if self.__impl:
            logging.debug('Stopping sniffer for interface {0}'.format(self.__interface))

            # Issue #1: We can't use just AsyncSniffer.stop(join=True),
            # because sometimes deadlock happens in cases when we stop immediately after start (see comment in Issue #1 for details).
            # Likely this is a bug in scapy, which doesn't expect this kind of usage.
            #
            # Initially here we just stopped AsyncSniffer with:
            # super().stop(join=True)
            #
            # I believe the issue was as follows:
            # Main thread:
            # - enters SIPpSniffer.start()
            # - starts Scapy thread and blocks on started.cond.wait()
            # - Main thread is paused
            # - Scapy thread is entered
            # Scapy thread:
            # - enters AsyncSniffer._run()
            # - calls started_callback(), which calls started.cond.notify().
            # - Scapy thread is paused
            # - Main thread is resumed
            # Main thread:
            # - continues its work, quickly finishes and calls AsyncSniffer.stop()
            # - AsyncSniffer.stop() sets AsyncSniffer.continue_sniff = False
            # - blocks on self.thread.join()
            # - Main thread is paused
            # - Scapy thread is resumed
            # Scapy thread:
            # - sets self.continue_sniff = True
            # - enters sniffing loop
            #
            # Therefore, Main thread cancels Scapy thread by setting self.continue_sniff = False,
            # but due to very short run time of Main thread, Scapy thread hasn't entered its loop.
            # Scapy thread is then resumed and sets this flag back to True and enters the loop.
            # The loop runs forever.
            #
            # To workaround this, we call AsyncSniffer.stop() continuosly, to reliably cancel Scapy thread.
            # This way, we continuosly set the self.continue_sniff = False, until the Scapy thread terminates.
            while True:
                self.__impl.stop(join=False)
                self.__impl.join(timeout=1)
                if self.__impl.thread.isAlive():
                    logging.debug('Sniffing thread is still alive for interface {0}, re-trying stopping'.format(self.__interface))
                else:
                    break

            # Issue #58: Sort basing on timestamp
            time_sorted = sorted(self.__impl.results.res, key=lambda pkt: pkt.time)
            wrpcap(os.path.join(self.__folder, self.__interface + ".pcap"), time_sorted)

            # restore defaults to be able to start() again
            self.__impl = None
            self.__folder = None
