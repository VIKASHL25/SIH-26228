import os
import sys
import argparse
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.data.ingester import DatasetIngester
from cv_assurance.data.visdrone import VisDroneBenchmarkSynthesizer, VisDroneIngester
from cv_assurance.attacks.pipeline import MultiContributorPipeline
from cv_assurance.attacks.manifest import ManifestValidator

def generate_benchmark_attacks(
    reference_dataset_path: str = None,
    output_dir: str = "data",
    num_samples: int = 60,
    seed: int = 42
):
    print("=" * 70)
    print("      MODULE 1: REPRODUCIBLE MULTI-CONTRIBUTOR ATTACK GENERATION")
    print("=" * 70)
    print(f"[*] Target Directory:   {output_dir}")
    print(f"[*] Random Seed:        {seed}")
    print(f"[*] Sample Count:       {num_samples}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Ingest or synthesize reference dataset
    if reference_dataset_path and os.path.exists(reference_dataset_path):
        print(f"[*] Ingesting reference dataset from: {reference_dataset_path}")
        ref_ds = DatasetIngester.auto_ingest(reference_dataset_path)
    else:
        print(f"[*] Generating VisDrone baseline reference dataset ({num_samples} samples)...")
        temp_dir = out_path / ".temp_ref"
        paths = VisDroneBenchmarkSynthesizer.generate_synthetic_visdrone_dataset(
            output_dir=str(temp_dir),
            num_train=num_samples,
            num_val=15,
            seed=seed
        )
        ref_ds = VisDroneIngester.ingest_visdrone(paths["train_root"], max_samples=num_samples, seed=seed)

    print(f"[+] Loaded clean reference dataset with {len(ref_ds.samples)} samples.")

    # Execute Multi-Contributor Pipeline
    print("\n[*] Partitioning pipeline into Contributors A, B, C, D and applying controlled attacks...")
    pipeline = MultiContributorPipeline(output_dir=str(out_path), seed=seed)
    manifest = pipeline.build_benchmark(ref_ds)

    print("\n[+] Attack generation completed successfully.")
    print("-" * 70)
    print(f"Total Benchmark Samples:      {manifest.total_samples}")
    print("Attack Summary Breakdown:")
    for atk, cnt in manifest.attack_summary.items():
        print(f"  - {atk:<30}: {cnt:>4} samples")
    print("\nContributor Distribution:")
    for cid, cnt in manifest.contributor_summary.items():
        print(f"  - {cid:<30}: {cnt:>4} samples")

    # Validate generated manifest
    print("\n[*] Validating Ground-Truth Manifest Schema & Integrity...")
    is_valid, errors = ManifestValidator.validate(manifest, base_dir=out_path)
    if is_valid:
        print("[+] Manifest Validation PASSED (100% compliant with Module 1 schema).")
    else:
        print(f"[!] Validation Warnings/Errors: {errors}")

    print("\n[+] Benchmark output artifacts saved to:")
    print(f"  - Clean Reference:     {output_dir}/reference/manifest.json")
    print(f"  - Contributors Data:   {output_dir}/contributors/ (A, B, C, D)")
    print(f"  - Isolated Attacks:    {output_dir}/attacks/")
    print(f"  - Operational Shifts:  {output_dir}/distribution_shift/")
    print(f"  - Master Ground Truth: {output_dir}/ground_truth/attack_manifest.json")
    print(f"  - Direct Dataset Entry:{output_dir}/dataset_manifest.json")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Generate reproducible multi-contributor attack benchmark (Module 1)")
    parser.add_argument("--reference-dataset", default=None, help="Path to clean reference dataset (COCO json or VisDrone folder)")
    parser.add_argument("--output-dir", default="data", help="Output directory for generated benchmark")
    parser.add_argument("--num-samples", type=int, default=60, help="Number of baseline samples to synthesize if generating from scratch")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    args = parser.parse_args()

    generate_benchmark_attacks(
        reference_dataset_path=args.reference_dataset,
        output_dir=args.output_dir,
        num_samples=args.num_samples,
        seed=args.seed
    )

if __name__ == "__main__":
    main()
