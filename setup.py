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
    license=open('LICENCE').read(),
    author='Andre Treebus',
    author_email='andretreebus@hotmail.com',
    description=open('README.rst').read(),
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
        'Topic :: Communications :: Email',
        'Topic :: Office/Business',
        'Topic :: Software Development :: Bug Tracking',
    ],
    install_requires=['PyQt5>=5.9.2', 'qdarkstyle>=2.3.1', 'pip>=9.0.1', 'setuptools>=28.8.0', 'sip>=4.19.6', 'wheel>=0.30.0']
)

# bash -cl "/venv/bin/python /setup.py bdist_wininst --bdist-dir=/tmp --dist-dir=/build --bitmap=/vqlmanager/images/splitter.png --title="VQL Manager" --user-access-control=auto"
# python3.6 setup.py bdist_wheel
