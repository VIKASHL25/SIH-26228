import os
import sys
import json
import argparse
from typing import Optional

from .governance.engine import AssuranceEngine
from .provenance.crypto_binding import CryptographicProvenanceEngine, InferenceOutputPrediction

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
    bind_parser.add_argument("--model-hash", required=True, help="Model SHA-256 hash digest")
    bind_parser.add_argument("--predictions", required=True, help="JSON string of predictions [box, confidence, category_id, category_name]")
    bind_parser.add_argument("--output-json", required=False, help="Path to save protected record JSON")

    # Subcommand: verify-inference
    verify_parser = subparsers.add_parser("verify-inference", help="Verify cryptographic integrity of an inference record")
    verify_parser.add_argument("--record-json", required=True, help="Path to protected inference record JSON file")

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
        prov = CryptographicProvenanceEngine()
        raw_preds = json.loads(args.predictions)
        preds = [InferenceOutputPrediction(**p) for p in raw_preds]
        
        record = prov.create_protected_record(
            image_path_or_hash=args.image,
            model_hash=args.model_hash,
            config_dict={"resolution": [640, 640], "confidence_threshold": 0.5},
            predictions=preds
        )
        
        print("\n[+] Created Protected Inference Record:")
        print(record.model_dump_json(indent=2) if hasattr(record, "model_dump_json") else record.json(indent=2))
        
        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                f.write(record.model_dump_json(indent=2) if hasattr(record, "model_dump_json") else record.json(indent=2))
            print(f"[+] Saved record to: {args.output_json}")

    elif args.command == "verify-inference":
        prov = CryptographicProvenanceEngine()
        with open(args.record_json, 'r', encoding='utf-8') as f:
            rec_dict = json.load(f)
        from .provenance.crypto_binding import ProtectedInferenceRecord
        record = ProtectedInferenceRecord(**rec_dict)
        res = prov.verify_record(record)
        
        print("\n" + "="*50)
        print("          INFERENCE RECORD VERIFICATION")
        print("="*50)
        print(f"Record ID:           {res.record_id}")
        print(f"Verification Passed: {res.verification_passed}")
        print(f"Tamper Detected:     {res.tamper_detected}")
        print(f"Details:             {res.details}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

