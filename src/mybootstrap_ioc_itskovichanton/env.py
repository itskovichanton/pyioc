import argparse
import copy
import os
import sys

from benedict import benedict

from src.mybootstrap_ioc_itskovichanton.utils import StoreInDict, append_benedict, create_benedict


def append_props_from_args(r: benedict):
    p = argparse.ArgumentParser(prefix_chars=' ')
    p.add_argument("options", nargs="*", action=StoreInDict, default=dict())
    args = p.parse_args(sys.argv[1:])
    append_benedict(r, create_benedict(vars(args)["options"]))


def get_env_props() -> benedict:
    r = create_benedict(copy.deepcopy(vars(os.environ).get("_data")))
    append_props_from_args(r)
    return r
