import pytest

from cuidfield.cuid import Cuid


@pytest.mark.parametrize(
    "value, prefix",
    [
        ("ckodhg53j000001labr7zezao", ""),
        ("cus_ckodhgdkx000101la536o00xg", "cus_"),
        ("111-ckodhgdkx000101la536o00xg", "111-"),
    ],
)
def test_cuid__successful_init(value, prefix):
    cuid = Cuid(value=value, prefix=prefix)
    assert str(cuid) == value
    assert cuid.cuid == value.removeprefix(prefix)
    assert cuid.prefix == prefix


@pytest.mark.parametrize(
    "value1, value2",
    [
        (
            Cuid(value="ckodhg53j000001labr7zezao"),
            Cuid(value="ckodhg53j000001labr7zezao"),
        ),
        (
            Cuid(value="cus_ckodhg53j000001labr7zezao", prefix="cus_"),
            Cuid(value="cus_ckodhg53j000001labr7zezao", prefix="cus_"),
        ),
    ],
)
def test_cuid__equality_match(value1, value2):
    assert value1 == value2


@pytest.mark.parametrize(
    "value1, value2",
    [
        # Both unprefixed, different cuid.
        (
            Cuid(value="ckodhg53j000001labr7zebab"),
            Cuid(value="ckodhg53j000001labr7zezao"),
        ),
        # Same cuid, one unprefixed & one prefixed.
        (
            Cuid(value="ckodhg53j000001labr7zezao"),
            Cuid(value="cus_ckodhg53j000001labr7zezao", prefix="cus_"),
        ),
        # Same cuid, different supplied prefixes.
        (
            Cuid(value="bus_ckodhg53j000001labr7zezao", prefix="bus_"),
            Cuid(value="cus_ckodhg53j000001labr7zezao", prefix="cus_"),
        ),
        # Different cuid, different supplied prefixes.
        (
            Cuid(value="bus_ckodhg53j000001labr7zebab", prefix="bus_"),
            Cuid(value="cus_ckodhg53j000001labr7zezao", prefix="cus_"),
        ),
    ],
)
def test_cuid__equality_mismatch(value1, value2):
    assert value1 != value2
