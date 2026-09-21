import os
import pytest
import tempfile
import hashlib
from blockchain.client import (
    FabricClient,
    BlockchainAnchorService,
    BlockchainDualVerifier,
    AssuranceEventType,
    MerkleTree
)
from cv_assurance.provenance.crypto_binding import (
    CryptographicProvenanceEngine,
    PreprocessingConfig,
    InferenceOutputPrediction,
    ProtectedInferenceRecord
)
from cv_assurance.governance.report_schema import (
    AssuranceReport,
    RecommendedDisposition
)


@pytest.fixture
def temp_fabric_client():
    with tempfile.TemporaryDirectory() as temp_dir:
        ledger_file = os.path.join(temp_dir, "test_ledger.json")
        client = FabricClient(ledger_storage_path=ledger_file)
        yield client


def test_blockchain_status_telemetry(temp_fabric_client):
    status = temp_fabric_client.get_status()
    assert status.status == "CONNECTED"
    assert status.channel_id == "assurancechannel"
    assert status.ledger_height >= 1
    assert "AssuranceAuthorityMSP" in status.endorsing_organizations


def test_contributor_and_dataset_anchoring(temp_fabric_client):
    anchor_service = BlockchainAnchorService(temp_fabric_client)
    
    # 1. Contributor
    evt_contrib = anchor_service.client.register_contributor(
        contributor_id="contributor_B",
        org_msp="ContributorOrgMSP",
        metadata={"unit": "Surveillance Wing"}
    )
    assert evt_contrib.event_type == AssuranceEventType.CONTRIBUTOR_REGISTERED
    assert evt_contrib.contributor_id == "contributor_B"

    # 2. Risk quarantine
    evt_risk = anchor_service.anchor_contributor_risk(
        contributor_id="contributor_B",
        risk_score=0.85,
        risk_level="CRITICAL",
        dominant_factor="Label Manipulation",
        disposition="QUARANTINE"
    )
    assert evt_risk.event_type == AssuranceEventType.QUARANTINE_RECORDED
    assert evt_risk.disposition == "QUARANTINE"


def test_inference_dual_verification_pipeline(temp_fabric_client):
    anchor_service = BlockchainAnchorService(temp_fabric_client)
    prov_engine = CryptographicProvenanceEngine()
    verifier = BlockchainDualVerifier(temp_fabric_client, prov_engine)

    preds = [
        InferenceOutputPrediction(box=[50.0, 50.0, 100.0, 100.0], confidence=0.92, category_id=4, category_name="car")
    ]
    rec = prov_engine.create_protected_record(
        image_path_or_hash=b"FRAME_101_BYTES",
        model_hash="fdab8c003aa41f4c3795f97f" * 2,
        predictions=preds,
        sequence_number=1,
        nonce="fresh_nonce_101"
    )

    # Anchor to ledger
    anchor_service.anchor_inference_record(rec, contributor_id="contributor_A")

    # Clean verification
    dual_pass = verifier.verify_inference_record_dual(rec, image_bytes_or_path=b"FRAME_101_BYTES")
    assert dual_pass.local_verification_passed is True
    assert dual_pass.blockchain_hash_matched is True
    assert dual_pass.final_assurance_status == "TRUST_VERIFIED"
    assert dual_pass.recommended_disposition == "ACCEPT"


def test_merkle_batch_anchoring(temp_fabric_client):
    anchor_service = BlockchainAnchorService(temp_fabric_client)
    prov_engine = CryptographicProvenanceEngine()

    records = []
    for i in range(10):
        rec = prov_engine.create_protected_record(
            image_path_or_hash=f"FRAME_{i}".encode('utf-8'),
            model_hash="fdab8c003aa41f4c3795f97f" * 2,
            predictions=[InferenceOutputPrediction(box=[0, 0, 10, 10], confidence=0.9, category_id=1, category_name="car")],
            sequence_number=i + 1,
            nonce=f"nonce_{i}"
        )
        records.append(rec)

    event, tree = anchor_service.anchor_inference_batch(records, batch_id="BATCH_MERKLE_01")
    assert event.event_type == AssuranceEventType.INFERENCE_RECORDED
    assert event.merkle_root is not None
    assert event.batch_size == 10

    # Test inclusion proof for 5th record
    proof = tree.get_proof(4)
    assert MerkleTree.verify_proof(proof) is True
