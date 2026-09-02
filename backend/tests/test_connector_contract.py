"""T40 — the typed connector contract. Zero connector test coverage
existed before this (confirmed: no test_connector*.py / test_*_connector.py
anywhere in this suite), matching the report's own "shared function call,
not a typed contract" finding — this both proves the contract holds and
gives the connectors their first regression coverage."""
import pytest

from app.services.connector_base import Connector, get_enabled_connectors
from app.services.watched_folder_connector import WatchedFolderConnector
from app.services.sftp_connector import SFTPConnector
from app.services.email_connector import EmailConnector


@pytest.mark.parametrize("connector_cls", [WatchedFolderConnector, SFTPConnector, EmailConnector])
def test_each_connector_satisfies_the_protocol(connector_cls):
    instance = connector_cls()
    assert isinstance(instance, Connector)
    assert isinstance(instance.name, str) and instance.name


def test_connector_names_are_unique():
    names = {WatchedFolderConnector().name, SFTPConnector().name, EmailConnector().name}
    assert len(names) == 3


def test_get_enabled_connectors_excludes_email_by_default():
    from app.config import settings

    original = settings.email_enabled
    try:
        settings.email_enabled = False
        connectors = get_enabled_connectors()
        assert {c.name for c in connectors} == {"watched_folder", "sftp"}
    finally:
        settings.email_enabled = original


def test_get_enabled_connectors_includes_email_when_enabled():
    from app.config import settings

    original = settings.email_enabled
    try:
        settings.email_enabled = True
        connectors = get_enabled_connectors()
        assert {c.name for c in connectors} == {"watched_folder", "sftp", "email"}
    finally:
        settings.email_enabled = original


@pytest.mark.asyncio
async def test_poll_once_delegates_to_module_function(monkeypatch):
    """The wrapper classes must not reimplement polling logic — they
    delegate to the existing module-level functions other tests/scripts
    already call directly, so this stays additive, not a rewrite."""
    called = {}

    async def fake_poll():
        called["hit"] = True
        return 3

    monkeypatch.setattr("app.services.sftp_connector.poll_sftp_once", fake_poll)
    result = await SFTPConnector().poll_once()
    assert result == 3
    assert called.get("hit")
