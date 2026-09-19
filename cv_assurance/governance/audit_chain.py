import os
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

GENESIS_PREVIOUS_HASH = "0" * 64

class AuditEvent(BaseModel):
    """
    Immutable audit event record participating in an append-only cryptographic hash chain.
    """
    event_id: str
    sequence_index: int
    timestamp_utc: float
    timestamp_iso: str
    event_type: str  # e.g., "PIPELINE_INIT", "DATASET_AUDIT", "MODEL_AUDIT", "SHIFT_AUDIT", "PROVENANCE_AUDIT", "GOVERNANCE_DISPOSITION"
    affected_asset: str
    event_summary: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str
    current_event_hash: str

    def canonical_payload(self) -> str:
        """
        Creates deterministic canonical representation of the event payload
        excluding current_event_hash.
        """
        payload = {
            "event_id": self.event_id,
            "sequence_index": self.sequence_index,
            "timestamp_utc": self.timestamp_utc,
            "timestamp_iso": self.timestamp_iso,
            "event_type": self.event_type,
            "affected_asset": self.affected_asset,
            "event_summary": self.event_summary,
            "event_data": self.event_data,
            "previous_event_hash": self.previous_event_hash
        }
        return json.dumps(payload, sort_keys=True, separators=(',', ':'))

    @classmethod
    def compute_event_hash(
        cls,
        event_id: str,
        sequence_index: int,
        timestamp_utc: float,
        timestamp_iso: str,
        event_type: str,
        affected_asset: str,
        event_summary: str,
        event_data: Dict[str, Any],
        previous_event_hash: str
    ) -> str:
        """
        Derives cryptographic SHA-256 digest linked to the previous event in the chain.
        """
        payload = {
            "event_id": event_id,
            "sequence_index": sequence_index,
            "timestamp_utc": timestamp_utc,
            "timestamp_iso": timestamp_iso,
            "event_type": event_type,
            "affected_asset": affected_asset,
            "event_summary": event_summary,
            "event_data": event_data,
            "previous_event_hash": previous_event_hash
        }
        canonical_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()


class TamperEvidentAuditChain:
    """
    Offline append-only cryptographic hash chain for trustworthy audit assurance.
    Guarantees mathematical tamper-evidence without external cloud or blockchain dependencies.
    """

    def __init__(self, chain_file: Optional[str] = None):
        self.chain_file = chain_file
        self.events: List[AuditEvent] = []
        if self.chain_file and os.path.exists(self.chain_file):
            self.load()

    @property
    def latest_hash(self) -> str:
        """Returns current hash head of the chain."""
        if not self.events:
            return GENESIS_PREVIOUS_HASH
        return self.events[-1].current_event_hash

    @property
    def chain_length(self) -> int:
        return len(self.events)

    def append_event(
        self,
        event_type: str,
        affected_asset: str,
        event_summary: str,
        event_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None
    ) -> AuditEvent:
        """
        Appends an event to the hash chain, computing current_event_hash
        derived from canonical payload and previous_event_hash.
        """
        seq_idx = len(self.events)
        ts = time.time()
        ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        evt_id = event_id or f"AUD-EVT-{seq_idx:04d}"
        data = event_data or {}
        prev_hash = self.latest_hash

        curr_hash = AuditEvent.compute_event_hash(
            event_id=evt_id,
            sequence_index=seq_idx,
            timestamp_utc=ts,
            timestamp_iso=ts_iso,
            event_type=event_type,
            affected_asset=affected_asset,
            event_summary=event_summary,
            event_data=data,
            previous_event_hash=prev_hash
        )

        event = AuditEvent(
            event_id=evt_id,
            sequence_index=seq_idx,
            timestamp_utc=ts,
            timestamp_iso=ts_iso,
            event_type=event_type,
            affected_asset=affected_asset,
            event_summary=event_summary,
            event_data=data,
            previous_event_hash=prev_hash,
            current_event_hash=curr_hash
        )

        self.events.append(event)
        self.save()
        return event

    def verify_chain(self) -> Tuple[bool, str, Optional[int]]:
        """
        Verifies mathematical integrity of all events in the hash chain.
        Returns:
            (is_valid, verification_message, corrupted_event_index)
        """
        if not self.events:
            return True, "Audit chain is empty; no events to verify.", None

        expected_prev_hash = GENESIS_PREVIOUS_HASH

        for idx, event in enumerate(self.events):
            # 1. Check sequence index
            if event.sequence_index != idx:
                return False, f"Sequence discontinuity at index {idx}: expected {idx}, found {event.sequence_index}.", idx

            # 2. Check previous hash linkage
            if event.previous_event_hash != expected_prev_hash:
                return (
                    False,
                    f"Hash chain broken at event #{idx} ({event.event_id}): "
                    f"previous_hash '{event.previous_event_hash[:16]}...' does not match expected '{expected_prev_hash[:16]}...'.",
                    idx
                )

            # 3. Recompute and verify current hash
            recomputed_hash = AuditEvent.compute_event_hash(
                event_id=event.event_id,
                sequence_index=event.sequence_index,
                timestamp_utc=event.timestamp_utc,
                timestamp_iso=event.timestamp_iso,
                event_type=event.event_type,
                affected_asset=event.affected_asset,
                event_summary=event.event_summary,
                event_data=event.event_data,
                previous_event_hash=event.previous_event_hash
            )

            if recomputed_hash != event.current_event_hash:
                return (
                    False,
                    f"Tampering detected in event payload at #{idx} ({event.event_id}): "
                    f"stored current_hash '{event.current_event_hash[:16]}...' differs from recomputed digest '{recomputed_hash[:16]}...'.",
                    idx
                )

            expected_prev_hash = event.current_event_hash

        return True, f"Audit hash chain verified unbroken and tamper-free across all {len(self.events)} events.", None

    def export_log(self) -> List[Dict[str, Any]]:
        """Exports all audit events as list of dictionaries."""
        return [e.model_dump() for e in self.events]

    def save(self) -> None:
        """Atomically saves audit chain to local JSON file if configured."""
        if not self.chain_file:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.chain_file)), exist_ok=True)
        tmp_file = f"{self.chain_file}.tmp.{os.getpid()}"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(self.export_log(), f, indent=2)
        os.replace(tmp_file, self.chain_file)

    def load(self) -> None:
        """Loads audit chain from local JSON file."""
        if not self.chain_file or not os.path.exists(self.chain_file):
            return
        try:
            with open(self.chain_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.events = [AuditEvent(**item) for item in data]
        except Exception:
            self.events = []

    def clear(self) -> None:
        """Clears audit chain (useful for testing)."""
        self.events = []
        if self.chain_file and os.path.exists(self.chain_file):
            try:
                os.remove(self.chain_file)
            except OSError:
                pass
