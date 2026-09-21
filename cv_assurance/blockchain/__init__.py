"""
CV Assurance Blockchain Adapter Module.
Exposes Hyperledger Fabric evidence ledger anchoring and dual-layer verification.
"""

from blockchain.client import (
    AssuranceEvent,
    AssuranceEventType,
    BlockchainStatus,
    DualVerificationResult,
    MerkleTree,
    MerkleProof,
    FabricClient,
    BlockchainAnchorService,
    BlockchainDualVerifier
)

__all__ = [
    "AssuranceEvent",
    "AssuranceEventType",
    "BlockchainStatus",
    "DualVerificationResult",
    "MerkleTree",
    "MerkleProof",
    "FabricClient",
    "BlockchainAnchorService",
    "BlockchainDualVerifier"
]
