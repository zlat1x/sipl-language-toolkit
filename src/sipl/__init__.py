"""SIPL Language Toolkit public API."""
from .parser import parse
from .interpreter import execute
from .semantics import build, evaluate

__version__ = "1.0.0"
__all__ = ["parse", "execute", "build", "evaluate"]
