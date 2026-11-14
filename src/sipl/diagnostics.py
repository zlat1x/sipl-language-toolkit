"""Structured diagnostics used by all toolchain interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from .ast import SourceSpan, to_data


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    span: SourceSpan

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "span": to_data(self.span)}


class SIPLError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        pos = diagnostic.span.start
        super().__init__(f"{pos.line}:{pos.column}: {diagnostic.code}: {diagnostic.message}")
