#!/usr/bin/env python3
"""
Download the open-source PlantDoc classification dataset.

Source: https://github.com/pratikkayal/PlantDoc-Dataset
Citation: Singh et al., "PlantDoc: A Dataset for Visual Plant Disease Detection", CoDS-COMAD 2020.

Usage:
  PYTHONPATH=. python scripts/download_plantdoc.py
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/pratikkayal/PlantDoc-Dataset.git"
DEFAULT_DEST = Path(__file__).resolve().parent.parent / "data" / "raw" / "plantdoc"


def download_plantdoc(dest: Path, force: bool = False) -> Path:
    dest = dest.resolve()
    train_dir = dest / "train"
    test_dir = dest / "test"

    if train_dir.is_dir() and test_dir.is_dir() and not force:
        n_train = sum(1 for _ in train_dir.rglob("*") if _.is_file())
        n_test = sum(1 for _ in test_dir.rglob("*") if _.is_file())
        print(f"PlantDoc already present at {dest} ({n_train} train / {n_test} test files).")
        return dest

    if dest.exists() and force:
        print(f"Removing existing dataset at {dest}")
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_clone = dest.parent / "_plantdoc_clone_tmp"
    if tmp_clone.exists():
        shutil.rmtree(tmp_clone)

    print(f"Cloning {REPO_URL} (shallow)...")
    subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, str(tmp_clone)],
        check=True,
    )

    # Upstream layout is either repo root with train/test, or nested PlantDoc-Dataset/
    candidates = [
        tmp_clone,
        tmp_clone / "PlantDoc-Dataset",
        tmp_clone / "train",
    ]
    source_root = None
    for cand in candidates:
        if (cand / "train").is_dir() and (cand / "test").is_dir():
            source_root = cand
            break
        if cand.name == "train" and cand.is_dir():
            # train accidentally selected — parent should hold both
            if (cand.parent / "test").is_dir():
                source_root = cand.parent
                break

    if source_root is None:
        shutil.rmtree(tmp_clone, ignore_errors=True)
        raise RuntimeError(
            "Could not locate train/ and test/ folders in the cloned PlantDoc repo."
        )

    dest.mkdir(parents=True, exist_ok=True)
    for split in ("train", "test"):
        src = source_root / split
        dst = dest / split
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    # Keep a small attribution file
    (dest / "SOURCE.txt").write_text(
        "PlantDoc Dataset\n"
        f"Upstream: {REPO_URL}\n"
        "Paper: PlantDoc: A Dataset for Visual Plant Disease Detection (CoDS-COMAD 2020)\n",
        encoding="utf-8",
    )

    shutil.rmtree(tmp_clone, ignore_errors=True)

    n_train = sum(1 for p in (dest / "train").rglob("*") if p.is_file())
    n_test = sum(1 for p in (dest / "test").rglob("*") if p.is_file())
    print(f"PlantDoc ready at {dest}")
    print(f"  train images/files: {n_train}")
    print(f"  test images/files:  {n_test}")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Download PlantDoc dataset")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()
    try:
        download_plantdoc(args.dest, force=args.force)
    except subprocess.CalledProcessError as e:
        print(f"git clone failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
