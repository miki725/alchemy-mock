.PHONY: clean-pyc clean-build clean

# automatic help generator
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## install all requirements including dev dependencies
	pip install -U -r requirements-dev.txt

clean: clean-build clean-pyc clean-test  ## remove all artifacts

clean-build:  ## remove build artifacts
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info

clean-pyc:  ## remove Python file artifacts
	-@find . -name '*.pyc' -follow -print0 | xargs -0 rm -f
	-@find . -name '*.pyo' -follow -print0 | xargs -0 rm -f
	-@find . -name '__pycache__' -type d -follow -print0 | xargs -0 rm -rf

clean-test:  ## remove test and coverage artifacts
	@rm -rf .coverage coverage*
	@rm -rf htmlcov/
	@rm -rf .cache

clean-all:  ## remove tox test artifacts
	rm -rf .tox

lint:  ## check style with flake8 and importanize
	flake8 alchemy_mock
	python -m importanize alchemy_mock/

test: clean  ## run all tests
	pytest --doctest-modules --cov=alchemy_mock/ --cov-report=term-missing alchemy_mock/

test-pdb: clean  ## run all tests with pdb
	pytest --doctest-modules --cov=alchemy_mock/ --cov-report=term-missing --pdb --capture=no alchemy_mock/

test-all: clean  ## run all tests with tox
	tox

check: lint clean test  ## run all necessary steps to check validity of project

release: clean  ## package and upload a release
	# python setup.py checkdocs
	python setup.py sdist upload
	python setup.py bdist_wheel upload

dist: clean  ## package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist
