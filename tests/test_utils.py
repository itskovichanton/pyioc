import sys
from dataclasses import dataclass

import pytest
from benedict import benedict

from src.mybootstrap_ioc_itskovichanton.env import append_props_from_args
from src.mybootstrap_ioc_itskovichanton.utils import (
    append_benedict,
    create_benedict,
    default_dataclass_field,
    flatten_dict,
    infer,
    infer_from_value,
    merge_missing_keys,
    nested_dict_iter,
    trim_string,
)


def test_trim_string():
    assert trim_string("  abc  ", 10) == "abc"
    assert trim_string("", 10) == ""
    assert trim_string(None, 10) == ""
    assert trim_string("abcdef", 4) == "abc…"


def test_flatten_and_nested_iter():
    flat = flatten_dict({"email": {"host": "root", "port": 25}, "name": "a"})
    assert flat == {"email.host": "root", "email.port": 25, "name": "a"}
    assert list(nested_dict_iter({"a": {"b": 1}, "c": 2})) == [("b", 1), ("c", 2)]


def test_benedict_helpers_keep_dotted_keys():
    bag = create_benedict({"email": {"host": "root"}})
    append_benedict(bag, create_benedict({"email": {"user": "ann"}}))
    assert bag["email.host"] == "root"
    assert bag["email.user"] == "ann"


def test_infer_casts_defaults_and_literals():
    bag = benedict({"n": "4", "item": {"a": 1}})

    @dataclass
    class Item:
        a: int

    assert infer(bag, "n", result=int) == 4
    assert infer(bag, "missing", default=7, result=int, none_result_violated=False) == 7
    assert isinstance(infer(bag, "item", result=Item), Item)
    assert infer(bag, "item", result=Item).a == 1
    with pytest.raises(ValueError, match="missing.now"):
        infer(bag, "missing.now")
    assert infer_from_value(bag, "not.a.real.key") == "not.a.real.key"
    assert infer_from_value(bag, ("n", int)) == 4
    assert infer_from_value(bag, ("absent", int, 3)) == 3


def test_merge_missing_keys_keeps_existing_values():
    root = {"email": {"host": "root", "port": 25}, "keep": [1]}
    profile = {"email": {"host": "dev", "user": "ann"}, "extra": {"flag": 1}, "keep": [2]}
    merge_missing_keys(root, profile)
    assert root["email"] == {"host": "root", "port": 25, "user": "ann"}
    assert root["extra"] == {"flag": 1}
    assert root["keep"] == [1]
    root["extra"]["flag"] = 9
    assert profile["extra"]["flag"] == 1


def test_cli_props_collect_repeats_and_skip_junk(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["app", "port=1", "port=2", "nope", "=x", "name=a"])
    bag = benedict()
    append_props_from_args(bag)
    assert bag["port"] == ["1", "2"]
    assert bag["name"] == "a"
    assert "nope" not in bag


def test_default_dataclass_field_is_not_a_constructor_argument():
    @dataclass
    class Row:
        name: str
        extra: str = default_dataclass_field("z")

    row = Row("a")
    assert row.extra == "z"
