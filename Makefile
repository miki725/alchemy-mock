.PHONY: clean-pyc clean-build clean

# automatic help generator
help:  ## show help
	@grep -E '^[a-zA-Z_\-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		cut -d':' -f1- | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## install all requirements including dev dependencies
	pip install -U -r requirements-dev.txt

clean: clean-build clean-pyc clean-test  ## remove all artifacts

clean-build:  ## remove build artifacts
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info

clean-pyc:  ## clean pyc files
	-@find . -path ./.tox -prune -o -name '*.pyc' -follow -print0 | xargs -0 rm -f
	-@find . -path ./.tox -prune -o -name '*.pyo' -follow -print0 | xargs -0 rm -f
	-@find . -path ./.tox -prune -o -name '__pycache__' -type d -follow -print0 | xargs -0 rm -rf

clean-test:  ## remove test and coverage artifacts
	@rm -rf .coverage coverage*
	@rm -rf htmlcov/
	@rm -rf .cache

clean-all: clean  ## remove tox test artifacts
	rm -rf .tox

lint: clean  ## lint whole library
	if python -c "import sys; exit(1) if sys.version[:3] < '3.6' else exit(0)"; \
	then \
		pre-commit run --all-files ; \
	fi
	python setup.py checkdocs

test: clean  ## run all tests
	pytest --doctest-modules --cov=alchemy_mock/ --cov-report=term-missing alchemy_mock/

test-pdb: clean  ## run all tests with pdb
	pytest --doctest-modules --cov=alchemy_mock/ --cov-report=term-missing --pdb --capture=no alchemy_mock/

test-all: clean  ## run all tests with tox
	tox

check: lint clean test  ## run all necessary steps to check validity of project

release: clean  ## push release to pypi
	python setup.py sdist bdist_wheel upload

dist: clean  ## create distribution of the library
	python setup.py sdist bdist_wheel
	ls -l dist
