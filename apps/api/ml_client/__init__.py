"""Private local-ML adapter. Fixture mode is explicit and never a fallback."""
from .client import FixtureMLClient, RealMLClient
from .validation import validate_answer, validate_snapshot

__all__ = ['RealMLClient', 'FixtureMLClient', 'validate_snapshot', 'validate_answer']
