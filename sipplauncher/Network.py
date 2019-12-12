#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import random
import ipaddress
from scapy.sendrecv import srp
from scapy.layers.l2 import Ether, ARP
import pyroute2
from socket import AF_INET
from . import Sniffer

class IPNotAvailable(Exception):
    pass


logger = logging.getLogger("sipplaunchernetwork")


IFACE_PREFIX = 'sipp'

class DUT(ipaddress.IPv4Interface):
    """ The Device Under Test IP (likely not to be in this box -> no need to have the interface)
    """

    def __str__(self):
        ret = '<ip:"{0}" network:"{1}"">'.format(self.ip, self.network)
        return ret


def force_cleanup():
    """ Removes all the interfaces with our configured prefix
    """
    with pyroute2.IPRoute() as ip_route:
        logger.debug('Deleting all interface named:"*{0}*"'.format(IFACE_PREFIX))
        for link in ip_route.get_links():
            ifname = link['attrs'][0][1]
            if IFACE_PREFIX in ifname:
                try:
                    logger.debug('Removed interface adapter:"{0}"'.format(ifname))
                    ip_route.link("del", index=link['index'])
                except:
                    raise
                else:
                    logger.debug('Cleaning interface adapter:"{0}"'.format(ifname))


class SIPpNetwork():
    """ Represents a LAN Network where sipp scenario can be run
    """
    def __init__(self, dut, mask, interface):

        self.dut = DUT(u'{0}/{1}'.format(dut, mask))

        # Interface name always have our prefix
        self.interface = '{0}-{1}'.format(IFACE_PREFIX, interface)
        # Stop if exists
        SIPpNetwork._check_available_interface(interface)
        # Creating interface adapter for real
        with pyroute2.IPRoute() as ip_route:
            try:
                logger.debug('Creating interface adapter:"{0}"'.format(self.interface))
                ip_route.link("add", kind="dummy", ifname=self.interface)
            except:
                logger.error('Problem found creating interface adapter:"{0}"'.format(self.interface))
                raise
            else:
                logger.debug('Created interface adapter:"{0}"'.format(self.interface))

        self.ips = []
        self.__sniffer = Sniffer.SIPpSniffer(self.interface)

    @staticmethod
    def _check_available_interface(interface):
        ret = None
        with pyroute2.IPRoute() as ip_route:
            if len(ip_route.link_lookup(ifname=interface)) == 0:
                logger.debug('interface adapter name "{0}" is available'.format(interface))
                ret = True
            else:
                msg = 'interface adapter name "{0}" already exists'.format(interface)
                logger.error(msg)
                raise Exception(msg)
        return ret

    def __str__(self):
        ret = '<dut:"{0}" interface:"{1}" ips:"{2}">'.format(self.dut, self.interface, self.ips)
        return ret                

    def add_random_ip(self):
        # Find a random IP
        ip = SIPpNetwork._get_random_available_ip(self.dut.network)
        logger.debug('Picked a random IP to generate the UA: "{0}"'.format(ip))
        # Creating interface adapter
        with pyroute2.IPRoute() as ip_route:
            try:
                logger.debug('Adding IP:"{0}" to interface:"{1}"'.format(ip, self.interface))
                index = ip_route.link_lookup(ifname=self.interface)[0]
                ip_route.addr('add', index, address=str(ip), mask=self.dut.network.prefixlen)
            except:
                logger.error('Problem found adding IP:"{0}" to interface:"{1}"'.format(ip, self.interface))
                raise
            else:
                logger.debug('Created IP:"{0}" in interface adapter:"{1}"'.format(ip, self.interface))
                self.ips.append(ip)
                return str(ip)

    @staticmethod
    def get_interfaces():
        """
        :returns: Names of interfaces, which are currently UP
        :rtype: set(str)
        """
        ifaces = set()
        with pyroute2.IPRoute() as ip_route:
            for link in ip_route.get_links():
                if link["state"] == "up":
                    for name, value in link["attrs"]:
                        if name == "IFLA_IFNAME":
                            ifaces.add(value)
        return ifaces

    @staticmethod
    def __arp_ping(ip):
        """ Performs ARP-ping on L2.
        http://www.aviran.org/arp-ping-with-python-and-scapy/

        :returns: True if ARP-ping succeeds, False if fails
        :rtype: bool
        """
        ret = False
        ifaces = SIPpNetwork.get_interfaces()
        for iface in ifaces:
            answered, unanswered = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip),
                                       timeout=0.1, # seconds
                                       verbose=False,
                                       iface=iface)
            if answered:
                ret = True
                break
        return ret

    @staticmethod
    def __get_gateways():
        gateways = set()
        with pyroute2.IPRoute() as ip_route:
            for route in ip_route.get_routes(family=AF_INET):
                for name, value in route["attrs"]:
                    if name == "RTA_GATEWAY":
                        gateways.add(value)
        return gateways

    @staticmethod
    def __get_local_ip_addresses():
        ips = set()
        with pyroute2.IPRoute() as ip_route:
            for addr in ip_route.get_addr(family=AF_INET):
                 for name, value in addr["attrs"]:
                    if name == "IFA_ADDRESS":
                        ips.add(value)
        return ips

    @staticmethod
    def _get_random_available_ip(network):
        assigned_ips = SIPpNetwork.__get_gateways() | SIPpNetwork.__get_local_ip_addresses()
        ret = None
        hosts = list(ipaddress.IPv4Network(network).hosts())
        random.shuffle(hosts)
        for ip in hosts:
            if str(ip) in assigned_ips:
                logger.debug('IP "{0}" is already assigned'.format(ip))
            else:
                if not SIPpNetwork.__arp_ping(str(ip)):
                    logger.debug('IP "{0}" is down, we can use it'.format(ip))
                    ret = ip
                    break
                logger.debug('IP "{0}" is up, continue searching'.format(ip))
        if not ret:
            raise IPNotAvailable('Unable to find an available ip')
        return ret

    def sniffer_start(self, folder):
        filter = "host ({0})".format(" or ".join(str(ip) for ip in self.ips))
        self.__sniffer.start(filter, folder)

    def sniffer_stop(self):
        self.__sniffer.stop()

    def shutdown(self):
        # Deleting interface adapter
        with pyroute2.IPRoute() as ip_route:
            try:
                logger.debug('Deleting interface adapter:"{0}"'.format(self.interface))
                index = ip_route.link_lookup(ifname=self.interface)[0]
                ip_route.link("del", index=index)
            except IndexError:
                logger.warning('When removing, unable to find adapter:"{0}"'.format(self.interface))
                pass
            # raise
            except:
                logger.error('Problem found deleting interface adapter:"{0}"'.format(self.interface))
                raise
            else:
                logger.debug('Deleted interface adapter:"{0}"'.format(self.interface))
