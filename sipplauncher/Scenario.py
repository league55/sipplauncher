#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

from enum import Enum
import os

class Scenario:
    """
    Scenario descriptor
    """

    class Role(Enum):
        uac = 1
        uas = 2

    def __init__(self, filename, role):
        """
        :param filename: filename of a scenario
        :type filename: str

        :param role: role of scenario
        :type role: Role
        """
        self.__filename = filename
        self.__role = role
        self.__tracefilename = os.path.splitext(filename)[0]+'_trace.csv'


    def get_filename(self):
        """
        :returns: filename of scenario
        :rtype: str
        """
        return self.__filename

    def get_tracefile(self):
        """
        :returns: filename of scenario
        :rtype: str
        """
        return self.__tracefilename

    def get_role(self):
        """
        :returns: role of scenario
        :rtype: Role
        """
        return self.__role

    def is_uac(self):
        """
        :return: bool
        """
        return self.__role == self.Role.uac
