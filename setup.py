"""
Historical
==========

Allows for the tracking of AWS configuration data across accounts/regions/technologies.

"""
import sys
import os.path

import subprocess
from distutils import log
from setuptools import setup, find_packages
from setuptools.command.install import install


ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__)))

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src/ directory to the sys.path.
sys.path.insert(0, ROOT)

about = {}
with open(os.path.join(ROOT, "historical", "__about__.py")) as f:
    exec(f.read(), about)


install_requires = [
    'cloudaux',
    'boto3>=1.4.4',
    'click==6.7',
    'pynamodb==3.1.0',
    'deepdiff==3.3.0',
    'cloudaux',
    'raven-python-lambda'
]

tests_require = [
    'pytest==3.1.3',
    'moto==1.0.1',
    'coveralls==1.1'
]


setup(
    name=about["__title__"],
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__email__"],
    url=about["__uri__"],
    description=about["__summary__"],
    long_description='See README.md',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        'tests': tests_require
    },
    entry_points={
        'console_scripts': [
            'historical = historical.cli:cli',
        ]
    },
    keywords=['aws', 'account_management']
)


