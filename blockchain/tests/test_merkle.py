import unittest
import hashlib
from blockchain.client.merkle import MerkleTree, MerkleProof


class TestMerkleTree(unittest.TestCase):
    def test_merkle_tree_construction_and_root(self):
        hashes = [
            hashlib.sha256(f"record_{i}".encode('utf-8')).hexdigest()
            for i in range(8)
        ]
        tree = MerkleTree(hashes)
        self.assertIsNotNone(tree.root)
        self.assertEqual(len(tree.root), 64)

    def test_merkle_inclusion_proof_validity(self):
        hashes = [
            hashlib.sha256(f"leaf_{i}".encode('utf-8')).hexdigest()
            for i in range(16)
        ]
        tree = MerkleTree(hashes)

        for idx in [0, 5, 10, 15]:
            proof = tree.get_proof(idx)
            self.assertIsNotNone(proof)
            self.assertTrue(MerkleTree.verify_proof(proof))

    def test_merkle_proof_detects_tampering(self):
        hashes = [
            hashlib.sha256(f"leaf_{i}".encode('utf-8')).hexdigest()
            for i in range(4)
        ]
        tree = MerkleTree(hashes)
        proof = tree.get_proof(2)

        # Alter target hash in proof
        tampered_proof = MerkleProof(
            target_hash=hashlib.sha256(b"tampered_data").hexdigest(),
            merkle_root=proof.merkle_root,
            proof_hashes=proof.proof_hashes,
            leaf_index=proof.leaf_index,
            total_leaves=proof.total_leaves
        )
        self.assertFalse(MerkleTree.verify_proof(tampered_proof))

    def test_odd_number_of_leaves(self):
        hashes = [
            hashlib.sha256(f"leaf_{i}".encode('utf-8')).hexdigest()
            for i in range(5)
        ]
        tree = MerkleTree(hashes)
        self.assertIsNotNone(tree.root)
        proof = tree.get_proof(4)
        self.assertTrue(MerkleTree.verify_proof(proof))


if __name__ == "__main__":
    unittest.main()
