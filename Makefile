PYTHON = python
FILE_WITH_VERSION = findimports.py
FILE_WITH_CHANGELOG = CHANGES.rst

.PHONY: default
default:
	@echo "Nothing to build here"

.PHONY: flake8
flake8:
	tox -e flake8

.PHONY: check test
check test:
	tox -p auto

.PHONY: coverage
coverage:
	coverage run testsuite.py
	coverage report -m --fail-under=100

.PHONY: preview-pypi-description
preview-pypi-description:
	# pip install restview, if missing
	restview --long-description

# My usual 'make release' and friends
include release.mk
