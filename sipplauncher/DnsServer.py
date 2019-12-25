#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2017 Samuel Colvin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
"""

from dnslib.server import DNSServer
from dnslib.proxy import ProxyResolver

class Resolver(ProxyResolver):
    def __init__():
        super().__init__("8.8.8.8", 53, 5)
        self.__records = dict()

    @staticmethod
    def __zone_lines(zone_file):
        current_line = ''
        for line in zone_file.open():
            if line.startswith('#'):
                continue
            line = line.rstrip('\r\n\t ')
            if not line.startswith(' ') and current_line:
                yield current_line
                current_line = ''
            current_line += line.lstrip('\r\n\t ')
        if current_line:
            yield current_line

    @staticmethod
    def __load_zones(zone_file):
        assert zone_file.exists(), f'zone files "{zone_file}" does not exist'
        logger.info('loading zone file "%s":', zone_file)
        zones = []
        for line in __zone_lines(zone_file):
            try:
                rname, rtype, args_ = line.split(maxsplit=2)

                if args_.startswith('['):
                    args = tuple(json.loads(args_))
                else:
                    args = (args_,)
                record = Record(rname, rtype, args)
                zones.append(record)
                logger.info(' %2d: %s', len(zones), record)
            except Exception as e:
                raise RuntimeError(f'Error processing line ({e.__class__.__name__}: {e}) "{line.strip()}"') from e
        logger.info('%d zone resource records generated from zone file', len(zones))
        return zones

    def resolve(self, request, handler):
        type_name = QTYPE[request.q.qtype]
        reply = request.reply()

        for records in self.__records.values():
            for record in records:
                if record.match(request.q):
                    reply.add_answer(record.rr)

        if reply.rr:
            logger.info('found zone for %s[%s], %d replies', request.q.qname, type_name, len(reply.rr))
            return reply

        # no direct zone so look for an SOA record for a higher level zone
        for record in self.records:
            if record.sub_match(request.q):
                reply.add_answer(record.rr)

        if reply.rr:
            logger.info('found higher level SOA resource for %s[%s]', request.q.qname, type_name)
            return reply

        logger.info('no local zone found, proxying %s[%s]', request.q.qname, type_name)
        return super().resolve(request, handler)

    def add(self, run_id, file):
        assert(run_id not in self.__records)
        self.__records[run_id] = self.load_zones(file)

    def remove(self, run_id):
        del self.__records[run_id]


class DnsServer(DNSServer):
    """
    Embedded DNS server
    """
    def __init__(self, domain):
        """
        :param domain: base domain
        :type domain: str
        """
        super().__init__(Resolver(domain))

    def add(self, run_id, file):
        self.server.resolver.add(run_id, file)

    def remove(self, run_id):
        self.server.resolver.remove(run_id)
