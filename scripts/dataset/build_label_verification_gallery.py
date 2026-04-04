#!/usr/bin/env python3
"""
Build one HTML page to manually review every row in image_dataset.csv (open in a browser).

Image paths in HTML are relative to the output HTML directory.
"""

from __future__ import annotations

import argparse
import csv
import html
import os


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-root", required=True, help="snake_images directory (contains class subfolders)")
    ap.add_argument("--csv", required=True, help="image_dataset.csv")
    ap.add_argument("--out", required=True, help="Output HTML path (e.g. .../label_verification_gallery.html)")
    args = ap.parse_args()

    out_dir = os.path.dirname(os.path.abspath(args.out)) or "."
    img_root = os.path.abspath(args.image_root)

    rows: list[dict[str, str]] = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_folder: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        fl = (row.get("folder_label") or "unknown").strip()
        by_folder.setdefault(fl, []).append(row)

    parts: list[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Snakebite label verification</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; margin: 16px; background: #1a1a1a; color: #eee; }",
        ".section { margin-bottom: 28px; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }",
        ".card { background: #2d2d2d; border-radius: 8px; padding: 8px; font-size: 11px; }",
        ".card img { width: 100%; height: 160px; object-fit: cover; border-radius: 4px; background: #111; }",
        ".meta { margin-top: 6px; line-height: 1.35; word-break: break-all; }",
        ".tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; }",
        ".neurotoxic { background: #1e5c3a; }",
        ".hemotoxic { background: #6b2c2c; }",
        ".cytotoxic { background: #4a4a4a; }",
        ".myotoxic { background: #2c3f6b; }",
        ".non_venomous { background: #5a5a3a; }",
        ".not_snakebite { background: #4a3a5a; }",
        ".unknown { background: #6b5a2c; }",
        ".unclear { background: #6b5a2c; }",
        "</style></head><body>",
        f"<h1>Label verification — {len(rows)} images</h1>",
        "<p>Scroll by class. Fix labels in CSV / folders after review.</p>",
    ]

    for folder in sorted(by_folder.keys()):
        items = by_folder[folder]
        tag_class = folder.replace(" ", "_")
        parts.append(f"<div class='section'><h2>{html.escape(folder)} ({len(items)})</h2><div class='grid'>")
        for row in items:
            base = os.path.basename((row.get("image_path") or "").strip())
            abs_img = os.path.join(img_root, folder, base)
            if not os.path.isfile(abs_img):
                rel = ""
            else:
                rel = os.path.relpath(abs_img, out_dir).replace(os.sep, "/")
            conf = row.get("folder_confidence", row.get("confidence_top1", ""))
            ent = row.get("softmax_entropy", "")
            margin = row.get("margin_top1_top2", "")
            review = row.get("needs_manual_review", "")
            parts.append("<div class='card'>")
            if rel:
                parts.append(f"<img src='{html.escape(rel)}' alt='' loading='lazy' />")
            else:
                parts.append(f"<div style='height:160px;display:flex;align-items:center;justify-content:center;color:#888'>missing<br/>{html.escape(base)}</div>")
            parts.append("<div class='meta'>")
            parts.append(f"<span class='tag {html.escape(tag_class)}'>{html.escape(folder)}</span><br/>")
            parts.append(f"<b>{html.escape(base)}</b><br/>")
            parts.append(
                f"conf {html.escape(str(conf))} | margin {html.escape(str(margin))} | H {html.escape(str(ent))}<br/>"
            )
            parts.append(f"review: {html.escape(str(review))}")
            parts.append("</div></div>")
        parts.append("</div></div>")

    parts.append("</body></html>")
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"Wrote {args.out} ({len(rows)} cards)")


if __name__ == "__main__":
    main()
