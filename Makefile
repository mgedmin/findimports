PYTHON = python
FILE_WITH_VERSION = findimports.py
FILE_WITH_CHANGELOG = CHANGES.rst

.PHONY: default
default:
	@echo "Nothing to build here"

.PHONY: check test
check test:
	$(PYTHON) testsuite.py

.PHONY: coverage
coverage:
	coverage run testsuite.py
	coverage report -m --fail-under=100

.PHONY: test-all-pythons
test-all-pythons:
	# pip install detox, if missing
	detox

.PHONY: preview-pypi-description
preview-pypi-description:
	# pip install restview, if missing
	restview --long-description

# My usual 'make release' and friends
include release.mk
