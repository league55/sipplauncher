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


TYPE_LOOKUP = {
    'A': (dns.A, QTYPE.A),
    'AAAA': (dns.AAAA, QTYPE.AAAA),
    'CAA': (dns.CAA, QTYPE.CAA),
    'CNAME': (dns.CNAME, QTYPE.CNAME),
    'DNSKEY': (dns.DNSKEY, QTYPE.DNSKEY),
    'MX': (dns.MX, QTYPE.MX),
    'NAPTR': (dns.NAPTR, QTYPE.NAPTR),
    'NS': (dns.NS, QTYPE.NS),
    'PTR': (dns.PTR, QTYPE.PTR),
    'RRSIG': (dns.RRSIG, QTYPE.RRSIG),
    'SOA': (dns.SOA, QTYPE.SOA),
    'SRV': (dns.SRV, QTYPE.SRV),
    'TXT': (dns.TXT, QTYPE.TXT),
    'SPF': (dns.TXT, QTYPE.TXT),
}


class Record:
    def __init__(self, rname, rtype, args):
        self._rname = DNSLabel(rname)

        rd_cls, self._rtype = TYPE_LOOKUP[rtype]

        if self._rtype == QTYPE.SOA and len(args) == 2:
            # add sensible times to SOA
            args += (SERIAL_NO, 3600, 3600 * 3, 3600 * 24, 3600),

        if self._rtype == QTYPE.TXT and len(args) == 1 and isinstance(args[0], str) and len(args[0]) > 255:
            # wrap long TXT records as per dnslib's docs.
            args = wrap(args[0], 255),

        if self._rtype in (QTYPE.NS, QTYPE.SOA):
            ttl = 3600 * 24
        else:
            ttl = 300

        self.rr = RR(
            rname=self._rname,
            rtype=self._rtype,
            rdata=rd_cls(*args),
            ttl=ttl,
        )

    def match(self, q):
        return q.qname == self._rname and (q.qtype == QTYPE.ANY or q.qtype == self._rtype)

    def sub_match(self, q):
        return self._rtype == QTYPE.SOA and q.qname.matchSuffix(self._rname)

    def __str__(self):
        return str(self.rr)


class Resolver(ProxyResolver):
    def __init__():
        super().__init__("8.8.8.8", 53, 5)
        self.__run_id_map = dict()

    @staticmethod
    def __load(file):
        assert(os.path.exists(file))
        logger.info('loading DNS file "%s":', file)
        records = []
        with open(file, 'r') as f:
            for line in f:
                try:
                    if line.startswith('#'):
                        continue

                    line.strip('\r\n\t ')

                    rname, rtype, args_ = line.split(maxsplit=2)
                    if args_.startswith('['):
                        args = tuple(json.loads(args_))
                    else:
                        args = (args_,)

                    record = Record(rname, rtype, args)
                    records.append(record)
                    logger.info(' %2d: %s', len(records), record)
                except Exception as e:
                    raise RuntimeError(f'Error processing line ({e.__class__.__name__}: {e}) "{line.strip()}"') from e

        logger.info('%d zone resource records generated from file', len(records))
        return records

    def resolve(self, request, handler):
        type_name = QTYPE[request.q.qtype]
        reply = request.reply()

        for records in self.__run_id_map.values():
            for record in records:
                if record.match(request.q):
                    reply.add_answer(record.rr)

        if reply.rr:
            logger.info('found zone for %s[%s], %d replies', request.q.qname, type_name, len(reply.rr))
            return reply

        # no direct zone so look for an SOA record for a higher level zone
        for records in self.__run_id_map.values():
            for record in records:
                if record.sub_match(request.q):
                    reply.add_answer(record.rr)

        if reply.rr:
            logger.info('found higher level SOA resource for %s[%s]', request.q.qname, type_name)
            return reply

        logger.info('no local zone found, proxying %s[%s]', request.q.qname, type_name)
        return super().resolve(request, handler)

    def add(self, run_id, file):
        assert(run_id not in self.__run_id_map)
        self.__run_id_map[run_id] = self.__load(file)

    def remove(self, run_id):
        del self.__run_id_map[run_id]


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
