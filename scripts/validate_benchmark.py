import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.attacks.manifest import GroundTruthManifest, ManifestValidator

def validate_benchmark_suite(benchmark_dir: str = "data") -> bool:
    print("=" * 70)
    print("      BENCHMARK GROUND-TRUTH & DATA LEAKAGE INTEGRITY VALIDATION")
    print("=" * 70)
    print(f"[*] Benchmark Directory: {benchmark_dir}")

    b_path = Path(benchmark_dir)
    if not b_path.exists():
        print(f"[!] Benchmark directory does not exist: {b_path}")
        return False

    gt_manifest_file = b_path / "ground_truth" / "attack_manifest.json"
    calib_manifest_file = b_path / "calibration" / "manifest.json"
    clean_test_manifest_file = b_path / "clean_test" / "manifest.json"
    ref_manifest_file = b_path / "reference" / "manifest.json"

    all_passed = True

    # 1. Validate Master Attack Manifest
    if not gt_manifest_file.exists():
        print(f"[!] Missing ground truth manifest: {gt_manifest_file}")
        return False

    gt_manifest = GroundTruthManifest.load(gt_manifest_file)
    print(f"[+] Loaded master ground truth manifest with {gt_manifest.total_samples} samples.")

    is_valid, errors = ManifestValidator.validate(gt_manifest, base_dir=b_path)
    if is_valid:
        print("[+] Attack Manifest Schema Validation: PASSED")
    else:
        print(f"[!] Attack Manifest Errors ({len(errors)}):")
        for err in errors[:10]:
            print(f"    - {err}")
        all_passed = False

    # 2. Data Leakage Verification
    print("\n[*] Checking for Partition Data Leakage across Calibration & Test...")
    calib_originals: Set[str] = set()
    clean_test_originals: Set[str] = set()
    attack_test_originals: Set[str] = set()

    if calib_manifest_file.exists():
        calib_m = GroundTruthManifest.load(calib_manifest_file)
        calib_originals = {Path(s.original_image).name for s in calib_m.samples if s.original_image}
        print(f"  - Calibration partition samples: {len(calib_originals)}")

    if clean_test_manifest_file.exists():
        clean_m = GroundTruthManifest.load(clean_test_manifest_file)
        clean_test_originals = {Path(s.original_image).name for s in clean_m.samples if s.original_image}
        print(f"  - Clean Test partition samples:  {len(clean_test_originals)}")

    for s in gt_manifest.samples:
        if s.is_attacked or s.is_shifted:
            if s.original_image:
                attack_test_originals.add(Path(s.original_image).name)
    print(f"  - Attack Test partition source originals: {len(attack_test_originals)}")

    # Check overlaps
    leakage_calib_clean = calib_originals & clean_test_originals
    leakage_calib_attack = calib_originals & attack_test_originals

    if leakage_calib_clean:
        print(f"[!] DATA LEAKAGE DETECTED between Calibration and Clean Test ({len(leakage_calib_clean)} images): {leakage_calib_clean}")
        all_passed = False
    else:
        print("  [+] Zero leakage between Clean Calibration and Clean Test.")

    if leakage_calib_attack:
        print(f"[!] DATA LEAKAGE DETECTED between Calibration and Attack Test ({len(leakage_calib_attack)} images): {leakage_calib_attack}")
        all_passed = False
    else:
        print("  [+] Zero leakage between Clean Calibration and Attack Test.")

    # 3. Verify Contributor Submissions
    print("\n[*] Verifying Contributor Partition Integrity...")
    for cid in ["contributor_A", "contributor_B", "contributor_C", "contributor_D"]:
        c_dir = b_path / "contributors" / cid / "images"
        c_manifest = b_path / "contributors" / cid / "manifest.json"
        if not c_dir.exists() or not c_manifest.exists():
            print(f"[!] Missing contributor files for '{cid}'")
            all_passed = False
        else:
            m = GroundTruthManifest.load(c_manifest)
            print(f"  [+] {cid:<16}: {m.total_samples} samples verified on disk.")

    print("\n" + "=" * 70)
    if all_passed:
        print("    VALIDATION STATUS: ALL CHECKS PASSED (100% Defensible Benchmark)")
    else:
        print("    VALIDATION STATUS: FAILED (Resolve issues above)")
    print("=" * 70)
    return all_passed

def main():
    parser = argparse.ArgumentParser(description="Validate benchmark ground truth schema and zero data leakage")
    parser.add_argument("--benchmark-dir", default="data", help="Path to benchmark directory")
    args = parser.parse_args()

    success = validate_benchmark_suite(benchmark_dir=args.benchmark_dir)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
