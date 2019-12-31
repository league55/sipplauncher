#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import logging
import json
import binascii
import sipplauncher.Test
from dnslib.server import (DNSServer,
                           BaseResolver)
from dnslib import (DNSLabel,
                    QTYPE,
                    RCODE,
                    RR,
                    dns)


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

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

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
        self.__rname = DNSLabel(rname)

        rd_cls, self.__rtype = TYPE_LOOKUP[rtype]

        if self.__rtype == QTYPE.SOA and len(args) == 2:
            # add sensible times to SOA
            args += (SERIAL_NO, 3600, 3600 * 3, 3600 * 24, 3600),

        if self.__rtype == QTYPE.TXT and len(args) == 1 and isinstance(args[0], str) and len(args[0]) > 255:
            # wrap long TXT records as per dnslib's docs.
            args = wrap(args[0], 255),

        if self.__rtype in (QTYPE.NS, QTYPE.SOA):
            ttl = 3600 * 24
        else:
            ttl = 300

        self.rr = RR(
            rname=self.__rname,
            rtype=self.__rtype,
            rdata=rd_cls(*args),
            ttl=ttl,
        )

    def match(self, q):
        return q.qname == self.__rname and (q.qtype == QTYPE.ANY or q.qtype == self.__rtype)

    def sub_match(self, q):
        return self.__rtype == QTYPE.SOA and q.qname.matchSuffix(self.__rname)

    def __str__(self):
        return str(self.rr)


"""
End of MIT-licensed code
"""


class Logger:
    def log_recv(self, handler, data):
        logging.debug("Received: [{0}:{1}] ({2}) <{3}> : {4}".format(handler.client_address[0],
                                                                     handler.client_address[1],
                                                                     handler.protocol,
                                                                     len(data),
                                                                     binascii.hexlify(data)))

    def log_send(self, handler, data):
        logging.debug("Sent: [{0}:{1}] ({2}) <{3}> : {4}".format(handler.client_address[0],
                                                                 handler.client_address[1],
                                                                 handler.protocol,
                                                                 len(data),
                                                                 binascii.hexlify(data)))

    def log_request(self, handler, request):
        logging.debug("Request: [{0}:{1}] ({2}) / '{3}' ({4})".format(handler.client_address[0],
                                                                      handler.client_address[1],
                                                                      handler.protocol,
                                                                      request.q.qname,
                                                                      QTYPE[request.q.qtype]))
        self.log_data(request)

    def log_reply(self, handler, reply):
        if reply.header.rcode == RCODE.NOERROR:
            logging.debug("Reply: [{0}:{1}] ({2}) / '{3}' ({4}) / RRs: {5}".format(handler.client_address[0],
                                                                                   handler.client_address[1],
                                                                                   handler.protocol,
                                                                                   reply.q.qname,
                                                                                   QTYPE[reply.q.qtype],
                                                                                   ",".join([QTYPE[a.rtype] for a in reply.rr])))
        else:
            logging.debug("Reply: [{0}:{1}] ({2}) / '{3}' ({4}) / {5}".format(handler.client_address[0],
                                                                              handler.client_address[1],
                                                                              handler.protocol,
                                                                              reply.q.qname,
                                                                              QTYPE[reply.q.qtype],
                                                                              RCODE[reply.header.rcode]))
        self.log_data(reply)

    def log_truncated(self, handler, reply):
        logging.debug("Truncated Reply: [{0}:{1}] ({2}) / '{3}' ({4}) / RRs: {5}".format(handler.client_address[0],
                                                                                         handler.client_address[1],
                                                                                         handler.protocol,
                                                                                         reply.q.qname,
                                                                                         QTYPE[reply.q.qtype],
                                                                                         ",".join([QTYPE[a.rtype] for a in reply.rr])))
        self.log_data(reply)

    def log_error(self, handler, e):
        logging.debug("Invalid Request: [{0}:{1}] ({2}) :: {3}".format(handler.client_address[0],
                                                                       handler.client_address[1],
                                                                       handler.protocol,
                                                                       e))

    def log_data(self, dnsobj):
        logging.debug("\n{0}\n".format(dnsobj.toZone("    ")))


class Resolver(BaseResolver):
    def __init__(self):
        self.__run_id_map = dict()

    @staticmethod
    def __load(run_id, file):
        """
        Parse and load a file into memory.
        Store it in dict with a key of run_id.

        :param run_id: a key of DNS information which is added
        :type run_id: str

        :param file: a path to file to parse and load
        :type file: str
        """
        assert(os.path.exists(file))
        Resolver.__get_logger(run_id).info('loading DNS file {0}'.format(file))
        records = []
        with open(file, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    continue

                line = line.strip()

                if not line:
                    continue

                rname, rtype, args_ = line.split(maxsplit=2)
                if args_.startswith('['):
                    args = tuple(json.loads(args_))
                else:
                    args = (args_,)

                record = Record(rname, rtype, args)
                records.append(record)
                Resolver.__get_logger(run_id).info(' %2d: %s', len(records), record)

        Resolver.__get_logger(run_id).info('%d zone resource records generated from file', len(records))
        return records

    def resolve(self, request, handler):
        """
        Virtual overriden method which serves the requests from the clients.
        """
        type_name = QTYPE[request.q.qtype]
        reply = request.reply()

        for run_id, records in self.__run_id_map.items():
            for record in records:
                if record.match(request.q):
                    reply.add_answer(record.rr)
                    self.__get_logger(run_id).info('found zone for {0}[{1}]'.format(request.q.qname, type_name))

        if reply.rr:
            return reply

        # no direct zone so look for an SOA record for a higher level zone
        for run_id, records in self.__run_id_map.items():
            for record in records:
                if record.sub_match(request.q):
                    reply.add_answer(record.rr)
                    self.__get_logger(run_id).info('found higher level SOA resource for {0}[{1}]'.format(request.q.qname, type_name))

        if reply.rr:
            return reply

        logging.debug('no local zone found for {0}'.format(request.q))
        return super().resolve(request, handler)

    def add(self, run_id, file):
        """
        Add a file with DNS information for test.

        :param run_id: a key of DNS information which is added
        :type run_id: str

        :param file: a path to file with DNS information
        :type file: str
        """
        # Attempt to add duplicate run_id is an error
        assert(run_id not in self.__run_id_map)
        self.__run_id_map[run_id] = self.__load(run_id, file)

    def remove(self, run_id):
        """
        Remove DNS information.

        :param run_id: a key of DNS information which needs to be deleted
        :type run_id: str
        """
        # Attempt to delete non-existent run_id is not an error
        if run_id in self.__run_id_map:
            del self.__run_id_map[run_id]

    @staticmethod
    def __get_logger(run_id):
        """
        Get SIPpTest's logger, in order to log to test's run folder.
        """
        return logging.getLogger(".".join([sipplauncher.Test.SIPpTest.__module__, run_id]))


class DnsServer(DNSServer):
    def __new__(cls):
        """
        Singleton
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        super().__init__(resolver=Resolver(), logger=Logger())
        super().start_thread()

    def add(self, run_id, file):
        """
        Add a file with DNS information for test

        :param run_id: a key of DNS information which is added
        :type run_id: str

        :param file: a path to file with DNS information
        :type file: str
        """
        self.server.resolver.add(run_id, file)

    def remove(self, run_id):
        """
        Remove DNS information by a given key "run_id"

        :param run_id: a key of DNS information which needs to be deleted
        :type run_id: str
        """
        self.server.resolver.remove(run_id)
