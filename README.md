# Poetry Template

Django app template, using `poetry-python` as dependency manager.

This project is a template that can be cloned and re-used for redistributable apps.

It includes the following:

* `poetry` for dependency management
* `isort`, `black`, `pylint` and `flake8` linting
* `pre-commit` to run linting
* `mypy` for type checking
* `tox` and `travis` for builds and CI

There are default config files for the linting and mypy.

## Principles

The motivation for this project is to provide a consistent set of standards across all YunoJuno public Python/Django projects. The principles we want to encourage are:

* Simple for developers to get up-and-running:
    * Install all dev dependencies in an isolated environment
    * Run complete tox suite locally
* Consistent style:
    * Common formatting with `isort` and `black`
    * Common patterns with `pylint` and `flake8`
* Full type hinting

## Versioning

It's 2020, Python2 is officially deprecated, and we run our core platform on recent releases (Python 3.8 and Django 2.2 at the time of writing). Taking out lead from Django itself, we only support Python 3.8/7/6 and Django 2.2/3.0. As new versions arrive we will deprecate older versions at the point at which maintaining becomes a burden. Typically this is when we start to have to incorporate conditional imports into modules. When an older version of Python / Django is deprecated, the last supported version will be tagged as such. In the unlikely event that any bug fixes need to be applied to an old version, they will be done on a branch off the last known good version. They will not be released to PyPI.

## Tests

#### Tests package
The package tests themselves are _outside_ of the main library code, in a package that is itself a Django app (it contains `models`, `settings`, and any other artifacts required to run the tests (e.g. `urls`).) Where appropriate, this test app may be runnable as a Django project - so that developers can spin up the test app and see what admin screens look like, test migrations, etc.

#### Running tests
The tests themselves use `pytest` as the test runner. If you have installed the `poetry` evironment, you can run them thus:

```
$ poetry run pytest
```

or 

```
$ poetry shell
(my_app) $ pytest
```

The full suite is controlled by `tox`, which contains a set of environments that will format (`fmt`), lint, and test against all support Python + Django version combinations.

```
$ tox
...
______________________ summary __________________________
  fmt: commands succeeded
  lint: commands succeeded
  mypy: commands succeeded
  py36-django22: commands succeeded
  py36-django30: commands succeeded
  py37-django22: commands succeeded
  py37-django30: commands succeeded
  py38-django22: commands succeeded
  py38-django30: commands succeeded
```

#### CI

There is a `.travis.yml` file that can be used as a baseline to run all of the tests on Travis.
