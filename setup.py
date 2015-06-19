#!/usr/bin/env python

# Copyright (C) 2013-2015 SignalFuse, Inc.
# Copyright (C) 2015 SignalFx, Inc.

from setuptools import setup, find_packages

from signalfx.version import name, version

with open('README.md') as readme:
    long_description = readme.read()

with open('requirements.txt') as f:
    requirements = [line.strip() for line in f.readlines()]

setup(
    name=name,
    version=version,
    author='SignalFx, Inc',
    author_email='info@signalfx.com',
    description='SignalFx Python Library',
    license='Apache Software License v2',
    long_description=long_description,
    zip_safe=True,
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    url='https://github.com/signalfx/signalfx-python',
)
