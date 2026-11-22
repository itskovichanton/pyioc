import functools
import inspect
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional, Type

from opyoid import Injector, Module, SingletonScope
from opyoid.scopes import Scope

from src.mybootstrap_ioc_itskovichanton import context as context_module
from src.mybootstrap_ioc_itskovichanton.context import preprocess_context
from src.mybootstrap_ioc_itskovichanton.env import get_env_props
from src.mybootstrap_ioc_itskovichanton.utils import infer_from_value, omittable_parentheses

_lock = threading.Lock()
_injector: Optional[Injector] = None
_dirty = True
_built_profile: Optional[str] = None
_init_kwargs_cache: dict[Callable, bool] = {}


@dataclass
class Context:
    properties = get_env_props()
    profile = context_module.profile or properties.get("profile", default="dev")


context = Context()
if preprocess_context:
    preprocess_context(context)


@dataclass
class _Bean:
    to_class: Any
    scope: Type[Scope] = SingletonScope
    self_bound: bool = False
    profile: Optional[str] = None
    qualifier: Optional[str] = None


# Пара (базовый класс, бин). Контейнер по этому списку собирается один раз.
_registrations: list[tuple[Any, _Bean]] = []


def _init_accepts_kwargs(init: Callable) -> bool:
    func = getattr(init, "__func__", init)
    cached = _init_kwargs_cache.get(func)
    if cached is not None:
        return cached
    takes = inspect.getfullargspec(func).varkw is not None
    _init_kwargs_cache[func] = takes
    return takes


def _create_bean_init(method, specs: tuple[tuple[str, Any], ...]):
    @functools.wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        setattr(self, "_context", context)
        resolved = {}
        for key, spec in specs:
            try:
                value = infer_from_value(context.properties, spec)
            except BaseException as ex:
                raise Exception(
                    f'Cannot infer bean "{type(self).__name__}" value for key={key}, cause={ex}'
                ) from ex
            resolved[key] = value
            setattr(self, key, value)

        result = method(self, *method_args, **method_kwargs)
        init = getattr(self, "init", None)
        if callable(init):
            if _init_accepts_kwargs(init):
                init(**resolved)
            else:
                init()
        return result

    return _impl


@omittable_parentheses(allow_partial=True)
def bean(scope: Type[Scope] = SingletonScope,
         qualifier: Optional[str] = None,
         self_bound: bool = False,
         profile: str = None,
         **kwargs):
    def discover(cl):
        global _dirty
        if not cl or not hasattr(cl, "__bases__"):
            return cl
        cl = dataclass(cl)
        prefs = _Bean(
            to_class=cl,
            scope=scope,
            self_bound=self_bound,
            profile=profile,
            qualifier=qualifier,
        )
        for base in cl.__bases__:
            _registrations.append((base, prefs))
        cl.__init__ = _create_bean_init(cl.__init__, tuple(kwargs.items()))
        # Импорт только помечает контейнер грязным. Сборка — на следующем inject.
        _dirty = True
        return cl

    return discover


class _IocModule(Module):

    def configure(self) -> None:
        for target_type, prefs in _registrations:
            if prefs.profile is not None and prefs.profile != context.profile:
                continue
            impl = prefs.to_class
            scope = prefs.scope
            if target_type is object or target_type is impl:
                self.bind(impl, scope=scope)
                continue
            self.bind(target_type, to_class=impl, scope=scope)
            if prefs.self_bound:
                self.bind(impl, scope=scope)


def _bound_inject(target_type, *, named=None):
    current = _ensure()
    return Injector.inject(current, target_type, named=named)


def _ensure() -> Injector:
    """Один Injector на профиль. Заново собирается, только если появился бин или сменился профиль."""
    global _injector, _dirty, _built_profile
    while True:
        profile = context.profile
        if _injector is not None and not _dirty and _built_profile == profile:
            return _injector
        with _lock:
            profile = context.profile
            if _injector is not None and not _dirty and _built_profile == profile:
                return _injector
            _dirty = False
            _built_profile = profile
            if _injector is None:
                _injector = Injector([_IocModule])
                _injector.inject = _bound_inject
            else:
                _injector.__init__([_IocModule])
            if not _dirty and _built_profile == context.profile:
                return _injector


def injector() -> Injector:
    return _ensure()
