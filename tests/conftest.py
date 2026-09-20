"""The suite never needs an owner's API credentials or a live network."""
import socket
import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', '')
    orig_connect = socket.socket.connect

    def blocked(self, address, *args, **kwargs):
        if isinstance(address, tuple) and len(address) >= 1:
            host = address[0]
            if host in ('127.0.0.1', 'localhost', '::1'):
                return orig_connect(self, address, *args, **kwargs)
        raise AssertionError('Unexpected network access in offline test suite')

    monkeypatch.setattr(socket.socket, 'connect', blocked)
