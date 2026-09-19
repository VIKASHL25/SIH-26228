import os
import sys
import argparse
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cv_assurance.data.visdrone import VisDroneIngester, VisDroneBenchmarkSynthesizer

def prepare_visdrone(
    source_dir: str = None,
    output_dir: str = "demo_assets/visdrone_raw",
    num_train: int = 100,
    num_val: int = 25,
    seed: int = 42
):
    out_path = Path(output_dir)
    print(f"[*] Preparing VisDrone Dataset in: {out_path}")
    
    if source_dir and os.path.exists(source_dir):
        print(f"[*] Ingesting official VisDrone source dataset from: {source_dir}")
        ds = VisDroneIngester.ingest_visdrone(source_dir, max_samples=num_train, seed=seed)
        out_json = out_path / "visdrone_coco.json"
        VisDroneIngester.export_to_coco(ds, str(out_json))
        print(f"[+] Successfully extracted {len(ds.samples)} samples from real VisDrone dataset.")
        return str(out_json)
    else:
        print(f"[*] Official VisDrone local archive not found. Generating high-fidelity VisDrone-format benchmark for offline assurance...")
        paths = VisDroneBenchmarkSynthesizer.generate_synthetic_visdrone_dataset(
            output_dir=str(out_path),
            num_train=num_train,
            num_val=num_val,
            seed=seed
        )
        print(f"[+] Generated {num_train} train and {num_val} val VisDrone-compliant aerial samples in {out_path}")
        return paths["train_root"]

def main():
    parser = argparse.ArgumentParser(description="Prepare or synthesize VisDrone dataset for Computer Vision Assurance")
    parser.add_argument("--source-dir", default=None, help="Path to raw uncompressed VisDrone directory if downloaded")
    parser.add_argument("--output-dir", default="demo_assets/visdrone_raw", help="Target output directory")
    parser.add_argument("--num-train", type=int, default=100, help="Number of train/reference samples")
    parser.add_argument("--num-val", type=int, default=25, help="Number of validation samples")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    args = parser.parse_args()

    prepare_visdrone(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        num_train=args.num_train,
        num_val=args.num_val,
        seed=args.seed
    )

if __name__ == "__main__":
    main()
