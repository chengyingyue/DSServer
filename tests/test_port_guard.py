from __future__ import annotations

import socket

import pytest

from dsserver.__main__ import refuse_busy_port


def test_refuse_busy_port_exits_when_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind(("127.0.0.1", 0))
        held.listen()
        port = held.getsockname()[1]
        with pytest.raises(SystemExit):
            refuse_busy_port("127.0.0.1", port)


def test_refuse_busy_port_passes_when_free():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as free:
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
    refuse_busy_port("127.0.0.1", port)
