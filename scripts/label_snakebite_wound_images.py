#!/usr/bin/env python3
"""
Snakebite wound images → labels per ``rubric.json`` (v2.0): 6 CLIP classes + ``unknown/`` fallback.

CLIP classes: ``not_snakebite``, ``neurotoxic``, ``hemotoxic``, ``cytotoxic``, ``myotoxic``, ``non_venomous``.
``unknown/`` is used when quality fails, CLIP is ambiguous, or rubric tie-breaks demand it (see rubric).

Rubric-aligned behavior (automated approximations):
- Per-class minimum softmax confidence for folder assignment (not_snakebite 0.85; most venom 0.75;
  neurotoxic 0.60–0.70 cap; myotoxic 0.65 cap).
- Necrosis heuristic can override toward cytotoxic (necrosis overrides other venom classes).
- Optional hybrid tooth-row score when CLIP says hemotoxic/neurotoxic → ``non_venomous`` (arc pattern).

Clinical / expert review is still required for deployment.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from collections import Counter

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from snakebite_morphology import morphology_bite_pattern, necrosis_dark_fraction

import numpy as np
from PIL import Image

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
except ImportError as e:
    print("Missing deps. Install: pip install torch transformers pillow", file=sys.stderr)
    raise SystemExit(1) from e

# Subfolders we scan when there are no loose files in ``image-dir`` root.
# ``unclear`` kept for older layouts migrating to rubric ``unknown/``.
ALL_SUBDIRS = (
    "not_snakebite",
    "neurotoxic",
    "hemotoxic",
    "cytotoxic",
    "myotoxic",
    "non_venomous",
    "unknown",
    "unclear",
)

CLASS_PROMPTS_ENSEMBLE: dict[str, tuple[str, str, str]] = {
    "not_snakebite": (
        "a clinical photograph of a skin injury that is clearly not a snake bite: linear cut, slash, or laceration without paired puncture marks",
        "burn mark, thermal injury, insect sting, or bite pattern that is not from snake fangs",
        "surgical wound, abscess, blunt trauma bruise, or skin infection without snake bite puncture pattern",
    ),
    "neurotoxic": (
        "a clinical close-up photograph of a snakebite showing minimal or no local swelling, "
        "small clean puncture marks, no bleeding or bruising, relatively normal surrounding skin",
        "snakebite wound with tiny paired fang marks, little edema, no ecchymosis, surrounding skin looks normal",
        "elapid-type bite appearance: mild local reaction, two small punctures, no hemorrhagic discoloration",
    ),
    "hemotoxic": (
        "a clinical close-up photograph of a snakebite with visible bleeding at the bite site, "
        "bruising or dark discoloration, swelling with hemorrhagic appearance",
        "viper-type snakebite with oozing blood, purple ecchymosis, and swollen hemorrhagic tissue",
        "hemorrhagic snake envenomation: dark bruising, bleeding from punctures, tense swollen limb",
    ),
    "cytotoxic": (
        "a clinical close-up photograph of a snakebite with tissue necrosis or blackening, "
        "blistering or bullae, severe local tissue destruction, ulceration or open wound",
        "necrotic snakebite with black eschar, fluid-filled bullae, or deep ulceration",
        "severe local snakebite injury with sloughing skin, blistering, and tissue breakdown",
    ),
    "myotoxic": (
        "a clinical close-up photograph of a snakebite with deep diffuse swelling, "
        "large muscle area involvement, without clear necrosis or active bleeding",
        "snakebite causing pronounced limb or muscle swelling, tight shiny skin, without frank necrosis",
        "profound regional edema from snakebite over muscle bulk, limited bleeding",
    ),
    "non_venomous": (
        "a clinical photograph of superficial snake teeth marks only, no significant swelling, "
        "clean minor punctures, no progressive tissue reaction",
        "dry bite or minimal envenomation: shallow tooth marks, almost no swelling",
        "minor snake bite without strong inflammatory or hemorrhagic response",
    ),
}

RUBRIC_CLIP_CLASSES = tuple(CLASS_PROMPTS_ENSEMBLE.keys())
UNKNOWN_FOLDER = "unknown"

# Strict CSV: rubric global 0.75 for most classes; neuro/myotoxic use class-specific thresholds below
TOP2_GAP_STRICT = 0.04

# Image quality → unknown (rubric: blurry / too dark / wound not assessable)
BLUR_VAR_THRESHOLD = 22.0
MEAN_LUMINANCE_DARK = 42.0

# Folder assignment: decisive margin; per-class min confidence in ``min_conf_for_rubric_folder``
MIN_FOLDER_MARGIN = 0.12
# 6-way CLIP; keep similar strictness as former 5-class run
MAX_SOFTMAX_ENTROPY = 1.28

# Rubric: minimum_confidence_to_label 0.75 (class-specific overrides for neuro/myotoxic in code)
MIN_FOLDER_CONFIDENCE_DEFAULT = 0.75

# Rubric class minima (folder assignment)
MIN_CONF_NOT_SNAKEBITE = 0.85
MIN_CONF_CYTO = 0.75
MIN_CONF_HEMO = 0.75
MIN_CONF_NEURO = 0.60
MAX_CONF_NEURO = 0.70  # rubric: wound cannot confirm neurotoxic syndrome
MIN_CONF_MYOTOXIC = 0.65
MAX_CONF_MYOTOXIC = 0.65
MIN_CONF_NONV = 0.75

# Rubric: necrosis visible → cytotoxic overrides other venom classes (heuristic)
NECROSIS_OVERRIDE_CYTOTOXIC = 0.14

# Rubric: hemotoxic needs bleeding — very low red-fraction → unknown
HEMOTOXIC_MIN_SCATTER_BLOOD = 0.006

HUMAN_REASON = {
    "not_snakebite": "injury pattern does not match snake bite per ensemble match",
    "neurotoxic": "clean puncture, minimal local reaction per ensemble match (syndrome not visible)",
    "hemotoxic": "bleeding/bruising or hemorrhagic swelling pattern per ensemble match",
    "cytotoxic": "necrosis, blistering, or severe local destruction pattern per ensemble match",
    "myotoxic": "diffuse swelling/muscle-region involvement per ensemble match (limited reliability)",
    "non_venomous": "superficial teeth marks without strong envenomation signs per ensemble match",
}


def min_conf_for_rubric_folder(cls: str) -> float:
    return {
        "not_snakebite": MIN_CONF_NOT_SNAKEBITE,
        "cytotoxic": MIN_CONF_CYTO,
        "hemotoxic": MIN_CONF_HEMO,
        "neurotoxic": MIN_CONF_NEURO,
        "myotoxic": MIN_CONF_MYOTOXIC,
        "non_venomous": MIN_CONF_NONV,
    }[cls]


def rubric_capped_confidence(cls: str, raw: float) -> float:
    """Rubric max confidence from image alone for neurotoxic / myotoxic."""
    if cls == "neurotoxic":
        return min(raw, MAX_CONF_NEURO)
    if cls == "myotoxic":
        return min(raw, MAX_CONF_MYOTOXIC)
    return raw


def strict_label_passes_rubric(cls: str, raw_conf: float, gap: float) -> bool:
    if gap < TOP2_GAP_STRICT:
        return False
    cap = rubric_capped_confidence(cls, raw_conf)
    need = min_conf_for_rubric_folder(cls)
    return cap >= need


def list_images(directory: str) -> list[str]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    out: list[str] = []
    for name in sorted(os.listdir(directory)):
        p = os.path.join(directory, name)
        if os.path.isfile(p) and os.path.splitext(name.lower())[1] in exts:
            out.append(p)
    if out:
        return sorted(out)
    for sub in ALL_SUBDIRS:
        d = os.path.join(directory, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.path.splitext(name.lower())[1] in exts:
                out.append(p)
    return sorted(out)


def laplacian_variance_gray(pil_img: Image.Image) -> float:
    g = np.asarray(pil_img.convert("L"), dtype=np.float64)
    if g.size < 4:
        return 0.0
    gy, gx = np.gradient(g)
    return float(np.var(gx) + np.var(gy))


def mean_luminance(pil_img: Image.Image) -> float:
    return float(np.asarray(pil_img.convert("L"), dtype=np.float64).mean())


def softmax_np(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x, axis=-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=-1, keepdims=True)


def entropy_np(p: np.ndarray, eps: float = 1e-8) -> float:
    p = np.clip(p, eps, 1.0)
    return float(-np.sum(p * np.log(p)))


def scattered_blood_fraction(pil_img: Image.Image, size: int = 200) -> float:
    """High value ≈ many small red spots (e.g. non-venomous tooth rows); not a diagnosis."""
    a = np.asarray(pil_img.convert("RGB").resize((size, size)), dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (r > 85.0) & (r > g + 18.0) & (r > b + 18.0)
    return float(mask.mean())


# If CLIP says cytotoxic but image looks like many scattered punctures, reject (rubric: mild redness ≠ cytotoxic).
SCATTER_REJECT_CYTOTOXIC = 0.022
CYTOTOXIC_MIN_CONF = 0.75


def pick_device(explicit: str | None) -> torch.device:
    if explicit:
        return torch.device(explicit)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def default_batch_size(device: torch.device, model_name: str) -> int:
    is_large = "large" in model_name.lower()
    if device.type == "cuda":
        return 32 if is_large else 64
    if device.type == "mps":
        return 24 if is_large else 64
    return 8 if is_large else 16


def fmt_num(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".")


@torch.inference_mode()
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--review-csv", default=None)
    parser.add_argument("--classified-dir", default=None)
    parser.add_argument("--copy", action="store_true")
    parser.add_argument("--no-copy", action="store_true")
    parser.add_argument("--model", default="openai/clip-vit-large-patch14")
    parser.add_argument("--device", default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--single-prompt", action="store_true")
    parser.add_argument(
        "--min-folder-conf",
        type=float,
        default=MIN_FOLDER_CONFIDENCE_DEFAULT,
        help="Default min softmax top-1 (per-class rubric mins override; default: 0.75)",
    )
    parser.add_argument(
        "--min-margin",
        type=float,
        default=MIN_FOLDER_MARGIN,
        help="Min top1-top2 margin to assign a class folder (default: 0.12)",
    )
    parser.add_argument(
        "--max-entropy",
        type=float,
        default=MAX_SOFTMAX_ENTROPY,
        help="Max softmax entropy (6 classes); above → unknown (default: 1.28)",
    )
    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Disable morphology step: many small punctures → non_venomous (overrides wrong hemotoxic/CLIP).",
    )
    args = parser.parse_args()
    use_hybrid = not args.no_hybrid

    min_fc = args.min_folder_conf
    min_mg = args.min_margin
    max_ent = args.max_entropy

    device = pick_device(args.device)
    batch_size = args.batch_size if args.batch_size else default_batch_size(device, args.model)
    use_amp = device.type in ("cuda", "mps")

    image_paths = list_images(args.image_dir)
    if not image_paths:
        print(f"No images under {args.image_dir}", file=sys.stderr)
        raise SystemExit(1)

    classified_dir = None if args.no_copy else (args.classified_dir or os.path.abspath(args.image_dir))

    print(
        f"Device: {device} | batch: {batch_size} | min_conf={min_fc} | min_margin={min_mg} | max_H={max_ent} | hybrid={use_hybrid}",
        flush=True,
    )
    print(f"Loading {args.model} …", flush=True)
    model = CLIPModel.from_pretrained(args.model).to(device)
    if use_amp:
        model = model.half()
    model.eval()
    processor = CLIPProcessor.from_pretrained(args.model)

    classes = list(RUBRIC_CLIP_CLASSES)
    n_classes = len(classes)
    n_prompts = 1 if args.single_prompt else len(CLASS_PROMPTS_ENSEMBLE[classes[0]])
    flat_prompts: list[str] = []
    for c in classes:
        tpl = CLASS_PROMPTS_ENSEMBLE[c]
        for i in range(n_prompts):
            flat_prompts.append(tpl[i])

    text_inputs = processor(text=flat_prompts, return_tensors="pt", padding=True, truncation=True)
    text_inputs = {k: v.to(device) for k, v in text_inputs.items()}
    if use_amp:
        text_inputs = {k: v.half() if v.dtype.is_floating_point else v for k, v in text_inputs.items()}

    text_features = model.get_text_features(**text_inputs)
    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
    logit_scale = model.logit_scale.exp()

    meta: dict[str, tuple[Image.Image | None, float, float, str | None]] = {}
    pending: list[tuple[str, Image.Image]] = []
    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
        except Exception as e:
            meta[path] = (None, 0.0, 0.0, str(e))
            continue
        meta[path] = (img, laplacian_variance_gray(img), mean_luminance(img), None)
        pending.append((path, img))

    # top_label, conf, second_label, conf2, gap, entropy, probs (n_classes,)
    clip_map: dict[str, tuple[str, float, str, float, float, float, np.ndarray]] = {}

    for start in range(0, len(pending), batch_size):
        chunk = pending[start : start + batch_size]
        paths_chunk = [p[0] for p in chunk]
        imgs = [p[1] for p in chunk]

        inputs = processor(images=imgs, return_tensors="pt", padding=True)
        pixel_values = inputs["pixel_values"].to(device)
        if use_amp:
            pixel_values = pixel_values.half()

        if use_amp:
            with torch.autocast(device_type=device.type, dtype=torch.float16):
                image_features = model.get_image_features(pixel_values=pixel_values)
        else:
            image_features = model.get_image_features(pixel_values=pixel_values)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        raw = image_features @ text_features.T
        bsz = raw.shape[0]
        raw = raw.float().view(bsz, n_classes, n_prompts).mean(dim=-1)
        logits = logit_scale * raw
        probs = softmax_np(logits.cpu().numpy())

        for j, path in enumerate(paths_chunk):
            p = probs[j]
            order = np.argsort(-p)
            top_idx = int(order[0])
            second_idx = int(order[1])
            conf = float(p[top_idx])
            conf2 = float(p[second_idx])
            gap = conf - conf2
            top_label = classes[top_idx]
            second_label = classes[second_idx]
            ent = entropy_np(p)
            clip_map[path] = (top_label, conf, second_label, conf2, gap, ent, p.copy())

        done = min(start + batch_size, len(pending))
        if done % 200 == 0 or done == len(pending):
            print(f"  CLIP {done}/{len(pending)} …", flush=True)

    flat_rows: list[tuple] = []
    for path in image_paths:
        if meta[path][0] is None:
            flat_rows.append(
                (
                    path,
                    "unknown",
                    0.0,
                    f"failed to load: {meta[path][3]}",
                    UNKNOWN_FOLDER,
                    0.0,
                    "",
                    0.0,
                    0.0,
                    "",
                    True,
                    0.0,
                )
            )
            continue

        blur_v, lum = meta[path][1], meta[path][2]
        top_label, conf, s2l, s2c, gap, ent, probs = clip_map[path]
        pil = meta[path][0]
        assert pil is not None
        idx = {c: i for i, c in enumerate(classes)}
        conf_for = lambda c: float(probs[idx[c]])

        quality_ok = blur_v >= BLUR_VAR_THRESHOLD and lum >= MEAN_LUMINANCE_DARK
        entropy_ok = ent <= max_ent
        mc_top = max(min_fc, min_conf_for_rubric_folder(top_label))
        model_ok = conf >= mc_top and gap >= min_mg

        q_notes = []
        if blur_v < BLUR_VAR_THRESHOLD:
            q_notes.append(f"blur_var={blur_v:.1f}<{BLUR_VAR_THRESHOLD}")
        if lum < MEAN_LUMINANCE_DARK:
            q_notes.append(f"mean_lum={lum:.0f}<{MEAN_LUMINANCE_DARK}")

        necrosis_override = False
        try:
            nd = necrosis_dark_fraction(pil)
        except Exception:
            nd = 0.0

        if not quality_ok:
            dest_folder = UNKNOWN_FOLDER
            why = "unknown: image quality — " + "; ".join(q_notes)
        elif not entropy_ok:
            dest_folder = UNKNOWN_FOLDER
            why = f"unknown: softmax entropy {ent:.3f} > {max_ent} (ambiguous)"
        elif nd >= NECROSIS_OVERRIDE_CYTOTOXIC:
            necrosis_override = True
            dest_folder = "cytotoxic"
            why = (
                f"rubric tie-break: necrosis_dark_fraction={nd:.3f} ≥ {NECROSIS_OVERRIDE_CYTOTOXIC} "
                f"→ cytotoxic (overrides CLIP top {top_label})"
            )
        elif not model_ok:
            dest_folder = UNKNOWN_FOLDER
            if conf < mc_top and gap < min_mg:
                why = f"unknown: conf {conf:.2f} < {mc_top:.2f} (rubric min for {top_label}) and margin {gap:.2f} < {min_mg}"
            elif conf < mc_top:
                why = f"unknown: confidence {conf:.2f} < {mc_top:.2f} (rubric minimum for {top_label})"
            else:
                why = f"unknown: top-2 margin {gap:.2f} < {min_mg} ({top_label} vs {s2l})"
        elif top_label == "not_snakebite" and conf < MIN_CONF_NOT_SNAKEBITE:
            dest_folder = UNKNOWN_FOLDER
            why = f"unknown: not_snakebite requires conf ≥ {MIN_CONF_NOT_SNAKEBITE} (rubric tie-break)"
        elif top_label == "cytotoxic" and conf < CYTOTOXIC_MIN_CONF:
            dest_folder = UNKNOWN_FOLDER
            why = f"unknown: cytotoxic requires conf ≥ {CYTOTOXIC_MIN_CONF}, got {conf:.2f}"
        elif top_label == "cytotoxic" and scattered_blood_fraction(pil) > SCATTER_REJECT_CYTOTOXIC:
            sf = scattered_blood_fraction(pil)
            dest_folder = UNKNOWN_FOLDER
            why = (
                f"unknown: many scattered red foci (frac={sf:.3f}>{SCATTER_REJECT_CYTOTOXIC}); "
                "ambiguous vs tooth-row / mild erythema"
            )
        elif top_label == "hemotoxic" and scattered_blood_fraction(pil) < HEMOTOXIC_MIN_SCATTER_BLOOD:
            dest_folder = UNKNOWN_FOLDER
            why = (
                f"unknown: hemotoxic needs bleeding pattern (rubric); blood signal {scattered_blood_fraction(pil):.4f} "
                f"< {HEMOTOXIC_MIN_SCATTER_BLOOD}"
            )
        else:
            dest_folder = top_label
            why = HUMAN_REASON[top_label] + f" (conf {conf:.2f}, margin {gap:.2f}, H={ent:.3f})"

        hybrid_override = False
        if (
            use_hybrid
            and quality_ok
            and not necrosis_override
            and dest_folder in RUBRIC_CLIP_CLASSES
            and dest_folder not in ("non_venomous", "not_snakebite")
            and top_label in ("hemotoxic", "neurotoxic")
        ):
            try:
                pat, dbg = morphology_bite_pattern(pil)
                nd = necrosis_dark_fraction(pil)
                if pat == "many_small_teeth" and nd < 0.14:
                    dest_folder = "non_venomous"
                    hybrid_override = True
                    why = (
                        f"hybrid morphology: many small punctures (tooth-row pattern) dbg={dbg} "
                        f"necrosis_dark={nd:.3f}; overrides CLIP {top_label}"
                    )
            except Exception:
                pass

        # Strict label column (rubric v2)
        if hybrid_override:
            if strict_label_passes_rubric("non_venomous", conf_for("non_venomous"), gap):
                strict_lab = "non_venomous"
                strict_reason = "hybrid tooth-row morphology"
            else:
                strict_lab = "unknown"
                strict_reason = "hybrid tooth-row hint but non_venomous softmax below rubric"
        elif not quality_ok:
            strict_lab = "unknown"
            strict_reason = "quality gate"
        elif dest_folder == UNKNOWN_FOLDER:
            strict_lab = "unknown"
            strict_reason = "rubric gate or ambiguous"
        elif necrosis_override:
            if strict_label_passes_rubric("cytotoxic", conf_for("cytotoxic"), gap):
                strict_lab = "cytotoxic"
                strict_reason = "necrosis override + cytotoxic conf ok"
            else:
                strict_lab = "unknown"
                strict_reason = "necrosis visible but cytotoxic softmax below rubric"
        elif strict_label_passes_rubric(dest_folder, conf, gap):
            strict_lab = dest_folder
            strict_reason = "passed rubric"
        else:
            strict_lab = "unknown"
            strict_reason = "below rubric confidence for assigned folder"

        if dest_folder == UNKNOWN_FOLDER:
            out_conf = conf
        elif hybrid_override:
            out_conf = rubric_capped_confidence("non_venomous", conf_for("non_venomous"))
        elif necrosis_override:
            out_conf = rubric_capped_confidence("cytotoxic", conf_for("cytotoxic"))
        else:
            out_conf = rubric_capped_confidence(dest_folder, conf)

        full_reason = (
            f"folder={dest_folder}. clip_best={top_label}@{conf:.2f} margin={gap:.2f} H={ent:.3f}. {why}. "
            f"strict={strict_reason}"
        )

        needs_review = (dest_folder == UNKNOWN_FOLDER or strict_lab == "unknown") and not hybrid_override

        flat_rows.append(
            (
                path,
                strict_lab,
                out_conf,
                full_reason,
                dest_folder,
                out_conf,
                s2l,
                s2c,
                gap,
                top_label,
                needs_review,
                ent,
            )
        )

    out_dir = os.path.dirname(os.path.abspath(args.output_csv)) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "image_path",
                "label_strict",
                "confidence_top1",
                "reason",
                "folder_label",
                "folder_confidence",
                "second_best_label",
                "second_best_confidence",
                "margin_top1_top2",
                "clip_best_guess",
                "softmax_entropy",
                "needs_manual_review",
            ]
        )
        for row in flat_rows:
            path = row[0]
            display = f"/snake_images/{os.path.basename(path)}"
            w.writerow(
                [
                    display,
                    row[1],
                    fmt_num(row[2]),
                    row[3],
                    row[4],
                    fmt_num(row[5]),
                    row[6],
                    fmt_num(row[7]) if row[6] else "",
                    fmt_num(row[8]),
                    row[9],
                    fmt_num(row[11]),
                    str(row[10]).lower(),
                ]
            )

    review_path = args.review_csv or os.path.join(out_dir, "label_review_queue.csv")
    n_rev = 0
    with open(review_path, "w", newline="", encoding="utf-8") as rf:
        rw = csv.writer(rf)
        rw.writerow(
            ["image_path", "folder_label", "clip_best_guess", "confidence", "margin", "entropy", "note"]
        )
        for row in flat_rows:
            if not row[10]:
                continue
            path = row[0]
            display = f"/snake_images/{os.path.basename(path)}"
            rw.writerow(
                [
                    display,
                    row[4],
                    row[9],
                    fmt_num(row[5]),
                    fmt_num(row[8]),
                    fmt_num(row[11]),
                    "unknown or strict unknown — review (rubric)",
                ]
            )
            n_rev += 1
    print(f"\nReview queue: {n_rev} rows -> {review_path}")

    if classified_dir and not args.no_copy:
        for sub in list(RUBRIC_CLIP_CLASSES) + [UNKNOWN_FOLDER]:
            os.makedirs(os.path.join(classified_dir, sub), exist_ok=True)
        n_moved = 0
        for row in flat_rows:
            path = row[0]
            if meta.get(path) and meta[path][0] is None:
                continue
            fl = row[4]  # destination folder (incl. unknown)
            base = os.path.basename(path)
            dest = os.path.join(classified_dir, fl, base)
            src_abs = os.path.abspath(path)
            dest_abs = os.path.abspath(dest)
            if src_abs == dest_abs:
                continue
            if os.path.exists(dest_abs) and dest_abs != src_abs:
                root, ext = os.path.splitext(base)
                dest = os.path.join(classified_dir, fl, f"{root}__dup{ext}")
                dest_abs = os.path.abspath(dest)
            if args.copy:
                shutil.copy2(path, dest_abs)
            else:
                shutil.move(path, dest_abs)
            n_moved += 1
        print(f"{'Copied' if args.copy else 'Moved'} {n_moved} files -> {classified_dir}")

    print("\nStrict label counts:", dict(Counter(r[1] for r in flat_rows)))
    print("Folder counts:", dict(Counter(r[4] for r in flat_rows if meta.get(r[0]) and meta[r[0]][0])))
    print(f"CSV: {args.output_csv}")


if __name__ == "__main__":
    main()
