#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

from sipplauncher.Network import SIPpNetwork

# Issue #64: ARP ping of localhost might work in some cases.
# And it won't work in another cases.
# Therefore unit-test of this kind doesn't make sense.
# Leaving the code commented out
# to notify whoever may attempt to add similar test in the future.
#
#def test_arp_ping_localhost():
#    """Testing if localhost is ARP-pingable
#    """
#    assert(not SIPpNetwork._SIPpNetwork__arp_ping("127.0.0.1"))

def test_arp_ping_fake_ip():
    """Testing if fake IP is ARP-pingable
    """
    assert(not SIPpNetwork._SIPpNetwork__arp_ping("1.1.1.1"))

def test_arp_ping_gateways():
    """Testing if gateways are ARP-pingable
    """
    for gw in SIPpNetwork._SIPpNetwork__get_gateways():
        assert(SIPpNetwork._SIPpNetwork__arp_ping(gw))
