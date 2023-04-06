from opyoid import Injector

from src.mybootstrap_ioc_itskovichanton import ioc
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.utils import append_benedict

config_service: ConfigService


def injector() -> Injector:
    _injector = ioc.injector()
    global config_service

    config_service = _injector.inject(ConfigService)
    append_benedict(ioc.context.properties, config_service.config.settings)
    return _injector
