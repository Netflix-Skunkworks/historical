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
    'boto3==1.4.4',
    'click==6.7',
    'pynamodb==3.1.0',
    'deepdiff==3.3.0',
    'raven_python_lambda',
    'cloudaux',
    'delegator'
]

tests_require = [
    'pytest==3.1.3',
    'moto==1.0.1',
    'coveralls==1.1'
]


class InstallServerless(install):
    def run(self):
        log.info("Running [npm install --quiet] in {0}".format(ROOT))
        try:
            subprocess.check_output(['npm', 'install', '--quiet'], cwd=ROOT)
        except subprocess.CalledProcessError as e:
            log.warn("Unable to install javascript components! Reason: {}".format(e))

        install.run(self)


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
    cmdclass={
        'install': InstallServerless
    },
    entry_points={
        'console_scripts': [
            'historical = historical.cli:cli',
        ]
    },
    keywords=['aws', 'account_management']
)


