"""
Export labeled feedback data to YOLO format and run YOLOv8 fine-tuning.

Usage (from repo root):
    python ml/training/train_yolo.py --model-type mechanical --epochs 50

The script:
  1. Pulls verified Symbol corrections from the DB (is_training_candidate=True)
  2. Renders the drawing page to an image
  3. Writes YOLO label files (class_id cx cy w h, normalized)
  4. Calls `yolo train` with the generated dataset
  5. Copies the best.pt to ml_models/<model_type>/current.pt
"""
import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


CLASS_NAMES = {
    "mechanical": [
        "ahu", "fcu", "vav_box", "diffuser_supply", "diffuser_return",
        "grille", "exhaust_fan", "inline_fan", "pump", "boiler",
        "chiller", "cooling_tower", "heat_exchanger", "vrf_indoor",
        "vrf_outdoor", "split_system", "thermostat", "damper_manual",
        "damper_motorized", "fire_damper", "smoke_damper", "valve_gate",
        "valve_ball", "valve_butterfly", "valve_check", "valve_balancing",
        "coil_heating", "coil_cooling", "filter", "humidifier",
        "expansion_tank", "air_separator", "pressure_gauge", "temperature_sensor",
    ],
    "electrical": [
        "panel_board", "disconnect", "junction_box", "outlet_120v",
        "outlet_208v", "light_fixture", "exit_sign", "emergency_light",
        "transformer", "vfd", "motor", "starter",
    ],
    "plumbing": [
        "sink", "toilet", "urinal", "floor_drain", "cleanout",
        "backflow_preventer", "water_heater", "hose_bib",
    ],
}


async def export_dataset(model_type: str, out_dir: Path) -> int:
    """Export verified feedback as YOLO label files. Returns number of images."""
    from core.database import AsyncSessionLocal
    from models.learning import FeedbackEvent
    from models.drawing import Symbol, DrawingPage, Drawing
    from core.storage import download_file
    from sqlalchemy import select
    import fitz
    import numpy as np
    import cv2

    classes = CLASS_NAMES.get(model_type, CLASS_NAMES["mechanical"])
    class_index = {name: i for i, name in enumerate(classes)}

    for split in ("train", "val"):
        (out_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    images_dir = out_dir / "images" / "train"
    labels_dir = out_dir / "labels" / "train"

    exported = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FeedbackEvent).where(
                FeedbackEvent.event_type == "symbol_correction",
                FeedbackEvent.is_training_candidate.is_(True),
                FeedbackEvent.used_in_training_job_id.is_(None),
            )
        )
        events = result.scalars().all()

        # Group by drawing page
        page_events: dict[int, list] = {}
        for ev in events:
            sym_result = await db.execute(select(Symbol).where(Symbol.id == ev.entity_id))
            sym = sym_result.scalar_one_or_none()
            if not sym or sym.symbol_type not in class_index:
                continue
            page_events.setdefault(sym.page_id, []).append((sym, ev))

        for page_id, sym_ev_pairs in page_events.items():
            page_result = await db.execute(select(DrawingPage).where(DrawingPage.id == page_id))
            page = page_result.scalar_one_or_none()
            if not page:
                continue

            drawing_result = await db.execute(select(Drawing).where(Drawing.id == page.drawing_id))
            drawing = drawing_result.scalar_one_or_none()
            if not drawing:
                continue

            try:
                file_bytes = download_file(drawing.file_path)
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                pg = doc[page.page_number - 1]
                mat = fitz.Matrix(2, 2)
                pix = pg.get_pixmap(matrix=mat)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                doc.close()

                img_path = images_dir / f"page_{page_id}.jpg"
                cv2.imwrite(str(img_path), img)
                h_img, w_img = img.shape[:2]

                label_path = labels_dir / f"page_{page_id}.txt"
                lines = []
                scale = drawing.scale_factor or 96.0
                zoom = 2.0

                for sym, _ in sym_ev_pairs:
                    cls_id = class_index[sym.symbol_type]
                    # Convert feet → pixels (zoom=2, scale=px/ft)
                    cx_px = sym.x * scale * zoom
                    cy_px = sym.y * scale * zoom
                    w_px = (sym.width or 2.0) * scale * zoom
                    h_px = (sym.height or 2.0) * scale * zoom
                    # Normalize
                    cx_n = max(0.0, min(1.0, cx_px / w_img))
                    cy_n = max(0.0, min(1.0, cy_px / h_img))
                    w_n = max(0.01, min(1.0, w_px / w_img))
                    h_n = max(0.01, min(1.0, h_px / h_img))
                    lines.append(f"{cls_id} {cx_n:.6f} {cy_n:.6f} {w_n:.6f} {h_n:.6f}")

                label_path.write_text("\n".join(lines))
                exported += 1
            except Exception as e:
                log.warning("Skipping page %d: %s", page_id, e)

    return exported


