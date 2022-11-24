import argparse
import functools
from collections import abc
from collections.abc import MutableMapping, ItemsView
from inspect import isclass

from benedict import benedict
from dacite import from_dict


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


def infer(b: benedict, keypath: str, default=None, result=None, none_result_violated=True):
    value = b[keypath] if keypath in b else default
    if value is None and none_result_violated:
        raise ValueError(f"Value for key={keypath} has not been provided")
    if value is None and result is None:
        return None

    if type(value) in (dict, benedict) and isclass(result):
        return from_dict(data_class=result, data=value)

    return value


def infer_from_tuple(b: benedict, args):
    if type(args) is tuple:
        if len(args) == 3:
            return infer(b, args[0], default=args[2], result=args[1], none_result_violated=False)
        if len(args) == 2:
            return infer(b, args[0], result=args[1])
        if len(args) == 1:
            return infer(b, args[0])
    if type(args) is str:
        return infer(b, args)
    return None


def _append_items(r: benedict, items: ItemsView):
    for k, v in items:
        if "." in k:
            keys = k.split(".")
            if len(keys) == 1:
                k = keys[0]
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
            k, v = opt.split("=", 1)
            k = k.lstrip("-")
            if k in d:
                d[k].append(v)
            else:
                d[k] = v
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
