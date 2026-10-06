from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import ComponentContract


class ComponentAdapter(Protocol):
    """Nozomi's stable boundary around an execution backend such as Rikka."""

    def capabilities(self) -> tuple[ComponentContract, ...]: ...


@dataclass(frozen=True)
class RikkaAdapter:
    """Only exposes capability proven by the installed Rikka integration."""

    def capabilities(self) -> tuple[ComponentContract, ...]:
        # Current Rikka exposes only printname; it has no positioning component
        # contract, so publishing no positioning capability is intentional.
        return ()
