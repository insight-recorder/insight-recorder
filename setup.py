#!/usr/bin/env python

"""
Installation module for Dawati User Testing.
"""

from distutils.core import setup

setup(name='Dawati user testing',
      version='0.3',
      description='Tool for creating observation videos of users performing tasks on desktop applications or other devices',
      author=file('AUTHORS').read(),
      url='http://github.com/dawati/dawati-user-testing',
      packages=['dut'],
      package_dir={'dut': 'src/dut'},
#      package_data={'none yet': ['*.xml']},
      scripts=['dawati-user-testing'],
)
