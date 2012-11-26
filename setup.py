#!/usr/bin/env python

"""
Installation module for insight recorder.
"""

from distutils.core import setup

setup(name='Insight recorder',
      version='0.5',
      description='Tool for creating observation videos of users performing tasks on desktop applications or other devices',
      author=file('AUTHORS').read(),
      url='http://github.com/dawati/insight-recorder',
      packages=['isr'],
      package_dir={'isr': 'src/isr'},
      data_files = [('share/applications', ['data/insight-recorder.desktop'])],
#      package_data={'none yet': ['*.xml']},
      scripts=['insight-recorder'],
)
