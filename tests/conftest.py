import pytest


@pytest.fixture
def ioc_state():
    from src.mybootstrap_ioc_itskovichanton import ioc

    def apply(profile=None, **props):
        if profile is not None:
            ioc.context.profile = profile
        for key, value in props.items():
            ioc.context.properties[key] = value
        ioc._dirty = True
        return ioc.injector()

    return apply
