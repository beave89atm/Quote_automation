"""Mill and lathe quoting — machine roster + published-formula calculators.

Parallel to weld/fit-up. Does not invent shop-specific times: SFM/IPT come
from published catalog starting points; setup minutes are placeholders.
Does not push to SecturaFAB.
"""

from .config import (
    Machine,
    MachiningConfig,
    load_machine_roster,
    load_machining_config,
)
from .lathe import LatheQuoteInput, quote_lathe
from .mill import MillQuoteInput, quote_mill

__all__ = [
    "Machine",
    "MachiningConfig",
    "MillQuoteInput",
    "LatheQuoteInput",
    "load_machine_roster",
    "load_machining_config",
    "quote_mill",
    "quote_lathe",
]
