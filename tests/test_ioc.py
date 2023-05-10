from dataclasses import dataclass
from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.ioc import bean


class AbstractBean(Protocol):
    def hello(self):
        ...


@bean(profile="prod", qualifier="second")
class OtherBean(AbstractBean):

    def init(self):
        print("OtherBean Constructed")

    def hello(self):
        print("Hello from OtherBean")


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
    # other_bean: OtherBean

    def init(self, **kwargs):
        print("MyBean Constructed")
        print(self.info())
        print(self.p6)
        print(self.p5)
        print(self.p7)

    def info(self) -> str:
        return f"info() = {self.p4}"

    def hello(self):
        print("Hello from MyBean")


class AbstractService:
    def do_smth(self):
        pass


@bean(profile="prod", appdata_env="APPDATA")
class ProdService(AbstractService):
    other_bean: AbstractBean

    def __init__(self, other_bean: AbstractBean):
        print("__init__")
        self.other_bean = other_bean

    def init(self):
        print("ProdService Constructed")

    def do_smth(self):
        print("do_smth() prints")
        self.other_bean.hello()
        print(f"I am ProdBean and i'm working! {self.appdata_env}")


@bean(profile="dev", a="qcb.version")
class DevService(AbstractService):
    other_bean: AbstractBean  # = field(init=False, default=None, metadata={"qualifier": "second"})

    def init(self, **kwargs):
        print("DevBean Constructed")

    def do_smth(self):
        self.other_bean.hello()
        print(f"I am DevBean and i'm working! a={self.a}")
