import os
import sys
import json
import argparse
from typing import Optional

from .governance.engine import AssuranceEngine
from .provenance.crypto_binding import (
    CryptographicProvenanceEngine,
    InferenceOutputPrediction,
    ProtectedInferenceRecord,
    ReplayProtectionRegistry
)
from .model.hasher import ModelHasher

def main():
    parser = argparse.ArgumentParser(
        description="Trustworthy Computer Vision Integrity Assurance Framework CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run full integrity & risk analysis on dataset & model")
    analyze_parser.add_argument("--dataset", required=True, help="Path to evaluation dataset (COCO json or YOLO folder)")
    analyze_parser.add_argument("--model", required=False, help="Path to model file (.pt, .pth, .onnx)")
    analyze_parser.add_argument("--ref-dataset", required=False, help="Path to reference dataset for distribution shift check")
    analyze_parser.add_argument("--ref-model-hash", required=False, help="Expected SHA-256 model digest hash")
    analyze_parser.add_argument("--output-json", required=False, help="Path to save report JSON output")

    # Subcommand: bind-inference
    bind_parser = subparsers.add_parser("bind-inference", help="Create cryptographically bound inference record")
    bind_parser.add_argument("--image", required=True, help="Path to input image file")
    bind_parser.add_argument("--model-hash", required=False, help="Model SHA-256 hash digest (or specify --model)")
    bind_parser.add_argument("--model", required=False, help="Path to model file (automatically calculates SHA-256)")
    bind_parser.add_argument("--predictions", required=True, help="JSON string or path to JSON file containing predictions")
    bind_parser.add_argument("--config", required=False, help="Path to preprocessing config JSON file or JSON string")
    bind_parser.add_argument("--sequence-number", type=int, default=1, help="Monotonically increasing sequence number")
    bind_parser.add_argument("--secret-key", required=False, help="HMAC secret key override (or set CV_INFERENCE_SECRET_KEY)")
    bind_parser.add_argument("--output-json", required=False, help="Path to save protected record JSON")

    # Subcommand: verify-inference
    verify_parser = subparsers.add_parser("verify-inference", help="Verify cryptographic integrity of an inference record")
    verify_parser.add_argument("--record-json", required=True, help="Path to protected inference record JSON file")
    verify_parser.add_argument("--image", required=False, help="Path to input image file to verify against record image hash")
    verify_parser.add_argument("--model", required=False, help="Path to model file to verify against record model digest")
    verify_parser.add_argument("--registry", required=False, help="Path to local replay registry JSON file")
    verify_parser.add_argument("--register-on-success", action="store_true", help="Register record into replay registry if verification succeeds")
    verify_parser.add_argument("--secret-key", required=False, help="HMAC secret key override (or set CV_INFERENCE_SECRET_KEY)")

    # Subcommand: verify-inference-chain
    chain_parser = subparsers.add_parser("verify-inference-chain", help="Verify cryptographic integrity and sequence ordering of an inference chain")
    chain_parser.add_argument("--records-json", required=True, help="Path to JSON file containing list of protected inference records")
    chain_parser.add_argument("--registry", required=False, help="Path to local replay registry JSON file")
    chain_parser.add_argument("--secret-key", required=False, help="HMAC secret key override (or set CV_INFERENCE_SECRET_KEY)")

    # Subcommand: benchmark-generate
    gen_parser = subparsers.add_parser("benchmark-generate", help="Generate reproducible multi-contributor attack benchmark")
    gen_parser.add_argument("--ref-dataset", required=False, help="Path to reference dataset (COCO or VisDrone)")
    gen_parser.add_argument("--output-dir", default="data", help="Output directory")
    gen_parser.add_argument("--num-samples", type=int, default=60, help="Number of samples to generate")
    gen_parser.add_argument("--seed", type=int, default=42, help="Random seed")

    # Subcommand: benchmark-evaluate
    eval_parser = subparsers.add_parser("benchmark-evaluate", help="Evaluate detector metrics against ground truth manifest")
    eval_parser.add_argument("--dataset", default="data/dataset_manifest.json", help="Path to evaluation dataset manifest")
    eval_parser.add_argument("--ground-truth", default="data/ground_truth/attack_manifest.json", help="Path to ground truth manifest")
    eval_parser.add_argument("--ref-dataset", default="data/reference/manifest.json", help="Path to reference manifest")
    eval_parser.add_argument("--output-json", required=False, help="Path to save evaluation metrics JSON")

    args = parser.parse_args()

    if args.command == "benchmark-generate":
        from scripts.generate_attacks import generate_benchmark_attacks
        generate_benchmark_attacks(
            reference_dataset_path=args.ref_dataset,
            output_dir=args.output_dir,
            num_samples=args.num_samples,
            seed=args.seed
        )

    elif args.command == "benchmark-evaluate":
        from scripts.evaluate_attacks import run_evaluation
        run_evaluation(
            dataset_path=args.dataset,
            ground_truth_manifest_path=args.ground_truth,
            ref_dataset_path=args.ref_dataset,
            output_metrics_json=args.output_json
        )

    elif args.command == "analyze":
        engine = AssuranceEngine()
        print(f"[*] Starting Computer Vision Integrity Assurance Evaluation...")
        print(f"    Target Dataset: {args.dataset}")
        if args.model:
            print(f"    Target Model:   {args.model}")

        report = engine.run_full_assurance(
            dataset_path=args.dataset,
            model_path=args.model,
            ref_dataset_path=args.ref_dataset,
            reference_model_hash=args.ref_model_hash
        )

        print("\n" + "="*70)
        print(f"               AI ASSURANCE EVALUATION REPORT ({report.report_id})")
        print("="*70)
        print(f"Overall System Health Score: {report.overall_health_score} / 100.0")
        print(f"Overall Recommended Disposition: [{report.overall_disposition.value}]")
        print(f"Audit Trail Hash: {report.audit_trail_hash}")
        print(f"Total Findings Flagged: {len(report.findings)}")
        print("-" * 70)

        for idx, f in enumerate(report.findings, 1):
            print(f"\nFinding #{idx}: [{f.severity.value}] {f.title}")
            print(f"  Asset:        {f.affected_asset}")
            print(f"  Reason:       {f.human_readable_reason}")
            print(f"  Confidence:   {f.confidence_score * 100}%")
            print(f"  Disposition:  {f.recommended_disposition.value}")

        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as out_f:
                out_f.write(report.model_dump_json(indent=2) if hasattr(report, "model_dump_json") else report.json(indent=2))
            print(f"\n[+] Full JSON report successfully exported to: {args.output_json}")

    elif args.command == "bind-inference":
        # Resolve model hash
        model_hash = args.model_hash
        if not model_hash:
            if args.model:
                model_hash = ModelHasher.compute_file_sha256(args.model)
            else:
                print("[-] Error: Either --model-hash or --model must be provided.")
                sys.exit(1)

        # Parse predictions from json string or file
        if os.path.isfile(args.predictions):
            with open(args.predictions, 'r', encoding='utf-8') as pf:
                raw_preds = json.load(pf)
        else:
            raw_preds = json.loads(args.predictions)

        preds = [InferenceOutputPrediction(**p) for p in raw_preds]

        # Parse preprocessing configuration if provided
        cfg_dict = {"resolution": [640, 640], "confidence_threshold": 0.50}
        if args.config:
            if os.path.isfile(args.config):
                with open(args.config, 'r', encoding='utf-8') as cf:
                    cfg_dict = json.load(cf)
            else:
                cfg_dict = json.loads(args.config)

        prov = CryptographicProvenanceEngine(secret_key=args.secret_key)
        record = prov.create_protected_record(
            image_path_or_hash=args.image,
            model_hash=model_hash,
            config_dict=cfg_dict,
            predictions=preds,
            sequence_number=args.sequence_number
        )

        print("\n[+] Created Protected Inference Record:")
        print(record.model_dump_json(indent=2) if hasattr(record, "model_dump_json") else record.json(indent=2))

        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                f.write(record.model_dump_json(indent=2) if hasattr(record, "model_dump_json") else record.json(indent=2))
            print(f"[+] Saved record to: {args.output_json}")

    elif args.command == "verify-inference":
        with open(args.record_json, 'r', encoding='utf-8') as f:
            rec_dict = json.load(f)

        record = ProtectedInferenceRecord(**rec_dict)
        registry = ReplayProtectionRegistry(args.registry) if args.registry else None

        prov = CryptographicProvenanceEngine(secret_key=args.secret_key)
        res = prov.verify_record(
            record,
            image_path=args.image,
            model_path=args.model,
            replay_registry=registry,
            register_if_valid=args.register_on_success
        )

        print("\n" + "=" * 56)
        print("          INFERENCE RECORD VERIFICATION")
        print("=" * 56)
        print(f"Record ID:           {res.record_id}")
        status_str = "PASS" if res.verification_passed else "FAIL (TAMPER DETECTED)"
        if res.replay_detected:
            status_str = "FAIL (REPLAY DETECTED)"
        print(f"Verification Status: [{status_str}]")
        print(f"Verification Passed: {res.verification_passed}")
        print(f"Tamper Detected:     {res.tamper_detected}")
        print(f"Replay Detected:     {res.replay_detected}")

        if res.field_verifications:
            print("\nField Integrity Checks:")
            for field_name, passed in res.field_verifications.items():
                mark = "[PASS]" if passed else "[FAIL]"
                print(f"  * {field_name:<22}: {mark}")

        if res.tampered_fields:
            print(f"\nViolated Fields:     {', '.join(res.tampered_fields)}")

        print(f"\nDetails:\n  {res.details}")
        print("=" * 56)

        if not res.verification_passed:
            sys.exit(1)

    elif args.command == "verify-inference-chain":
        with open(args.records_json, 'r', encoding='utf-8') as f:
            chain_list = json.load(f)

        records = [ProtectedInferenceRecord(**r) for r in chain_list]
        registry = ReplayProtectionRegistry(args.registry) if args.registry else None
        prov = CryptographicProvenanceEngine(secret_key=args.secret_key)

        print("\n" + "=" * 56)
        print(f"   INFERENCE CHAIN VERIFICATION ({len(records)} Records)")
        print("=" * 56)

        chain_valid = True
        last_seq = None
        last_ts = None
        seen_nonces = set()

        for idx, rec in enumerate(records, 1):
            res = prov.verify_record(rec, replay_registry=registry, register_if_valid=True)
            seq_valid = True
            ts_valid = True
            nonce_valid = (rec.nonce not in seen_nonces)
            seen_nonces.add(rec.nonce)

            if last_seq is not None and rec.sequence_number != last_seq + 1:
                seq_valid = False
                chain_valid = False

            if last_ts is not None and rec.timestamp_utc < last_ts:
                ts_valid = False
                chain_valid = False

            last_seq = rec.sequence_number
            last_ts = rec.timestamp_utc

            if not res.verification_passed or not seq_valid or not ts_valid or not nonce_valid:
                chain_valid = False
                print(f"  Record #{idx} [{rec.record_id}]: FAILED (Seq: {rec.sequence_number}, Tamper: {res.tamper_detected}, Replay: {res.replay_detected})")
            else:
                print(f"  Record #{idx} [{rec.record_id}]: PASS (Seq: {rec.sequence_number}, Nonce: {rec.nonce[:8]}...)")

        print("-" * 56)
        print(f"Chain Verification Status: [{'PASS' if chain_valid else 'FAIL'}]")
        print("=" * 56)

        if not chain_valid:
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
