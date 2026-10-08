"""Pytest startup. Blocks live Chrome, CDP, and Sectura HTTP."""

from tests.live_network_guard import install

install()
