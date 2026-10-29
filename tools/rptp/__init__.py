# SPDX-License-Identifier: GPL-3.0-or-later
"""RPTP static recompiler building blocks.

The package is deliberately small and dependency-free: an ELF32/EM_MIPS
loader, an R5900 instruction decoder, a CFG/function-discovery pass, a
reference oracle and a deterministic C++20 emitter.  It does not implement
PS2 kernel services, VU, GS or IOP behaviour.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
