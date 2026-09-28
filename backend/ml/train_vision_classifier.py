"""
Train PlantPathologyNet on the open-source PlantDoc dataset
(https://github.com/pratikkayal/PlantDoc-Dataset), with optional synthetic
fill for catalog classes that PlantDoc does not cover.

Usage:
  PYTHONPATH=. python scripts/download_plantdoc.py
  PYTHONPATH=. python backend/ml/train_vision_classifier.py
  PYTHONPATH=. python backend/ml/train_vision_classifier.py --synthetic-only
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional, Tuple

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import torch

torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))

import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, TensorDataset, WeightedRandomSampler
from PIL import Image
import torchvision.transforms as T

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.models.plant_disease_catalog import CLASS_NAMES, NUM_CLASSES
from backend.ml.vision_model_arch import PlantPathologyNet
from backend.ml.plantdoc_labels import resolve_plantdoc_folder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True,
)
logger = logging.getLogger("train_vision")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
DEFAULT_PLANTDOC = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "plantdoc"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def _train_transforms() -> T.Compose:
    return T.Compose([
        T.Resize((224, 224)),
        T.RandomHorizontalFlip(),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def _eval_transforms() -> T.Compose:
    return T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


class PlantDocImageDataset(Dataset):
    """Preloads resized tensors once so training never re-decodes JPEGs mid-epoch."""

    def __init__(self, samples: List[Tuple[Path, int]], train: bool = True):
        self.train = train
        self.labels = [y for _, y in samples]
        mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
        self.tensors: List[torch.Tensor] = []
        logger.info(f"Preloading {len(samples)} images into tensors...")
        for i, (path, _) in enumerate(samples):
            if i and i % 200 == 0:
                logger.info(f"  loaded {i}/{len(samples)}")
                sys.stdout.flush()
            try:
                with Image.open(path) as raw:
                    raw.load()
                    img = raw.convert("RGB")
                    img.thumbnail((224, 224), Image.BILINEAR)
                    # pad to exact 224x224
                    canvas = Image.new("RGB", (224, 224), (0, 0, 0))
                    ox = (224 - img.width) // 2
                    oy = (224 - img.height) // 2
                    canvas.paste(img, (ox, oy))
                    arr = np.asarray(canvas, dtype=np.float32) / 255.0
                    t = torch.from_numpy(arr).permute(2, 0, 1)
                    t = (t - mean) / std
            except Exception:
                t = torch.zeros(3, 224, 224)
            self.tensors.append(t)
        logger.info(f"Preload complete ({len(self.tensors)} tensors).")
        sys.stdout.flush()

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        x = self.tensors[idx]
        if self.train and torch.rand(1).item() < 0.5:
            x = torch.flip(x, dims=[2])
        return x, self.labels[idx]


def balance_samples(
    samples: List[Tuple[Path, int]], max_per_class: int
) -> List[Tuple[Path, int]]:
    """Cap images per class for faster CPU training."""
    if max_per_class <= 0:
        return samples
    rng = np.random.default_rng(42)
    by_class: dict[int, List[Tuple[Path, int]]] = {}
    for s in samples:
        by_class.setdefault(s[1], []).append(s)
    out: List[Tuple[Path, int]] = []
    for label, items in sorted(by_class.items()):
        if len(items) > max_per_class:
            idx = rng.choice(len(items), size=max_per_class, replace=False)
            items = [items[i] for i in idx]
        out.extend(items)
    logger.info(
        f"Balanced to {len(out)} images (max {max_per_class}/class across {len(by_class)} classes)"
    )
    return out


def collect_plantdoc_samples(root: Path, split: str) -> List[Tuple[Path, int]]:
    split_dir = root / split
    if not split_dir.is_dir():
        raise FileNotFoundError(f"Missing PlantDoc split directory: {split_dir}")

    class_to_idx = {name: i for i, name in enumerate(CLASS_NAMES)}
    samples: List[Tuple[Path, int]] = []
    skipped_folders = []
    mapped_counts = {}

    for folder in sorted(p for p in split_dir.iterdir() if p.is_dir()):
        catalog_key = resolve_plantdoc_folder(folder.name)
        if catalog_key is None:
            skipped_folders.append(folder.name)
            continue
        if catalog_key not in class_to_idx:
            skipped_folders.append(f"{folder.name}→{catalog_key} (not in catalog)")
            continue
        label = class_to_idx[catalog_key]
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        for fp in files:
            samples.append((fp, label))
        mapped_counts[catalog_key] = mapped_counts.get(catalog_key, 0) + len(files)

    if skipped_folders:
        logger.warning(f"Unmapped PlantDoc folders in {split}: {skipped_folders}")
    logger.info(
        f"PlantDoc {split}: {len(samples)} images across {len(mapped_counts)} catalog classes"
    )
    for k, n in sorted(mapped_counts.items(), key=lambda x: -x[1])[:12]:
        logger.info(f"  {k}: {n}")
    return samples


def generate_vectorized_dataset(num_samples: int = 570, num_classes: int = NUM_CLASSES):
    """Synthetic fallback for catalog classes without PlantDoc photos."""
    samples_per_class = max(1, num_samples // num_classes)
    total_samples = samples_per_class * num_classes

    class_signatures = {
        "tomato_early_blight": (0.28, 0.52, 0.22, 1, 0.8),
        "tomato_late_blight": (0.25, 0.45, 0.20, 4, 0.9),
        "tomato_septoria_leaf_spot": (0.30, 0.55, 0.25, 4, 0.7),
        "tomato_powdery_mildew": (0.35, 0.60, 0.30, 2, 0.85),
        "tomato_bacterial_spot": (0.30, 0.50, 0.22, 4, 0.6),
        "tomato_spider_mites": (0.40, 0.58, 0.28, 5, 0.75),
        "tomato_healthy": (0.20, 0.68, 0.24, 0, 0.0),
        "tomato_leaf_mold": (0.32, 0.55, 0.28, 2, 0.7),
        "tomato_mosaic_virus": (0.34, 0.58, 0.24, 5, 0.55),
        "tomato_yellow_leaf_curl": (0.42, 0.55, 0.20, 0, 0.0),
        "pepper_bacterial_spot": (0.26, 0.52, 0.20, 4, 0.65),
        "pepper_healthy": (0.18, 0.72, 0.22, 0, 0.0),
        "squash_powdery_mildew": (0.32, 0.58, 0.28, 2, 0.9),
        "apple_scab": (0.24, 0.54, 0.20, 4, 0.8),
        "apple_cedar_rust": (0.38, 0.50, 0.18, 3, 0.85),
        "apple_healthy": (0.20, 0.65, 0.22, 0, 0.0),
        "grape_black_rot": (0.25, 0.48, 0.20, 4, 0.85),
        "grape_healthy": (0.22, 0.66, 0.25, 0, 0.0),
        "strawberry_leaf_scorch": (0.35, 0.46, 0.22, 4, 0.8),
        "strawberry_healthy": (0.20, 0.68, 0.24, 0, 0.0),
        "potato_early_blight": (0.27, 0.50, 0.20, 1, 0.8),
        "potato_late_blight": (0.24, 0.42, 0.18, 4, 0.95),
        "potato_healthy": (0.19, 0.67, 0.21, 0, 0.0),
        "corn_gray_leaf_spot": (0.30, 0.52, 0.22, 4, 0.7),
        "corn_leaf_blight": (0.28, 0.50, 0.20, 1, 0.75),
        "corn_common_rust": (0.45, 0.40, 0.22, 3, 0.8),
        "blueberry_healthy": (0.18, 0.62, 0.28, 0, 0.0),
        "cherry_healthy": (0.20, 0.64, 0.24, 0, 0.0),
        "peach_healthy": (0.22, 0.66, 0.23, 0, 0.0),
        "raspberry_healthy": (0.21, 0.65, 0.25, 0, 0.0),
        "soybean_healthy": (0.19, 0.66, 0.22, 0, 0.0),
    }

    all_x = np.zeros((total_samples, 3, 224, 224), dtype=np.float32)
    all_y = np.zeros(total_samples, dtype=np.int64)
    y_grid, x_grid = np.ogrid[:224, :224]

    idx = 0
    for c_idx, class_name in enumerate(CLASS_NAMES):
        sig = class_signatures.get(class_name, (0.25, 0.60, 0.25, 0, 0.0))
        r_base, g_base, b_base, spot_type, spot_int = sig

        for _ in range(samples_per_class):
            noise = np.random.normal(0, 0.03, (3, 224, 224)).astype(np.float32)
            gradient = (np.sin(x_grid / 20.0) * np.cos(y_grid / 20.0) * 0.04).astype(np.float32)
            all_x[idx, 0] = np.clip(r_base + noise[0] + gradient, 0.0, 1.0)
            all_x[idx, 1] = np.clip(g_base + noise[1] + gradient, 0.0, 1.0)
            all_x[idx, 2] = np.clip(b_base + noise[2] + gradient, 0.0, 1.0)

            if spot_type == 1:
                for _ in range(np.random.randint(2, 4)):
                    cx, cy = np.random.randint(50, 170), np.random.randint(50, 170)
                    dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
                    mask = (dist < 25) & ((np.sin(dist / 3.0) > 0.2) | (dist < 6))
                    all_x[idx, 0, mask] = np.clip(all_x[idx, 0, mask] + 0.35 * spot_int, 0.0, 1.0)
                    all_x[idx, 1, mask] = np.clip(all_x[idx, 1, mask] - 0.25 * spot_int, 0.0, 1.0)
                    all_x[idx, 2, mask] = np.clip(all_x[idx, 2, mask] - 0.15 * spot_int, 0.0, 1.0)
            elif spot_type == 2:
                dust = (np.sin(x_grid / 12.0) + np.cos(y_grid / 12.0) > 0.4) & (
                    np.random.rand(224, 224) > 0.35
                )
                all_x[idx, 0, dust] = np.clip(all_x[idx, 0, dust] + 0.4 * spot_int, 0.0, 1.0)
                all_x[idx, 1, dust] = np.clip(all_x[idx, 1, dust] + 0.35 * spot_int, 0.0, 1.0)
                all_x[idx, 2, dust] = np.clip(all_x[idx, 2, dust] + 0.4 * spot_int, 0.0, 1.0)
            elif spot_type == 3:
                for _ in range(np.random.randint(3, 6)):
                    cx, cy = np.random.randint(40, 180), np.random.randint(40, 180)
                    dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
                    mask = dist < 14
                    all_x[idx, 0, mask] = 0.88
                    all_x[idx, 1, mask] = 0.48
                    all_x[idx, 2, mask] = 0.12
            elif spot_type == 4:
                for _ in range(np.random.randint(4, 9)):
                    cx, cy = np.random.randint(30, 190), np.random.randint(30, 190)
                    dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
                    mask = dist < np.random.randint(6, 15)
                    all_x[idx, 0, mask] = 0.18
                    all_x[idx, 1, mask] = 0.14
                    all_x[idx, 2, mask] = 0.08
            elif spot_type == 5:
                stipple = np.random.rand(224, 224) > 0.85
                all_x[idx, 0, stipple] = np.clip(all_x[idx, 0, stipple] + 0.35, 0.0, 1.0)
                all_x[idx, 1, stipple] = np.clip(all_x[idx, 1, stipple] + 0.30, 0.0, 1.0)
                all_x[idx, 2, stipple] = np.clip(all_x[idx, 2, stipple] + 0.10, 0.0, 1.0)

            all_y[idx] = c_idx
            idx += 1

    mean = np.array(IMAGENET_MEAN, dtype=np.float32).reshape(1, 3, 1, 1)
    std = np.array(IMAGENET_STD, dtype=np.float32).reshape(1, 3, 1, 1)
    all_x = (all_x - mean) / std
    return torch.from_numpy(all_x).float(), torch.from_numpy(all_y).long()


def _make_weighted_sampler(labels: List[int]) -> WeightedRandomSampler:
    counts = np.bincount(np.array(labels), minlength=NUM_CLASSES).astype(np.float64)
    counts[counts == 0] = 1.0
    class_w = 1.0 / counts
    sample_w = [class_w[y] for y in labels]
    return WeightedRandomSampler(sample_w, num_samples=len(sample_w), replacement=True)


def train_and_save_model(
    output_dir: str = "backend/ml/weights",
    epochs: int = 8,
    batch_size: int = 32,
    plantdoc_root: Optional[Path] = None,
    synthetic_only: bool = False,
    synthetic_fill_per_missing: int = 24,
    lr: float = 3e-4,
):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    weight_path = Path(output_dir) / "plant_disease_model.pt"
    plantdoc_root = Path(plantdoc_root) if plantdoc_root else DEFAULT_PLANTDOC

    if synthetic_only or not (plantdoc_root / "train").is_dir():
        if not synthetic_only:
            logger.warning(
                f"PlantDoc not found at {plantdoc_root}. "
                "Run: PYTHONPATH=. python scripts/download_plantdoc.py"
            )
            logger.warning("Falling back to synthetic-only training.")
        logger.info(f"Generating synthetic training data ({NUM_CLASSES} classes)...")
        train_x, train_y = generate_vectorized_dataset(num_samples=max(570, NUM_CLASSES * 30))
        val_x, val_y = generate_vectorized_dataset(num_samples=max(190, NUM_CLASSES * 10))
        train_loader = DataLoader(TensorDataset(train_x, train_y), batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(TensorDataset(val_x, val_y), batch_size=batch_size, shuffle=False)
        data_source = "synthetic"
    else:
        train_samples = collect_plantdoc_samples(plantdoc_root, "train")
        val_samples = collect_plantdoc_samples(plantdoc_root, "test")
        if not train_samples:
            raise RuntimeError("No PlantDoc train samples mapped to the disease catalog.")

        present = {y for _, y in train_samples}
        missing = [i for i in range(NUM_CLASSES) if i not in present]
        from torch.utils.data import ConcatDataset

        class _TensorPairDataset(Dataset):
            def __init__(self, x, y):
                self.x, self.y = x, y

            def __len__(self):
                return len(self.y)

            def __getitem__(self, i):
                return self.x[i], int(self.y[i])

        train_img_ds = PlantDocImageDataset(train_samples, train=True)
        if missing and synthetic_fill_per_missing > 0:
            logger.info(
                f"Synthetic fill for {len(missing)} catalog classes without PlantDoc images "
                f"({synthetic_fill_per_missing} each)..."
            )
            sx, sy = generate_vectorized_dataset(
                num_samples=NUM_CLASSES * synthetic_fill_per_missing,
                num_classes=NUM_CLASSES,
            )
            keep = torch.zeros(len(sy), dtype=torch.bool)
            for mi in missing:
                keep |= sy == mi
            sx, sy = sx[keep], sy[keep]
            train_ds = ConcatDataset([train_img_ds, _TensorPairDataset(sx, sy)])
            train_labels = list(train_img_ds.labels) + [int(v) for v in sy.tolist()]
        else:
            train_ds = train_img_ds
            train_labels = list(train_img_ds.labels)

        val_ds = PlantDocImageDataset(val_samples, train=False)
        sampler = _make_weighted_sampler(train_labels)
        train_loader = DataLoader(
            train_ds,
            batch_size=batch_size,
            sampler=sampler,
            num_workers=0,
            drop_last=len(train_ds) >= batch_size,
        )
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
        data_source = f"plantdoc@{plantdoc_root}"

    device = torch.device("cpu")
    logger.info(
        f"Training PlantPathologyNet/MobileNetV2 ({NUM_CLASSES} classes) on {device} using {data_source}..."
    )
    model = PlantPathologyNet(num_classes=NUM_CLASSES, pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(epochs, 1))

    start_time = time.time()
    best_acc = -1.0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        epoch_t0 = time.time()
        n_batches = len(train_loader)

        for bi, (batch_x, batch_y) in enumerate(train_loader, start=1):
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * batch_x.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == batch_y).sum().item()
            total += batch_y.size(0)
            if bi == 1 or bi % 20 == 0 or bi == n_batches:
                logger.info(f"  epoch {epoch} batch {bi}/{n_batches}")
                sys.stdout.flush()

        train_acc = correct / max(total, 1)
        scheduler.step()

        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for vx, vy in val_loader:
                vx = vx.to(device)
                vy = vy.to(device)
                v_out = model(vx)
                _, v_preds = torch.max(v_out, 1)
                val_correct += (v_preds == vy).sum().item()
                val_total += vy.size(0)

        val_acc = val_correct / max(val_total, 1)
        logger.info(
            f"Epoch {epoch:2d}/{epochs} - Loss: {running_loss / max(total, 1):.4f} - "
            f"Train Acc: {train_acc * 100:.1f}% - Val Acc: {val_acc * 100:.1f}% "
            f"({time.time() - epoch_t0:.0f}s)"
        )
        sys.stdout.flush()

        if val_acc >= best_acc or epoch == epochs:
            best_acc = max(best_acc, val_acc)
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "class_names": CLASS_NAMES,
                    "num_classes": NUM_CLASSES,
                    "val_accuracy": val_acc,
                    "data_source": data_source,
                    "dataset": "PlantDoc" if "plantdoc" in data_source else "synthetic",
                    "backbone": "mobilenet_v2",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                weight_path,
            )
            logger.info(f"Saved checkpoint → {weight_path} (val={val_acc * 100:.1f}%)")
            sys.stdout.flush()

    elapsed = time.time() - start_time
    logger.info(f"Training completed in {elapsed:.1f}s. Best Val Acc: {best_acc * 100:.1f}%")
    logger.info(f"Saved weights → {weight_path}")
    return weight_path


def main():
    parser = argparse.ArgumentParser(description="Train PlantPathologyNet on PlantDoc")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--plantdoc-root", type=Path, default=DEFAULT_PLANTDOC)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--synthetic-fill", type=int, default=24)
    parser.add_argument("--output-dir", type=str, default="backend/ml/weights")
    args = parser.parse_args()
    train_and_save_model(
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        plantdoc_root=args.plantdoc_root,
        synthetic_only=args.synthetic_only,
        synthetic_fill_per_missing=args.synthetic_fill,
        lr=args.lr,
    )


if __name__ == "__main__":
    main()
