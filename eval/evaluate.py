"""
Fashion AI Evaluation Script
=============================
Runs the GPT-4o-mini classifier against a labelled test set and
reports per-attribute accuracy.

Usage
-----
    python eval/evaluate.py --labels eval/sample_labels.csv --images eval/test_images/
    python eval/evaluate.py --labels eval/sample_labels.csv --images eval/test_images/ --out eval/results.csv

The labels CSV must have at minimum an `image_filename` column and one or
more attribute columns (garment_type, style, material, season, occasion, …).
"""

import sys
import csv
import argparse
import time
from pathlib import Path
from collections import defaultdict

# Allow running from the project root or from within eval/
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.classifier import classify_image


CATEGORICAL_FIELDS = [
    "garment_type", "style", "material", "pattern",
    "season", "occasion", "consumer_profile",
]
LOCATION_FIELDS = ["inferred_continent", "inferred_country", "inferred_city"]
ALL_EVALUATED_FIELDS = CATEGORICAL_FIELDS + LOCATION_FIELDS


def normalise(value: str) -> str:
    return value.strip().lower() if value else ""


def exact_match(pred: str, expected: str) -> bool:
    return normalise(pred) == normalise(expected)


def partial_match(pred: str, expected: str) -> bool:
    """True if either value contains the other (handles 'midi dress' vs 'dress')."""
    p, e = normalise(pred), normalise(expected)
    return p in e or e in p


def evaluate(labels_path: str, images_dir: str, out_path: str = None, delay: float = 0.5):
    labels_path = Path(labels_path)
    images_dir  = Path(images_dir)

    if not labels_path.exists():
        print(f"Labels file not found: {labels_path}")
        sys.exit(1)

    with open(labels_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if not rows:
        print("Labels file is empty.")
        sys.exit(1)

    evaluated_fields = [f for f in ALL_EVALUATED_FIELDS if f in rows[0]]
    print(f"Evaluating {len(rows)} images across fields: {evaluated_fields}\n")

    exact_hits:   defaultdict = defaultdict(int)
    partial_hits: defaultdict = defaultdict(int)
    totals:       defaultdict = defaultdict(int)
    results = []

    for i, row in enumerate(rows, 1):
        filename = row.get("image_filename") or row.get("image_path", "")
        image_path = images_dir / filename

        if not image_path.exists():
            print(f"[{i}/{len(rows)}] SKIP  {filename}  (file not found)")
            continue

        print(f"[{i}/{len(rows)}] Classifying {filename}...", end=" ", flush=True)
        try:
            pred = classify_image(str(image_path))
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({"image": filename, "error": str(exc)})
            continue

        result_row = {"image": filename}
        for field in evaluated_fields:
            expected = row.get(field, "")
            predicted = pred.get(field, "")
            if isinstance(predicted, list):
                predicted = ", ".join(predicted)

            if expected:
                totals[field] += 1
                em = exact_match(predicted, expected)
                pm = partial_match(predicted, expected)
                if em:
                    exact_hits[field] += 1
                if pm:
                    partial_hits[field] += 1
            else:
                em, pm = False, False

            result_row[f"{field}_expected"]  = expected
            result_row[f"{field}_predicted"] = predicted
            result_row[f"{field}_exact"]     = "1" if em else "0"
            result_row[f"{field}_partial"]   = "1" if pm else "0"

        results.append(result_row)
        print("OK")
        time.sleep(delay)  # Rate-limit API calls

    # Report 
    print("\n" + "=" * 60)
    print(f"{'Field':<25} {'Exact %':>8}  {'Partial %':>9}  {'N':>5}")
    print("-" * 60)
    for field in evaluated_fields:
        n = totals[field]
        if n == 0:
            continue
        em_pct = exact_hits[field]   / n * 100
        pm_pct = partial_hits[field] / n * 100
        print(f"{field:<25} {em_pct:>7.1f}%  {pm_pct:>8.1f}%  {n:>5}")
    print("=" * 60)

    overall_exact   = sum(exact_hits.values())   / max(sum(totals.values()), 1) * 100
    overall_partial = sum(partial_hits.values()) / max(sum(totals.values()), 1) * 100
    print(f"\nOverall exact match:   {overall_exact:.1f}%")
    print(f"Overall partial match: {overall_partial:.1f}%")

    # Optional CSV output
    if out_path and results:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Build fieldnames from the first successful (non-error) result row
        fieldnames = next(
            (list(r.keys()) for r in results if "error" not in r),
            list(results[0].keys()),
        )
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print(f"\nDetailed results written to: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate fashion classifier accuracy.")
    parser.add_argument("--labels", default="eval/sample_labels.csv",
                        help="Path to labels CSV")
    parser.add_argument("--images", default="eval/test_images/",
                        help="Directory containing test images")
    parser.add_argument("--out", default=None,
                        help="Optional path to write per-image results CSV")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds between API calls (default: 0.5)")
    args = parser.parse_args()
    evaluate(args.labels, args.images, args.out, args.delay)
