#!/usr/bin/env python3
#  Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import setuptools
import codecs
import os
import m2r

parent_path = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(parent_path, 'README.md'), encoding='utf-8') as f:
    long_description = m2r.convert(f.read())

setuptools.setup(
    name='TMPPy',
    version='0.1.3',
    description='A subset of Python that can be compiled to C++ meta-functions using the py2tmp compiler',
    long_description=long_description,
    url='https://github.com/google/tmppy',
    author='Marco Poletti',
    author_email='poletti.marco@gmail.com',
    license='Apache 2.0',
    keywords='C++ metaprogramming compiler templates',
    python_requires='>=3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Apache Software License',
        # TODO: check which 3.x Python versions work and update this.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    packages=setuptools.find_packages(exclude=['*.tests', 'extras']),
    data_files=[('include/tmppy', ['include/tmppy/tmppy.h'])],
    entry_points={
        'console_scripts': ['py2tmp=py2tmp:main'],
    },
)
