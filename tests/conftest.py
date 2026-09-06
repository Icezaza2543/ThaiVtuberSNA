"""The suite never needs an owner's API credentials or a live network."""
import socket
import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', '')
    monkeypatch.setattr('collector.youtube_collector.YOUTUBE_API_KEY', '')
    monkeypatch.setattr('collector.live_chat_adapter.YOUTUBE_API_KEY', '')
    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected network access in offline test suite')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
