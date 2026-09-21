import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class MerkleProof(BaseModel):
    """Cryptographic Merkle inclusion proof for a single batch element."""
    target_hash: str
    merkle_root: str
    proof_hashes: List[Tuple[str, str]]  # list of (direction 'L'/'R', sibling_hash)
    leaf_index: int
    total_leaves: int


class MerkleTree:
    """
    Cryptographic Merkle Tree for batching high-throughput inference records
    into a single immutable blockchain transaction anchor.
    """

    def __init__(self, leaf_hashes: Optional[List[str]] = None):
        self.leaf_hashes: List[str] = [h.lower() for h in (leaf_hashes or []) if h]
        self.tree_levels: List[List[str]] = []
        if self.leaf_hashes:
            self.build_tree()

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        combined = f"{left.lower()}:{right.lower()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def add_leaf(self, leaf_hash: str) -> None:
        if leaf_hash:
            self.leaf_hashes.append(leaf_hash.lower())
            self.build_tree()

    def build_tree(self) -> None:
        if not self.leaf_hashes:
            self.tree_levels = []
            return

        current_level = list(self.leaf_hashes)
        self.tree_levels = [current_level]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = self._hash_pair(left, right)
                next_level.append(parent)
            self.tree_levels.append(next_level)
            current_level = next_level

    @property
    def root(self) -> Optional[str]:
        if not self.tree_levels or not self.tree_levels[-1]:
            return None
        return self.tree_levels[-1][0]

    def get_proof(self, leaf_index: int) -> Optional[MerkleProof]:
        if not self.leaf_hashes or leaf_index < 0 or leaf_index >= len(self.leaf_hashes):
            return None

        target_hash = self.leaf_hashes[leaf_index]
        proof_hashes: List[Tuple[str, str]] = []
        idx = leaf_index

        for level in self.tree_levels[:-1]:
            is_right_child = (idx % 2 == 1)
            sibling_idx = idx - 1 if is_right_child else idx + 1
            if sibling_idx < len(level):
                direction = 'L' if is_right_child else 'R'
                proof_hashes.append((direction, level[sibling_idx]))
            else:
                # Sibling duplicated
                proof_hashes.append(('R', level[idx]))
            idx = idx // 2

        return MerkleProof(
            target_hash=target_hash,
            merkle_root=self.root or "",
            proof_hashes=proof_hashes,
            leaf_index=leaf_index,
            total_leaves=len(self.leaf_hashes)
        )

    @classmethod
    def verify_proof(cls, proof: MerkleProof) -> bool:
        """
        Verifies that the target hash deterministically computes to the expected root.
        """
        current_hash = proof.target_hash.lower()
        for direction, sibling_hash in proof.proof_hashes:
            if direction == 'L':
                current_hash = cls._hash_pair(sibling_hash, current_hash)
            else:
                current_hash = cls._hash_pair(current_hash, sibling_hash)
        return current_hash.lower() == proof.merkle_root.lower()
