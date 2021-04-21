# django-cuidfield

Provides a CUIDField for your Django models.

A [cuid](https://github.com/ericelliott/cuid) is a collision-resistant id optimised for
horizontal scaling and performance; it was designed by [@ericelliot](https://github.com/ericelliott).

cuid looks like this:

`cjld2cjxh0000qzrmn831i7rn`

and has the following properties:

* fast, tiny implementation.
* collision-free generation client or server side (horizontally scaleable).
* can be created before insertion, avoiding db-round trips to get an id.
* monotonically increasing, for better primary key peformance.
* URL-safe. No need to guess whether it should be hyphenated.
* more portable than GUID/UUID.
* and [plenty more](https://github.com/ericelliott/cuid).

This library supports:

* prefixing the ID on a per-model basis à la Stripe. e.g `cus_cjld2cjxh0000qzrmn831i7rn`
* PostgreSQL only. It will likely work with other database backends, but we will only maintain for PostgreSQL.


## 👩‍💻 Development

### 🏗️ Local environment

The local environment is handled with `poetry`, so install that first then:

```
$ poetry install
```

### 🧪 Running tests

The tests themselves use `pytest` as the test runner.

After setting up the environment, run them using:

```
$ poetry run pytest
```

The full CI suite is controlled by `tox`, which contains a set of environments that will format (`fmt`), lint, and test against all support Python + Django version combinations.

```
$ tox
```

#### ⚙️  CI

Uses GitHub Actions, see `./github/workflows`.
