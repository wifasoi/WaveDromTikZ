#!/usr/bin/env python

from setuptools import setup

setup(name='WaveDromTikZ',
      version='0.1.1',
      description='WaveDrom to TikZ converter.',
      author='Jonathan Heathcote',
      author_email='mail@jhnet.co.uk',
      maintainer='Luca Cristaldi',
      scripts=['wavedromtikz.py'],
      install_requires=['pyyaml']
      )
