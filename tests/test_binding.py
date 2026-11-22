from dataclasses import dataclass
from typing import Protocol

from opyoid import PerLookupScope
from opyoid.exceptions import NoBindingFound

from src.mybootstrap_ioc_itskovichanton.ioc import bean


class Port(Protocol):
    def ping(self) -> str:
        ...


class Api(Protocol):
    def name(self) -> str:
        ...


class Svc(Protocol):
    def n(self) -> int:
        ...


def test_singleton_is_reused_and_bare_decorator_calls_init(ioc_state):
    @bean
    class Bare:
        def init(self):
            self.ready = True

    inj = ioc_state()
    first = inj.inject(Bare)
    second = inj.inject(Bare)
    assert first is second
    assert first.ready is True


def test_qualifier_does_not_hide_the_default_binding(ioc_state):
    @bean(qualifier="named")
    class Named:
        def value(self) -> str:
            return "named"

    inj = ioc_state()
    assert inj.inject(Named).value() == "named"


def test_per_lookup_rereads_config(ioc_state):
    @bean(scope=PerLookupScope, n=("box.n", int, 1))
    class Box:
        def init(self, **kwargs):
            self.seen = kwargs["n"]

    inj = ioc_state(**{"box.n": "4"})
    first = inj.inject(Box)
    assert first.n == 4
    assert first.seen == 4
    assert first is not inj.inject(Box)

    from src.mybootstrap_ioc_itskovichanton import ioc

    ioc.context.properties["box.n"] = "9"
    second = inj.inject(Box)
    assert second.n == 9
    assert second.seen == 9


def test_missing_required_property_names_the_field(ioc_state):
    @bean(port=("missing.port", int))
    class NeedsPort:
        pass

    inj = ioc_state()
    try:
        inj.inject(NeedsPort)
        raise AssertionError("expected a missing property to fail")
    except Exception as ex:
        assert "key=port" in str(ex)


def test_profile_selects_one_implementation(ioc_state):
    created = []

    @bean(profile="dev")
    class DevPort(Port):
        def init(self):
            created.append("dev")

        def ping(self) -> str:
            return "dev"

    @bean(profile="prod")
    class ProdPort(Port):
        def init(self):
            created.append("prod")

        def ping(self) -> str:
            return "prod"

    inj = ioc_state(profile="dev")
    assert inj.inject(Port).ping() == "dev"
    assert created == ["dev"]
    try:
        inj.inject(ProdPort)
        raise AssertionError("prod bean must stay unbound on the dev profile")
    except NoBindingFound:
        pass

    from src.mybootstrap_ioc_itskovichanton import ioc

    ioc.context.profile = "prod"
    assert inj.inject(Port).ping() == "prod"
    assert created == ["dev", "prod"]


def test_later_bean_overrides_the_same_protocol(ioc_state):
    @bean
    class First(Svc):
        def n(self) -> int:
            return 1

    @bean
    class Second(Svc):
        def n(self) -> int:
            return 2

    inj = ioc_state()
    assert inj.inject(Svc).n() == 2
    assert inj.inject(First).n() == 1
    assert inj.inject(Second).n() == 2


def test_self_bound_keeps_the_protocol(ioc_state):
    @bean(self_bound=True)
    class OnlySelf(Api):
        def name(self) -> str:
            return "self"

    inj = ioc_state()
    assert inj.inject(Api).name() == "self"
    assert inj.inject(OnlySelf).name() == "self"


def test_values_are_cast_into_dataclasses(ioc_state):
    @dataclass
    class Item:
        a: int = None
        b: int = None

    @bean(nums=("bag.nums", list[Item], None), n=("bag.n", int, 3), label="not.a.real.key")
    class Bag:
        pass

    inj = ioc_state(**{"bag.n": "4", "bag.nums": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]})
    bag = inj.inject(Bag)
    assert bag.n == 4
    assert [(item.a, item.b) for item in bag.nums] == [(1, 2), (3, 4)]
    assert bag.label == "not.a.real.key"


def test_many_beans_rebuild_the_injector_once(monkeypatch, capsys):
    import src.mybootstrap_ioc_itskovichanton.ioc as ioc

    first = ioc.injector()
    calls = []
    real_init = ioc.Injector.__init__

    def counting(self, *args, **kwargs):
        calls.append(1)
        return real_init(self, *args, **kwargs)

    monkeypatch.setattr(ioc.Injector, "__init__", counting)
    created = []
    for i in range(40):
        @bean
        class Item:
            pass

        Item.marker = i
        created.append(Item)

    captured = capsys.readouterr()
    assert "Bean discovered" not in captured.out
    assert "Rebind" not in captured.out
    assert "binding " not in captured.out
    assert calls == []

    got = ioc.injector().inject(created[-1])
    assert got.marker == 39
    assert calls == [1]
    assert ioc.injector() is first
    assert ioc.injector().inject(created[0]).marker == 0
    assert calls == [1]
