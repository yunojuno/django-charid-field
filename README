# django-charid-field

[![PyPI version](https://badge.fury.io/py/django-charid-field.svg)](https://badge.fury.io/py/django-charid-field)

Provides a char-based, prefixable CharIDField for your Django models.

It can utilise [cuid], [ksuid], [ulid] or any other string-based UID generation systems.

It can be used as the primary key, or simple another key on your models.

[cuid]: https://github.com/ericelliott/cuid
[ksuid]: https://github.com/segmentio/ksuid
[ulid]: https://github.com/ulid/spec

## ⛲ Feature set

-   Ability to work with the UID generation spec of your choice.
-   Support for prefixing the ID on a per-model basis à la Stripe. e.g `cus_` => `cus_cjld2cjxh0000qzrmn831i7rn`
-   Support for all database backends that support the `CharField`.
-   Support for Python 3.8 & above only.

## 🤷 Why?

To get us a global namespace of collision-resistant IDs that:

* are URL-safe
* can be represented in a visual-space-efficient manor
* are collision-resistant to allow for client side generation
* exist now. UUID v6, v7, v8 are in RFC draft and not ready (Jul '21).

[cuid], [ksuid], [ulid] & many others offer this now, and prefixing gets us the global namespace.

**Why not use integers?**

* Auto-incrementing integers are easily enumerable and give away collection count.

* You can solve that with HashID but then you either have to store the HashID as another column or deal with constant conversion when looking up values in your UI VS raw in your database.

* Most importantly: relying on your database to generate IDs means sequential writes. Your clients are not free to generate their own IDs without a round trip to the database.

**Why not use UUIDs?**

They solve the collision problem so why not?

* The text formats use hex, which is not visually space-efficient.
* UUIDv4 (the one usually recommended) is completely random and thus impossible to sort. This has the knock on effect of making databases work harder when looking up/indexing as binary search goes out the window.
* Optional hyphenation when representing the hex. This nuance results in more code.

**Why prefix?**

Because global flat namespaces are powerful. An ID now represents the instance _and it's type_, which means you can have powerful lookup abilities with just the identifier alone. No more guessing whether `802302` is a `Dog` or a `Cat`.

## 📗 Install

Install using your favourite Python dependency manager, or straight with pip:

```
pip install django-charid-field
```

You'll also need to install your ID-generation library of choice (or bring your own).

For example:

|UID Spec|Python Library|What could it look like? (with a prefix `dev_`)|
|--------|--------------|----------------------------------------|
|[cuid]|cuid.py: [GH](https://github.com/necaris/cuid.py) / [PyPi](https://pypi.org/project/cuid/)|`dev_ckpffbliw000001mi3fw42vsn`|
|[ksuid]|cyksuid: [GH](https://github.com/timonwong/cyksuid) / [PyPi](https://pypi.org/project/cyksuid/)|`dev_1tOMP4onidzvnUFuTww2UeamY39`|
|[ulid]|python-ulid: [GH](https://github.com/mdomke/python-ulid) / [PyPi](https://pypi.org/project/python-ulid/)|`dev_01F769XGM83VR75H86ZPHKK595`|



## ✨ Usage

```
from charidfield import CharIDField
```

We recommend using `functool.partial` to create your own field for your codebase; this will allow you to specify your chosen ID generation and set the `max_length` parameter and then have an importable field you can use across all your models.

Here's an example using the cuid spec and cuid.py:

```python
# Locate this somewhere importable
from cuid import cuid
from charidfield import CharIDField

CuidField = partial(
    CharIDField,
    default=cuid,
    max_length=30,
    help_text="cuid-format identifier for this entity."
)

# models.py
from wherever_you_put_it import CuidField

class Dog(models.Model):
    id = CuidField(primary_key=True, prefix="dog_")
    name = models.CharField()

# shell
>>> dog = Dog(name="Ronnie")
>>> dog.id
"dog_ckpffbliw000001mi3fw42vsn"

```

### Parameters

|Param|Type|Required|Default|Note|
|-----|----|--------|-------|----|
|**default**|`Callable`|❌|-|This should be a callable which generates a UID in whatever system you chose. Your callable does not have to handle prefixing, the prefix will be applied onto the front of whatever string your default callable generates. Technically not required, but without it you will get blank fields and must handle ID generation yourself.|
|**prefix**|`str` |❌|`""`|If provided, the ID strings generated as the field's default value will be prefixed. This provides a way to have a per-model prefix which can be helpful in providing a global namespace for your ID system. The prefix should be provided as a string literal (e.g `cus_`). For more, see below.|
|**max_length**|`int`|✅|Set it|Controls the maximum length of the stored strings. Provide your own to match whatever ID system you pick, remembering to take into account the length of any prefixes you have configured. Also note that there is no perf/storage impact for modern Postgres so for that backend it is effectively an arbitary char limit.|
|**primary_key**|`boolean`|❌|`False`|Set to `True` to replace Django's default `Autofield` that gets used as the primary key, else the field will be additional ID field available to the model.|
|**unique**|`boolean`|❌|`True`|Whether the field should be treated as unique across the dataset; the field provides a sane default of `True` so that a database index is setup to protext you against collisions (whether due to chance or, more likely, a bug/human error). To turn the index off, simply pass `False`.|

All other `django.db.models.fields.CharField` keyword arguments should work as expected. See the [Django docs](https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.CharField).

### Usage as the Primary Key


This will replace Django's `AutoField` and the cuid will become the main primary key
for the entity, thus removing the default database-genererated incremental integer ID.

```python
# models/some_model.py or models.py

class SomeModel(models.Model):
    id = CharIDField(primary_key=True, default=your_id_generator)

>>> some_model = SomeModel.objects.create()
>>> some_model.id
"ckp9jm3qn001001mrg5hw3sk4"
>>> some_model.pk
"ckp9jm3qn001001mrg5hw3sk4"
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

Set a string literal during field instantiation. E.g:

```python
# models.py

class User(models.Model):
    public_id = CharIDField(prefix="usr_", ...)

>>> user = User.objects.create()
>>> user.public_id
"usr_ckp9me8zy000p01lda5579o3q"
```
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

[cuid]: https://github.com/ericelliott/cuid
[ksuid]: https://github.com/segmentio/ksuid
[ulid]: https://github.com/ulid/spec
