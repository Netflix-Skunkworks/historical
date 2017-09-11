Contributing
============

Want to contribute back to Historical? This page describes the general development flow,
our philosophy, the test suite, and issue tracking.


Documentation
-------------

If you're looking to help document Historical, you can get set up with Sphinx, our documentation tool,
but first you will want to make sure you have a few things on your local system:

* python-dev (if you're on OS X, you already have this)
* pip
* virtualenvwrapper

Once you've got all that, the rest is simple:

::

    # If you have a fork, you'll want to clone it instead
    git clone git://github.com/netflix/historical.git

    # Create a python virtualenv
    mkvirtualenv historical

    # Make the magic happen
    make dev-docs

Running ``make dev-docs`` will install the basic requirements to get Sphinx running.


Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

Inside the ``docs`` directory, you can run ``make`` to build the documentation.
See ``make help`` for available options and the `Sphinx Documentation <http://sphinx-doc.org/contents.html>`_ for more information.


Developing Against HEAD
-----------------------

We try to make it easy to get up and running in a development environment using a git checkout
of Historical. You'll want to make sure you have a few things on your local system first:

* python-dev (if you're on OS X, you already have this)
* pip
* virtualenv (ideally virtualenvwrapper)
* node.js (for npm and building css/javascript)
* (Optional) PostgreSQL

Once you've got all that, the rest is simple:

::

    # If you have a fork, you'll want to clone it instead
    git clone git://github.com/historical/historical.git

    # Create a python virtualenv
    mkvirtualenv historical

    # Make the magic happen
    make

Running ``make`` will do several things, including:

* Setting up any submodules (including Bootstrap)
* Installing Python requirements
* Installing NPM requirements

.. note::
    You will want to store your virtualenv out of the ``historical`` directory you cloned above,
    otherwise ``make`` will fail.


Coding Standards
----------------

Historical follows the guidelines laid out in `pep8 <http://www.python.org/dev/peps/pep-0008/>`_  with a little bit
of flexibility on things like line length. We always give way for the `Zen of Python <http://www.python.org/dev/peps/pep-0020/>`_. We also use strict mode for JavaScript, enforced by jshint.

You can run all linters with ``make lint``, or respectively ``lint-python`` or ``lint-js``.

Spacing
~~~~~~~

Python:
  4 Spaces


Git hooks
~~~~~~~~~

To help developers maintain the above standards, Historical includes a configuration file for Yelp's `pre-commit <http://pre-commit.com/>`_. This is an optional dependency and is not required in order to contribute to Historical.


Running the Test Suite
----------------------

The test suite consists of multiple parts, testing both the Python and JavaScript components in Historical. If you've setup your environment correctly, you can run the entire suite with the following command:

::

    make test

If you only need to run the Python tests, you can do so with ``make test-python``.


You'll notice that the test suite is structured based on where the code lives, and strongly encourages using the mock library to drive more accurate individual tests.

.. note:: We use py.test for the Python test suite.


Contributing Back Code
----------------------

All patches should be sent as a pull request on GitHub, include tests, and documentation where needed. If you're fixing a bug or making a large change the patch **must** include test coverage.

Uncertain about how to write tests? Take a look at some existing tests that are similar to the code you're changing, and go from there.

You can see a list of open pull requests (pending changes) by visiting https://github.com/netflix-skunkworks/historical/pulls

Pull requests should be against **master** and pass all TravisCI checks