def write_dataset_yaml(out_dir: Path, model_type: str) -> Path:
    """Write dataset.yaml with an 80/20 train/val split.

    Images are distributed into val/ from train/ so that validation metrics
    reflect held-out data rather than the training set.
    """
    import random

    train_imgs = list((out_dir / "images" / "train").glob("*.jpg"))
    if len(train_imgs) >= 5:
        # Hold out 20% (minimum 1) for validation
        n_val = max(1, len(train_imgs) // 5)
        random.shuffle(train_imgs)
        val_imgs = train_imgs[:n_val]
        for img_path in val_imgs:
            label_path = out_dir / "labels" / "train" / (img_path.stem + ".txt")
            img_path.rename(out_dir / "images" / "val" / img_path.name)
            if label_path.exists():
                label_path.rename(out_dir / "labels" / "val" / label_path.name)
        val_split = "images/val"
    else:
        # Too few images to split — reuse train to avoid empty val error
        val_split = "images/train"

    classes = CLASS_NAMES.get(model_type, CLASS_NAMES["mechanical"])
    cfg = {
        "path": str(out_dir),
        "train": "images/train",
        "val": val_split,
        "nc": len(classes),
        "names": classes,
    }
    yaml_path = out_dir / "dataset.yaml"
    yaml_path.write_text(yaml.dump(cfg))
    return yaml_path


def run_training(yaml_path: Path, model_type: str, epochs: int, output_dir: Path) -> Path | None:
    try:
        from ultralytics import YOLO

        base_model_path = output_dir / "current.pt"
        model_name = str(base_model_path) if base_model_path.exists() else "yolov8n.pt"
        model = YOLO(model_name)

        results = model.train(
            data=str(yaml_path),
            epochs=epochs,
            imgsz=640,
            batch=8,
            project=str(yaml_path.parent / "runs"),
            name=model_type,
            exist_ok=True,
            verbose=False,
        )

        best_pt = Path(results.save_dir) / "weights" / "best.pt"
        if best_pt.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(best_pt, output_dir / "current.pt")
            log.info("Saved new model to %s", output_dir / "current.pt")
            return output_dir / "current.pt"
    except Exception as e:
        log.error("Training failed: %s", e)
    return None


async def main(model_type: str, epochs: int):
    from core.config import settings

    models_path = Path(os.getenv("ML_MODELS_PATH", settings.ml_models_path))
    output_dir = models_path / model_type

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "dataset"
        log.info("Exporting training dataset for %s...", model_type)
        n = await export_dataset(model_type, out_dir)
        log.info("Exported %d images with labels", n)

        if n == 0:
            log.warning("No training data available. Collect symbol corrections first.")
            return

        yaml_path = write_dataset_yaml(out_dir, model_type)
        log.info("Starting YOLOv8 training: %d epochs", epochs)
        result = run_training(yaml_path, model_type, epochs, output_dir)

        if result:
            log.info("Training complete. Model saved to %s", result)
        else:
            log.error("Training did not produce a model.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-type", default="mechanical", choices=list(CLASS_NAMES))
    parser.add_argument("--epochs", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(main(args.model_type, args.epochs))
