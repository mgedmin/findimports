.PHONY: all
all:
	@echo "Nothing to build here"

.PHONY: test
test:                           ##: run tests
	tox -p auto

.PHONY: coverage
coverage:                       ##: measure test coverage
	tox -e coverage

.PHONY: flake8
flake8:                         ##: check for style problems
	tox -e flake8


# My usual 'make release' and friends
FILE_WITH_VERSION = findimports.py
include release.mk
