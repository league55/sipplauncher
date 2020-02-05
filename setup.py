#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

from setuptools import setup, find_packages
import re
import os

from sipplauncher.utils.Utils import (walk_folder_recur)
from sipplauncher.utils.Defaults import (long_description, VERSION, DEFAULT_CONFIG_FILES)

dependency_links = []
VCS_PREFIXES = ('git+', 'hg+', 'bzr+', 'svn+')

def extract_requirements(filename):
    # Thanks: https://github.com/yash-nisar/coala/commit/f19e50c9be5cb2b32d0f4f5acef051a22ce537d9
    requirements = []
    with open(filename) as requirements_file:
        lines = requirements_file.read().splitlines()
        for package in lines:
            if not package or package.startswith('#'):
                continue
            if any(package.startswith(prefix) for prefix in VCS_PREFIXES):
                dependency_links.append(package)
                if re.search('#egg=(.*)', package):
                    package = package.split('=')[1]
                else:
                    raise ValueError('Please enter "#egg=package_name" at the'
                                     'end of the url.')
            requirements.append(package)
    return requirements

PNAME = 'sipplauncher'
requirements = extract_requirements('requirements.txt')
requirements_test = extract_requirements('requirements_test.txt')
my_config_path=os.path.join('resources', 'etc')
my_data_files = walk_folder_recur(DEFAULT_CONFIG_FILES,
                                  my_config_path,
                                  level=2)

array_packages = find_packages(exclude=[])
my_array_files = find_packages(PNAME, exclude=['tests', 'tests.*', 'test', 'test_*', '*.tests'])
my_array_files = ['{0}.{1}'.format(PNAME, x) for x in my_array_files]
my_array_files.insert(0, PNAME)

setup(
    name = PNAME,
    packages=my_array_files,
    version = VERSION,
    license='MIT',
    description = 'Launching SIPp made easy - automate your SIPp SIP scenarios with just one command!',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author = 'Zaleos',
    author_email = 'mrbot@zaleos.net',
    url = 'https://github.com/zaleos/{0}'.format(PNAME),
    # download_url = 'https://github.com/zaleos/{0}/archive/pypi-0_1_3.tar.gz'.format(PNAME),
    keywords = ['voip', 'sipp', 'sip', 'testing', 'rtp', 'sdp', 'hp'],
    install_requires=requirements,
    tests_require=requirements_test,    
    dependency_links=dependency_links,
    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish
        'License :: OSI Approved :: MIT License',
        
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
    ],

    entry_points={
        'console_scripts': [
            'sipplauncher = sipplauncher.main:my_main_fun',
        ],
    },

    data_files=my_data_files,
    include_package_data=True,
    python_requires='>=3.6',
)
