#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Setup file for creating distributions
"""
from setuptools import setup, find_packages

setup(
    name='vqlmanager',
    version='0.1.0.dev1',
    packages=find_packages(),
    keywords=['vql', 'denodo'],
    python_requires='~=3.6',
    url='https://github.com/andretreebus/vqlmanager',
    license=open('LICENCE', encoding='utf-8').read(),
    author='Andre Treebus',
    author_email='andretreebus@hotmail.com',
    description='GUI Application for managing VQL scripts',
    long_description=open('README.rst', encoding='utf-8').read(),
    classifiers=[
        'Development Status :: 0.1 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Denodo Administrators',
        'License :: OSI Approved :: Apache-2',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.6',
        'Topic :: Version Control :: Denodo',
        'Topic :: Office/Business',
        'Topic :: Software Development :: VQL Management',
    ],
    install_requires=['PyQt5>=5.9.2', 'qdarkstyle>=2.3.1', 'pip>=9.0.1', 'setuptools>=28.8.0', 'sip>=4.19.6', 'wheel>=0.30.0'],
    entry_points={'gui_scripts': ['vqlmanager=vqlmanager.__main__:main', ], },
    include_package_data=False,
    zip_safe=True
)

# bash -cl "/venv/bin/python /setup.py bdist_wininst
# python3.6 setup.py bdist_wheel
