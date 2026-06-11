"""Shared pytest fixtures for the smith test suite.

Mirrors src/ layout: controller/, motor/, manager/ subpackages hold the focused
tests; reusable fakes and setups live here and under fixtures/.

Marker taxonomy (declared in pyproject.toml): unit · integration · sil · hil.

TODO: add fixtures (in-memory pub/sub, mock transport, BotConfig factory) as the
package fills in.
"""
from __future__ import annotations
