from dataclasses import dataclass
from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.ioc import bean


class AbstractBean(Protocol):
    def hello(self) -> str:
        ...


@bean(profile="prod", qualifier="second")
class OtherBean(AbstractBean):

    def init(self):
        self.ready = True

    def hello(self) -> str:
        return "OtherBean"


@dataclass
class AcquiringConfig:
    currency: str
    lang: str
    url: str


@dataclass
class Item:
    a: int = None
    b: int = None


@bean(profile="dev", qualifier="first", p1="qcb", p2="email.encoding", p4=("a.b.c.d", None, {"x": 1, "y": 2}),
      p5=("a.b", int), p6=("l1.l2", list[Item], None), p7=("acquiring", dict[str, AcquiringConfig], None))
class MyBean(AbstractBean):

    def init(self, **kwargs):
        self.ready = True
        self.seen = dict(kwargs)

    def hello(self) -> str:
        return "MyBean"


class AbstractService:
    def do_smth(self) -> str:
        pass


@bean(profile="prod", appdata_env="APPDATA")
class ProdService(AbstractService):
    other_bean: AbstractBean

    def __init__(self, other_bean: AbstractBean):
        self.other_bean = other_bean

    def init(self):
        self.ready = True

    def do_smth(self) -> str:
        return f"prod via {self.other_bean.hello()} env={self.appdata_env}"


@bean(profile="dev", a="qcb.version")
class DevService(AbstractService):
    other_bean: AbstractBean

    def init(self, **kwargs):
        self.ready = True
        self.seen = dict(kwargs)

    def do_smth(self) -> str:
        return f"dev a={self.a} via {self.other_bean.hello()}"


def test_dev_profile_wires_dev_beans_and_config(ioc_state):
    ioc_state(
        profile="dev",
        **{
            "a.b": 130,
            "qcb.version": "1.1",
            "email.encoding": "utf-8",
        },
    )
    from src.mybootstrap_ioc_itskovichanton.ioc import injector

    service = injector().inject(AbstractService)
    assert isinstance(service, DevService)
    assert service.ready is True
    assert service.do_smth() == "dev a=1.1 via MyBean"
    assert service.seen["a"] == "1.1"
    bean = service.other_bean
    assert isinstance(bean, MyBean)
    assert bean.p5 == 130
    assert bean.p2 == "utf-8"
    assert bean.p4 == {"x": 1, "y": 2}
    assert bean.p6 is None
    assert bean.p7 is None
    assert bean.seen["p5"] == 130
    assert injector().inject(AbstractService) is service


def test_verbose_logs_container_build(ioc_state, monkeypatch, capsys):
    monkeypatch.setenv("PYIOC_VERBOSE", "True")
    ioc_state(profile="dev", **{"a.b": 1, "qcb.version": "1.1", "email.encoding": "utf-8"})
    out = capsys.readouterr().out
    assert "сборка контейнера, profile=dev" in out
    assert "bind AbstractBean -> MyBean" in out
    assert "skip OtherBean: profile=prod, активный=dev" in out
    assert "готово:" in out


def test_verbose_off_is_silent(ioc_state, monkeypatch, capsys):
    monkeypatch.delenv("PYIOC_VERBOSE", raising=False)
    ioc_state(profile="dev", **{"a.b": 1, "qcb.version": "1.1", "email.encoding": "utf-8"})
    assert "[pyioc]" not in capsys.readouterr().out


def test_prod_profile_wires_prod_beans(ioc_state):
    ioc_state(profile="prod")
    from src.mybootstrap_ioc_itskovichanton.ioc import injector

    service = injector().inject(AbstractService)
    assert isinstance(service, ProdService)
    assert isinstance(service.other_bean, OtherBean)
    assert service.ready is True
    assert service.other_bean.ready is True
    assert service.do_smth().startswith("prod via OtherBean env=")
