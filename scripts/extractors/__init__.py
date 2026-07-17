"""Provider-specific ingestion modules."""

from .world_bank import WorldBankExtractor, WorldBankResponse

__all__ = ["WorldBankExtractor", "WorldBankResponse"]
