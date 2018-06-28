"""
Historical
==========

Allows for the tracking of AWS configuration data across accounts/regions/technologies.

"""
import os.path
import sys

from setuptools import setup, find_packages

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__)))

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src/ directory to the sys.path.
sys.path.insert(0, ROOT)

about = {}
with open(os.path.join(ROOT, "historical", "__about__.py")) as f:
    exec(f.read(), about)


install_requires = [
    'cloudaux>=1.4.14',
    'click>=6.7',
    'pynamodb>=3.1.0',
    'deepdiff>=3.3.0',
    'raven-python-lambda>=0.1.7',
    'marshmallow>=2.13.5',
    'swag-client>=0.3.0',
    'python-dateutil==2.6.1'
]

tests_require = [
    'pytest==3.1.3',
    'moto>=1.3.2',
    'coveralls==1.1',
    'factory-boy==2.9.2'
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
    keywords=['aws', 'account_management'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
