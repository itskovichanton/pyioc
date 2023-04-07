import functools
import inspect
import threading
from dataclasses import dataclass
from typing import Type, Optional, Any

from event_bus import EventBus
from opyoid import Injector, SingletonScope, Module
from opyoid.scopes import Scope

from src.mybootstrap_ioc_itskovichanton.env import get_env_props
from src.mybootstrap_ioc_itskovichanton.utils import infer_from_tuple, omittable_parentheses

_evbus = EventBus()
_event_bus_bound = False
_event_rebind = "fire_rebind"
_event_module_updated = "module_updated"
_injector: Injector = None
_lock = threading.Lock()


@dataclass
class Context:
    properties = get_env_props()
    profile = properties.get("profile", default="dev")


context = Context()


@dataclass
class _Bean:
    qualifier: Optional[str]
    scope: Type[Scope] = SingletonScope,
    self_bound: bool = False
    to_class: Any = None
    profile: str = None
    bound: bool = False


_beans: dict[Any, list[_Bean]] = {}


def _create_bean_init(method, prefs: _Bean, **kwargs):
    @functools.wraps(method)
    def _impl(self, *method_args, **method_kwargs):

        print("Init() called for", type(self), "hex =", hex(id(self)), "from bean =", prefs)

        setattr(self, "_context", context)
        for k, v in kwargs.items():
            v = infer_from_tuple(context.properties, v)
            kwargs[k] = v
            setattr(self, k, v)

        r = method(self, *method_args, **method_kwargs)

        if hasattr(self, 'init') and callable(self.init):
            init_method_spec = inspect.getfullargspec(self.init)
            if init_method_spec.varkw:
                self.init(**kwargs)
            else:
                self.init()

        return r

    return _impl


@omittable_parentheses(allow_partial=True)
def bean(scope: Type[Scope] = SingletonScope,
         qualifier: Optional[str] = None,
         self_bound: bool = False,
         profile: str = None,
         **kwargs):
    def discover(cl):
        print(f"Bean discovered: {cl.__name__}")
        if cl and hasattr(cl, "__bases__"):
            cl = dataclass(cl)
            prefs = _Bean(to_class=cl, scope=scope, self_bound=self_bound, profile=profile, qualifier=qualifier)
            for base in cl.__bases__:
                _beans.setdefault(base, []).append(prefs)
                _evbus.emit(_event_rebind, base, prefs)
            cl.__init__ = _create_bean_init(cl.__init__, prefs, **kwargs)

        return cl

    return discover


class _IocModule(Module):

    def configure(self) -> None:
        global _event_bus_bound

        self._bind_all()
        if not _event_bus_bound:
            _event_bus_bound = True
            _evbus.add_event(self._rebind, _event_rebind)

    def _bind_all(self):
        print("REBIND ALL BEANS")

        for target_type, beanList in _beans.items():
            for prefs in beanList:
                self._rebind(target_type, prefs)

    def _rebind(self, target_type, prefs):
        print("REBIND")

        if prefs.profile is None or prefs.profile == context.profile:
            if prefs.self_bound:
                target_type = prefs.to_class
            print(f"binding {target_type.__name__} --> {prefs.to_class.__name__}")
            self.bind(target_type, to_class=prefs.to_class, scope=prefs.scope)
            if not prefs.bound:
                prefs.bound = True
                _evbus.emit(_event_module_updated)
                print("bound")


def injector() -> Injector:
    return _injector


def _on_module_updated():
    global _injector
    with _lock:
        m = [_IocModule]
        if _injector:
            _injector.__init__(m)
        else:
            _injector = Injector(m)


_on_module_updated()
_evbus.add_event(_on_module_updated, _event_module_updated)
