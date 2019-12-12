#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

from enum import Enum

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

    def get_filename(self):
        """
        :returns: filename of scenario
        :rtype: str
        """
        return self.__filename

    def get_role(self):
        """
        :returns: role of scenario
        :rtype: Role
        """
        return self.__role
