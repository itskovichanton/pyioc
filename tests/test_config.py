import sys

from src.mybootstrap_ioc_itskovichanton.config import App, Config, ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


_YAML = """
app:
  name: Ядро
  version: "2"
email:
  host: root-host
  port: 25
dev:
  email:
    host: dev-host
    user: ann
  extra:
    flag: 1
prod:
  email:
    host: prod-host
"""


def test_app_and_config_names():
    app = App("Ядро", "2")
    cfg = Config(app=app, settings=None, profile="prod")
    assert app.full_name() == "Ядро-2"
    assert cfg.full_name() == "Ядро-2-[prod]"
    assert cfg.is_prod() is True
    assert Config(app=app, settings=None, profile="dev").is_prod() is False


def test_profile_fills_missing_keys_and_keeps_root(tmp_path, ioc_state):
    path = tmp_path / "config.yml"
    path.write_text(_YAML, encoding="utf-8")
    inj = ioc_state(profile="dev", **{"config-file": str(path), "workdir": str(tmp_path)})
    cfg = inj.inject(ConfigService)
    config = cfg.get_config()
    assert config.profile == "dev"
    assert config.is_prod() is False
    assert config.app.full_name() == "Ядро-2"
    assert config.settings["email.host"] == "root-host"
    assert config.settings["email.port"] == 25
    assert config.settings["email.user"] == "ann"
    assert config.settings["extra.flag"] == 1
    assert (tmp_path / "Ядро-2" / "work" / "dev").is_dir()
    logs = cfg.dir("logs")
    assert logs.endswith("Ядро-2/work/dev/logs") or logs.endswith("Ядро-2\\work\\dev\\logs")
    assert __import__("os").path.isdir(logs)

    from src.mybootstrap_ioc_itskovichanton import ioc

    ioc.context.profile = "prod"
    ioc._dirty = True
    prod = ioc.injector().inject(ConfigService).get_config()
    assert prod.is_prod() is True
    assert prod.settings["email.host"] == "root-host"


def test_missing_profile_section_raises(tmp_path, ioc_state):
    path = tmp_path / "config.yml"
    path.write_text("app:\n  name: A\n  version: '1'\n", encoding="utf-8")
    inj = ioc_state(profile="dev", **{"config-file": str(path), "workdir": str(tmp_path)})
    try:
        inj.inject(ConfigService)
        raise AssertionError("a config without the profile section must fail")
    except KeyError:
        pass


def test_di_merges_yaml_then_cli_and_sees_a_later_bean(tmp_path, monkeypatch, capsys):
    path = tmp_path / "config.yml"
    path.write_text(_YAML, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["app", "scenario.token=from-cli"])

    from src.mybootstrap_ioc_itskovichanton import di, ioc

    ioc.context.profile = "dev"
    ioc.context.properties["config-file"] = str(path)
    ioc.context.properties["workdir"] = str(tmp_path)
    ioc._dirty = True
    di.injector.instance = None

    inj = di.injector()
    out = capsys.readouterr().out
    assert "Ядро-2" in out
    assert "dev" in out
    assert ioc.context.properties["email.host"] == "root-host"
    assert ioc.context.properties["email.user"] == "ann"
    assert ioc.context.properties["scenario.token"] == "from-cli"
    assert di.injector() is inj

    @bean(user=("email.user", str), token=("scenario.token", str))
    class MailUser:
        pass

    mail = inj.inject(MailUser)
    assert mail.user == "ann"
    assert mail.token == "from-cli"
