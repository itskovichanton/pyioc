from opyoid import Injector
from paprika import singleton

from src.mybootstrap_ioc_itskovichanton import ioc
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.env import append_props_from_args
from src.mybootstrap_ioc_itskovichanton.utils import append_benedict

config_service: ConfigService


def print_banner():
    cfg = config_service.get_config()
    n = 50
    print("*" * n)
    print(f"*\tStarting {cfg.app.full_name()}")
    print(f"*\tProfile: {cfg.profile}")
    print("*" * n)


@singleton
def injector() -> Injector:
    _injector = ioc.injector()
    global config_service

    config_service = _injector.inject(ConfigService)
    append_benedict(ioc.context.properties, config_service.config.settings)
    append_props_from_args(ioc.context.properties)

    print_banner()
    return _injector
