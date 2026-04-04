#!/usr/bin/env python3
"""
Download snakebite-related clinical images from verified sources into a single corpus folder.

Sources
  1. PubMed Central — Open-access articles matching a PubMed Central query; figures are
     resolved from article HTML (cdn.ncbi.nlm.nih.gov/pmc/blobs/...). Use per NCBI usage
     guidelines (moderate rate, identify your tool).
  2. WHO — Curated + scraped image URLs from official who.int pages (cdn.who.int).
  3. Google — Optional: Google Custom Search JSON API (searchType=image). Set env
     GOOGLE_API_KEY and GOOGLE_CSE_ID (Programmable Search Engine with Image search enabled).
     Do not scrape google.com/images (violates ToS).
  4. Negatives — Wikimedia Commons API: skin lesion / wound images not labeled as snakebite,
     for contrastive training (verify licenses in manifest).

Notes
  - "Bite mark only" cannot be guaranteed automatically; many PMC figures are clinical
    photos but may include charts or non–bite-site panels. Filter with manifest + manual QC.
  - Licenses: PMC OA figures follow the article license (see article page). WHO media
    terms: https://www.who.int/about/policies/publishing-policy . Wikimedia: per-file CC.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = (
    "SnakeBiteWoundCorpus/1.0 (+https://github.com; research image corpus; "
    "respect NCBI guidelines)"
)

PMC_BLOB_RE = re.compile(
    r'(?:https://cdn\.ncbi\.lm\.nih\.gov/pmc)?'
    r'/blobs/[a-z0-9]+/\d+/[a-f0-9]+/[^\s"\'<>]+\.(?:jpg|jpeg|png|gif|webp)',
    re.IGNORECASE,
)

# Curated WHO pages to scrape for cdn.who.int media (snakebite programme).
WHO_PAGES = [
    "https://www.who.int/health-topics/snakebite",
    "https://www.who.int/news-room/fact-sheets/detail/snakebite-envenoming",
    "https://www.who.int/teams/control-of-neglected-tropical-diseases/snakebite-envenoming/snakes-gallery",
]

WHO_IMG_RE = re.compile(
    r'https://cdn\.who\.int/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
    re.I,
)


def _fetch(url: str, timeout: float = 45.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _fetch_text(url: str, timeout: float = 45.0) -> str:
    return _fetch(url, timeout).decode("utf-8", errors="replace")


def pmc_esearch(term: str, retmax: int, retstart: int) -> list[str]:
    q = urllib.parse.urlencode(
        {
            "db": "pmc",
            "term": term,
            "retmax": str(retmax),
            "retstart": str(retstart),
            "retmode": "json",
        }
    )
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{q}"
    data = json.loads(_fetch_text(url))
    return data.get("esearchresult", {}).get("idlist", [])


def pmc_esummary(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    q = urllib.parse.urlencode(
        {
            "db": "pmc",
            "id": ",".join(ids),
            "retmode": "json",
        }
    )
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{q}"
    data = json.loads(_fetch_text(url))
    out = {}
    for uid, rec in data.get("result", {}).items():
        if uid == "uids" or not isinstance(rec, dict):
            continue
        out[uid] = rec
    return out


def extract_pmc_image_urls(html: str) -> list[str]:
    seen: list[str] = []
    for m in PMC_BLOB_RE.findall(html):
        if m.startswith("http"):
            u = m
        else:
            u = "https://cdn.ncbi.nlm.nih.gov/pmc" + m
        if u not in seen:
            seen.append(u)
    return seen


def download_pmc_corpus(
    out_dir: Path,
    manifest: list[dict[str, str]],
    term: str,
    max_articles: int,
    delay_s: float,
    skip_existing: bool,
) -> int:
    pmc_dir = out_dir / "pmc"
    pmc_dir.mkdir(parents=True, exist_ok=True)
    n_downloaded = 0
    retstart = 0
    batch = 50
    pmc_ids: list[str] = []

    while len(pmc_ids) < max_articles:
        need = max_articles - len(pmc_ids)
        chunk = pmc_esearch(term, retmax=min(batch, need), retstart=retstart)
        if not chunk:
            break
        pmc_ids.extend(chunk)
        retstart += len(chunk)
        if len(chunk) < min(batch, need):
            break

    pmc_ids = pmc_ids[:max_articles]
    summaries = pmc_esummary(pmc_ids)

    for raw_id in pmc_ids:
        pmcid = f"PMC{raw_id}"
        article_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
        title = summaries.get(raw_id, {}).get("title", "") or ""
        try:
            html = _fetch_text(article_url)
        except urllib.error.HTTPError as e:
            manifest.append(
                {
                    "filename": "",
                    "source": "pmc",
                    "label": "snakebite_article_figure",
                    "license_notes": "see article OA license on PMC page",
                    "source_url": article_url,
                    "article_title": title.replace("\n", " ")[:500],
                    "pmc_id": pmcid,
                    "extra": f"fetch_error:{e.code}",
                }
            )
            time.sleep(delay_s)
            continue

        urls = extract_pmc_image_urls(html)
        time.sleep(delay_s)

        for i, img_url in enumerate(urls):
            ext = Path(urllib.parse.urlparse(img_url).path).suffix.lower() or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            base = f"{pmcid}_{i:02d}{ext}"
            dest = pmc_dir / base
            if skip_existing and dest.exists():
                manifest.append(
                    {
                        "filename": str(dest.relative_to(out_dir)),
                        "source": "pmc",
                        "label": "snakebite_article_figure",
                        "license_notes": "OA article figure; follow PMC article license",
                        "source_url": img_url,
                        "article_title": title.replace("\n", " ")[:500],
                        "pmc_id": pmcid,
                        "extra": article_url,
                    }
                )
                continue
            try:
                data = _fetch(img_url)
                dest.write_bytes(data)
                n_downloaded += 1
            except OSError as e:
                manifest.append(
                    {
                        "filename": "",
                        "source": "pmc",
                        "label": "snakebite_article_figure",
                        "license_notes": "",
                        "source_url": img_url,
                        "article_title": title[:500],
                        "pmc_id": pmcid,
                        "extra": f"write_error:{e}",
                    }
                )
                continue
            manifest.append(
                {
                    "filename": str(dest.relative_to(out_dir)),
                    "source": "pmc",
                    "label": "snakebite_article_figure",
                    "license_notes": "OA article figure; follow PMC article license",
                    "source_url": img_url,
                    "article_title": title.replace("\n", " ")[:500],
                    "pmc_id": pmcid,
                    "extra": article_url,
                }
            )

    return n_downloaded


def download_who_corpus(
    out_dir: Path,
    manifest: list[dict[str, str]],
    skip_existing: bool,
) -> int:
    who_dir = out_dir / "who"
    who_dir.mkdir(parents=True, exist_ok=True)
    seen_urls: set[str] = set()
    n = 0
    for page in WHO_PAGES:
        try:
            html = _fetch_text(page)
        except urllib.error.HTTPError:
            continue
        for u in WHO_IMG_RE.findall(html):
            u = u.split("?")[0] if "tmb-" in u else u
            if "tmb-" in u:
                continue
            if u in seen_urls:
                continue
            seen_urls.add(u)
            name = re.sub(r"[^\w\-.]", "_", u.split("/")[-1])[:120] or "image"
            dest = who_dir / name
            if not dest.suffix:
                dest = dest.with_suffix(".jpg")
            if skip_existing and dest.exists():
                manifest.append(
                    {
                        "filename": str(dest.relative_to(out_dir)),
                        "source": "who",
                        "label": "who_snakebite_programme_media",
                        "license_notes": "https://www.who.int/about/policies/publishing-policy",
                        "source_url": u,
                        "article_title": page,
                        "pmc_id": "",
                        "extra": "",
                    }
                )
                continue
            try:
                dest.write_bytes(_fetch(u))
                n += 1
            except OSError:
                continue
            manifest.append(
                {
                    "filename": str(dest.relative_to(out_dir)),
                    "source": "who",
                    "label": "who_snakebite_programme_media",
                    "license_notes": "https://www.who.int/about/policies/publishing-policy",
                    "source_url": u,
                    "article_title": page,
                    "pmc_id": "",
                    "extra": "",
                }
            )
    return n


def download_google_cse(
    out_dir: Path,
    manifest: list[dict[str, str]],
    query: str,
    max_results: int,
    api_key: str,
    cx: str,
) -> int:
    """Google Custom Search JSON API (image search)."""
    gdir = out_dir / "google_cse"
    gdir.mkdir(parents=True, exist_ok=True)
    n = 0
    start = 1
    while n < max_results:
        params = urllib.parse.urlencode(
            {
                "key": api_key,
                "cx": cx,
                "q": query,
                "searchType": "image",
                "num": min(10, max_results - n),
                "start": start,
                "safe": "active",
            }
        )
        url = f"https://www.googleapis.com/customsearch/v1?{params}"
        try:
            data = json.loads(_fetch_text(url))
        except urllib.error.HTTPError as e:
            print("Google CSE error:", e, file=sys.stderr)
            break
        items = data.get("items") or []
        if not items:
            break
        for j, it in enumerate(items):
            link = it.get("link") or ""
            if not link.startswith("http"):
                continue
            title = (it.get("title") or "")[:300]
            ext = Path(urllib.parse.urlparse(link).path).suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
                ext = ".jpg"
            dest = gdir / f"cse_{start + j:04d}{ext}"
            try:
                dest.write_bytes(_fetch(link, timeout=30.0))
            except (urllib.error.HTTPError, OSError, TimeoutError):
                continue
            manifest.append(
                {
                    "filename": str(dest.relative_to(out_dir)),
                    "source": "google_cse",
                    "label": "web_image_snakebite_query",
                    "license_notes": "verify copyright at source page; API result only",
                    "source_url": link,
                    "article_title": title,
                    "pmc_id": "",
                    "extra": it.get("image", {}).get("contextLink", ""),
                }
            )
            n += 1
            if n >= max_results:
                break
        start += 10
        if len(items) < 10:
            break
        time.sleep(1.0)
    return n


def download_wikimedia_negatives(
    out_dir: Path,
    manifest: list[dict[str, str]],
    search: str,
    max_files: int,
    delay_s: float,
) -> int:
    """Commons files: not snakebite-specific; use as negatives after QC."""
    ndir = out_dir / "negatives_wikimedia"
    ndir.mkdir(parents=True, exist_ok=True)
    api = "https://commons.wikimedia.org/w/api.php"
    n = 0
    params: dict[str, str | int] = {
        "action": "query",
        "generator": "search",
        "gsrsearch": search,
        "gsrnamespace": 6,
        "gsrlimit": min(50, max_files),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "format": "json",
    }
    q = urllib.parse.urlencode(params)
    try:
        data = json.loads(_fetch_text(f"{api}?{q}"))
    except urllib.error.HTTPError:
        return 0
    pages = data.get("query", {}).get("pages", {})
    for _pid, page in pages.items():
        if n >= max_files:
            break
        ii = (page.get("imageinfo") or [{}])[0]
        img_url = ii.get("url") or ""
        if not img_url.startswith("http"):
            continue
        meta = ii.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        fname = page.get("title", "file").replace("File:", "")
        ext = Path(urllib.parse.urlparse(img_url).path).suffix.lower() or ".jpg"
        dest = ndir / f"neg_{n:04d}{ext}"
        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=45) as r:
                dest.write_bytes(r.read())
        except (urllib.error.HTTPError, OSError, TimeoutError):
            continue
        manifest.append(
            {
                "filename": str(dest.relative_to(out_dir)),
                "source": "wikimedia_commons",
                "label": "negative_not_snakebite_skin",
                "license_notes": lic or "see Commons file page",
                "source_url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(fname)}",
                "article_title": search,
                "pmc_id": "",
                "extra": img_url,
            }
        )
        n += 1
        time.sleep(delay_s)

    return n


def write_manifest(out_dir: Path, rows: list[dict[str, str]]) -> None:
    path = out_dir / "manifest.csv"
    fieldnames = [
        "filename",
        "source",
        "label",
        "license_notes",
        "source_url",
        "article_title",
        "pmc_id",
        "extra",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    ap = argparse.ArgumentParser(description="Download verified snakebite-related images.")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "snakebite_wound_corpus",
        help="Output root (default: project/snakebite_wound_corpus)",
    )
    ap.add_argument(
        "--pmc-query",
        default='("snake bite"[Title/Abstract] OR snakebite[Title/Abstract] OR envenoming[Title/Abstract]) AND open access[filter]',
        help="PMC esearch query",
    )
    ap.add_argument("--max-pmc-articles", type=int, default=80, help="Max PMC articles to scan")
    ap.add_argument("--delay", type=float, default=0.35, help="Seconds between NCBI/HTML requests")
    ap.add_argument("--skip-existing", action="store_true", help="Skip PMC downloads if file exists")
    ap.add_argument("--no-pmc", action="store_true")
    ap.add_argument("--no-who", action="store_true")
    ap.add_argument("--no-negatives", action="store_true")
    ap.add_argument(
        "--wikimedia-search",
        default="skin abrasion clinical",
        help="Commons search for negative images",
    )
    ap.add_argument("--max-negatives", type=int, default=40)
    ap.add_argument("--google-max", type=int, default=20)
    ap.add_argument("--google-query", default="snake bite wound clinical photograph")
    ap.add_argument("--no-google", action="store_true")
    args = ap.parse_args()

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, str]] = []
    counts: dict[str, int] = {}

    if not args.no_pmc:
        print("PMC: searching and downloading figures…")
        counts["pmc"] = download_pmc_corpus(
            out_dir,
            manifest,
            args.pmc_query,
            args.max_pmc_articles,
            args.delay,
            args.skip_existing,
        )
        print(f"  PMC new image files: {counts['pmc']}")

    if not args.no_who:
        print("WHO: downloading curated page images…")
        counts["who"] = download_who_corpus(out_dir, manifest, args.skip_existing)
        print(f"  WHO new image files: {counts['who']}")

    api_key = __import__("os").environ.get("GOOGLE_API_KEY", "")
    cx = __import__("os").environ.get("GOOGLE_CSE_ID", "")
    if not args.no_google and api_key and cx:
        print("Google CSE: image search…")
        counts["google_cse"] = download_google_cse(
            out_dir,
            manifest,
            args.google_query,
            args.google_max,
            api_key,
            cx,
        )
        print(f"  Google CSE downloads: {counts.get('google_cse', 0)}")
    elif not args.no_google:
        print(
            "Google CSE: skipped (set GOOGLE_API_KEY and GOOGLE_CSE_ID for Programmable Search).",
            file=sys.stderr,
        )

    if not args.no_negatives:
        print("Wikimedia Commons: negative skin images…")
        counts["negatives"] = download_wikimedia_negatives(
            out_dir,
            manifest,
            args.wikimedia_search,
            args.max_negatives,
            args.delay,
        )
        print(f"  Negatives: {counts.get('negatives', 0)}")

    write_manifest(out_dir, manifest)
    print("Wrote", out_dir / "manifest.csv", "rows:", len(manifest))
    print("Done. Review manifest for licenses; PMC figures inherit article CC-BY etc.")


if __name__ == "__main__":
    main()
