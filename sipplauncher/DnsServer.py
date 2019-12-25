#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

from dnslib import server

class DnsServer(dnslib.server.DNSServer):
    """
    Embedded DNS server
    """
    def __init__(self, domain):
        """
        :param domain: base domain
        :type domain: str
        """
        self.__domain = domain

    def add(self, run_id, ua_address_dict):
        assert(run_id not in __run_id_map)
        self.__run_id_map[run_id] = ua_address_dict

    def remove(self, run_id):
        del self.__run_id_map[run_id]
