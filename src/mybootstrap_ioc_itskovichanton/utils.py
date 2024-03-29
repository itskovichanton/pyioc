import argparse
import functools
from collections import abc
from collections.abc import MutableMapping, ItemsView
from dataclasses import dataclass
from dataclasses import field
from inspect import isclass
from typing import get_origin, List, Dict

from benedict import benedict
from dacite import from_dict, Config


def trim_string(s: str, limit: int, ellips='…') -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) > limit:
        return s[:limit - 1].strip() + ellips
    return s


def omittable_parentheses(maybe_decorator=None, /, allow_partial=False):
    """A decorator for decorators that allows them to be used without parentheses"""

    def decorator(func):
        @functools.wraps(decorator)
        def wrapper(*args, **kwargs):
            if len(args) == 1 and callable(args[0]):
                if allow_partial:
                    return func(**kwargs)(args[0])
                elif not kwargs:
                    return func()(args[0])
            return func(*args, **kwargs)

        return wrapper

    if maybe_decorator is None:
        return decorator
    else:
        return decorator(maybe_decorator)


_SPECIAL_TYPES = (dict, benedict, list, List, Dict)


def infer(b: benedict, keypath: str, default=None, result=None, none_result_violated=True):
    v = b.get(keypath, default)
    if v is None and none_result_violated:
        raise ValueError(f"Value for key={keypath} has not been provided")

    if v is None and result is None:
        return None

    if type(v) in _SPECIAL_TYPES:

        if get_origin(result) in _SPECIAL_TYPES:
            @dataclass
            class _Wrapped:
                value: result = None

            return from_dict(data_class=_Wrapped, data={"value": v}, config=Config(check_types=False)).value

        if isclass(result):
            return from_dict(data_class=result, data=v, config=Config(check_types=False))

    if result and (v is not None) and type(v) != result:
        return result(v)

    return v


def infer_from_value(b: benedict, args):
    if type(args) == tuple:
        if len(args) == 3:
            return infer(b, args[0], default=args[2], result=args[1], none_result_violated=False)
        if len(args) == 2:
            return infer(b, args[0], result=args[1])
        if len(args) == 1:
            return infer(b, args[0])
    if type(args) == str:
        try:
            return infer(b, args)
        except:
            return args
    return None


def _append_items(r: benedict, items: ItemsView):
    for k, v in items:
        k = str(k)
        # v = str(v)
        try:
            if "." in k:
                keys = k.split(".")
                if len(keys) == 1:
                    k = keys[0]
        except BaseException as e:
            print(k, ":", v)
        r[k] = v


def create_benedict(a: dict) -> benedict:
    r = benedict()
    _append_items(r, flatten_dict(a).items())
    return r


def append_benedict(r: benedict, b: benedict):
    _append_items(r, flatten_dict(b).items())
    return r


class StoreInDict(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        d = getattr(namespace, self.dest)
        for opt in values:
            try:
                k, v = opt.split("=", 1)
                k = k.lstrip("-")
                if k in d:
                    d[k].append(v)
                else:
                    d[k] = v
            except:
                ...
        setattr(namespace, self.dest, d)


def nested_dict_iter(nested):
    for key, value in nested.items():
        if isinstance(value, abc.Mapping):
            yield from nested_dict_iter(value)
        else:
            yield key, value


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def default_dataclass_field(v):
    return field(init=False, default_factory=lambda: v)
