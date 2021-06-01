# django-cuidfield

Provides a CuidField for your Django models.

A [cuid](https://github.com/ericelliott/cuid) is a collision-resistant ID optimised for horizontal
scaling and performance; it was designed by [@ericelliot](https://github.com/ericelliott).

A cuid looks like this:

`cjld2cjxh0000qzrmn831i7rn`

and has the following properties:

-   fast, tiny implementation.
-   collision-free generation client or server side (horizontally scaleable).
-   can be created before insertion, avoiding db-round trips to get an id.
-   monotonically increasing, for better primary key peformance.
-   URL-safe. No need to guess whether it should be hyphenated.
-   more portable than GUID/UUID.
-   and [plenty more](https://github.com/ericelliott/cuid).

This library supports:

-   prefixing the ID on a per-model basis à la Stripe. e.g `cus_` => `cus_cjld2cjxh0000qzrmn831i7rn`
-   PostgreSQL only. It will likely work with other database backends, but we will only maintain for
    PostgreSQL.
-   Python 3.9 & above only.


## 📗 Install

Install using your favourite Python dependency manager, or straight with pip:

```
pip install django-cuidfield
```

## ✨ Usage

```
from cuidfield import CuidField
```

### Parameters

|Param|Type|Default|Note|
|-----|----|----|
|**primary_key*|`boolean`|`False`|Set to `True` to replace Django's default `Autofield` that gets used as the primary key, else the field will be additional ID field available to the model.|
|**prefix**|`str | Callable` |`""`|If provided, the cuid strings generated as the field's default value will be prefixed. This provides a way to have a per-model prefix which can be helpful in providing a global namespace for your ID system. The prefix can be provided as a string literal (e.g `cus_`), or as a `Callable` which is run when the field is attached to the model instance and can allow for more dynamic prefixing needs. For more, see below.|
|**default**|`Callable`|`cuid.cuid()`|By default the field is setup to generate a `cuid` to persist when a value has not been explicitly provided. This goes _against_ most Django fields which require explicitly setting a default but for this particular field we felt it made sense. If you would like to pass your own callable to generate the cuid you may do so, or pass `None` to explicitly disable any default generation of IDs which will leave the field blank on save. If you pass a default callable and the prefix parameter, the prefix will still be applied to the result of the callable default.|
|unique|`boolean`|`True`|Whether the field should be treated as unique across the dataset; the field provides a sane default of `True` so that a database index is setup to protext you against collisions (whether due to chance or, more likely, a bug/human error). To turn the index off, simply pass `False`.|
|`max_length`|`int`|`40`|Controls the maximum length of the stored strings. The field provides a sensible default to allow for future expansion of the cuid key size, but you may provide your own as you see fit, remembering to take into account the length of any prefixes you have configured. At this current time, the full cuids alone are 25 characters long but the spec reserves the right to increase collision-resistance in the future.|

All other `django.db.models.fields.CharField` keyword arguments should work as expected. See the [Django docs](https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.CharField).

### Usage as the Primary Key

This will replace Django's `AutoField` and the cuid will become the main primary key
for the entity, thus removing the default database-genererated incremental integer ID.

```python
# models/some_model.py or models.py

class SomeModel(models.Model):
    id = CuidField(primary_key=True)

>>> some_model = SomeModel.objects.create()
>>> str(some_model.id)
"ckp9jm3qn001001mrg5hw3sk4"
>>> some_model.id
Cuid(cuid="ckp9jm3qn001001mrg5hw3sk4", prefix="")
>>> some_model.id.cuid
"ckp9jm3qn001001mrg5hw3sk4"
>>> some_model.id.prefix
""
```
### Setting up prefixing

#### What?

Prefixing allows per-entity ID namespacing, e.g:

```
cus_ckp9mdxpd000i01ld6gzjgyl4 (reference a specific customer)
usr_ckp9me8zy000p01lda5579o3q (reference a specific user)
org_ckp9mek2d000s01ld8ffhhvd3 (reference a specific organisation)
```

#### Why?

By prefixing your entities IDs you can create a global namespace for your ID system which has numerous advantages:

* when displaying an ID you can immediately derive what type of object it represents from reading the prefix alone; most identifiers only showcase what instance is represented, but without information about the type it is machine-impossile to tell if ID `123` is from the `Dog` or `Cat` models. Whereas `cat_123` and `dog_123` make that clear.

* by having a global system of prefixing, you can speed up internal processes as (think: support) by having features in your backoffice such as "quick find" which allows you to dump the ID in question and be taken straight to the page which represents the specific instance of that type of object.

This may sound familiar, as it's how [Stripe](http://stripe.com/) handle their public IDs - everything is referenceable.

#### How?

Two options.

First is to set a string literal during field instantiation. E.g:

```python
# models.py

class User(models.Model):
    public_id = CuidField(prefix="usr_")

>>> user = User.objects.create()
>>> str(user.public_id)
"usr_ckp9me8zy000p01lda5579o3q"
>>> user.public_id.cuid
"ckp9me8zy000p01lda5579o3q"
>>> user.public_id.prefix
"usr_"
```

Second is to pass a callable which is executed after field initialisation and during its addition to the model itself (`Field.contribute_to_class`). This allows for dynamic generation of the prefix at runtime, which is especially helpful if you've defined the field on an Abstract Django model class, as the prefix generator will be called once for every concrete model that inherits the abstract.

The callable should accept `model_class: models.Model` (the model the field is being added to), `field_instance: django.db.models.Field` (the field instance being added) & `field_name: str` (the name of the field on the model). E.g:

```python
# models.py

def get_prefix_from_class_name(
    *,
    model_class: models.Model,
    field_instance: Field,
    field_name: str,
) -> str:
    """Return the Model's name in snake_case for use as a cuid prefix."""
    name = model_class.__name__
    # CamelCase to snake_case
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower() + "_"


class UserProfile(models.Model):
    public_id = CuidField(prefix=get_prefix_from_class_name)

>>> user = User.objects.create()
>>> str(user.public_id)
"user_profile_ckp9me8zy000p01lda5579o3q"
>>> user.public_id.cuid
"ckp9me8zy000p01lda5579o3q"
>>> user.public_id.prefix
"user_profile_"
```

### General usage

The field has a descriptor set that returns a special `Cuid` object that exposes a few helpful things:

* `prefix` and `cuid` attributes to make reading _just_ the cuid or prefix easier.
* when stringified, the `Cuid` object returns the full string representation of the ID.

```
>>> user.id
Cuid(cuid="ckp9me8zy000p01lda5579o3q", prefix="usr_")
>>> str(user.id)
"use_ckp9me8zy000p01lda5579o3q"
>>> user.id.cuid
"ckp9me8zy000p01lda5579o3q"
>>> user.id.prefix
"usr_"
```

* a `.cycle()` method to allow for in-place rotation (replacing) of the ID while keeping the same prefix.

```
>>> user.id
Cuid(cuid="ckp9me8zy000p01lda5579o3q", prefix="usr_")
>>> user.id.cycle()
>>> user.id
Cuid(cuid="ckp9nrmg7000x01kv90bx83kn", prefix="usr_")
>>> user.save()
>>> user.refresh_from_db()
>>> user.id.cuid
"ckp9nrmg7000x01kv90bx83kn"
>>> user.id.prefix
"usr_"
```

Generally speaking, the `Cuid` and full string representation can be used in most scenarios interchangeably: ORM lookups work with both; and setting the field works with both, whilst ensuring the correct prefix has been applied.

See the tests for more common usage patterns.
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

The full CI suite is controlled by `tox`, which contains a set of environments that will format
(`fmt`), lint, and test against all support Python + Django version combinations.

```
$ tox
```

#### ⚙️ CI

Uses GitHub Actions, see `./github/workflows`.
