#!/usr/bin/env python3
"""
NOTE: For the production ML schema (severity, weight, family, PubMed+WHO rows),
use scripts/build_production_symptom_dataset.py instead. This script builds a
long-format species-joined table from WHO Appendix 1 (different columns).

Build symptom_dataset.csv from:
  (1) WHO TRS No. 1004 Annex 5 PDF — Appendix 1 (medically important species by family)
  (2) Symptom/pathology terms and family associations justified by the same PDF + WHO fact sheet

This script does not invent clinical signs; symptom rows are enumerated from fixed
strings present in WHO TRS §19.3 / §20.2.3 / WHO snakebite fact sheet (see SOURCES).

Output (long format; one species per row):
  venom_type,symptom,possible_snakes,source

possible_snakes: scientific binomial from WHO Appendix 1 for the family mapping applied.
"""
from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "symptom_data" / "processed"
ORIG_DIR = ROOT / "symptom_data" / "original"
OUT_CSV = OUT_DIR / "symptom_dataset.csv"
PDF_NAME = "who_trs1004_annex5.pdf"

WHO_TRS_URL = (
    "https://cdn.who.int/media/docs/default-source/biologicals/blood-products/"
    "document-migration/antivenomglrevwho_trs_1004_web_annex_5.pdf?sfvrsn=ef4b2aa5_3"
)
WHO_FS_URL = "https://www.who.int/news-room/fact-sheets/detail/snakebite-envenoming"

# Symptom inventory: verbatim or direct paraphrase of pathology named in WHO TRS / fact sheet.
# venom_type groups follow common clinical taxonomy used with WHO materials.
# families_apply: which Appendix-1 family labels get this symptom row (mechanistic mapping
# from WHO §19.3: vipers emphasized for haemorrhagic/coagulopathic; neurotoxicity for elapids
# in §19.3.6 + fact sheet paralysis; necrosis §19.3.2 “humans bitten by snakes” broadly—applied
# to Viperidae+Elapidae as major medically important groups in Appendix 1).
SYMPTOM_DEFS: list[dict[str, object]] = [
    {
        "venom_type": "Neurotoxic",
        "symptom": "neurotoxicity (laboratory/neurotoxic venom effects)",
        "families": ("Elapidae",),
        "source": f"{WHO_TRS_URL} §19.3.6 (neurotoxic activity; neutralization testing)",
    },
    {
        "venom_type": "Neurotoxic",
        "symptom": "paralysis",
        "families": ("Elapidae",),
        "source": f"{WHO_FS_URL} (paralysis that may prevent breathing)",
    },
    {
        "venom_type": "Neurotoxic",
        "symptom": "impaired breathing / ventilatory failure from neuromuscular paralysis",
        "families": ("Elapidae",),
        "source": f"{WHO_FS_URL} (paralysis preventing breathing)",
    },
    {
        "venom_type": "Neurotoxic",
        "symptom": "clinical neurotoxicity (e.g., as an antivenom trial endpoint)",
        "families": ("Elapidae",),
        "source": f"{WHO_TRS_URL} §20.2.3 (objective clinical improvement in neurotoxicity)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "haemostasis disruption (including haemorrhagic and coagulopathic mechanisms)",
        "families": ("Viperidae", "Atractaspididae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §19.3 opening (haemostasis-disruptive effects, haemorrhage, pro- and anti-coagulopathic effects)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "haemorrhage (systemic/local)",
        "families": ("Viperidae", "Atractaspididae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §19.3.1 (haemorrhagic activity; especially vipers)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "bleeding into tissues / organ haemorrhage (incl. cerebral haemorrhage as lethal mechanism)",
        "families": ("Viperidae",),
        "source": f"{WHO_TRS_URL} §19.3.1 (bleeding into the brain and other major organs; major lethal effect of many viperid species)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "coagulopathy / incoagulable blood",
        "families": ("Viperidae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §19.3.3–19.3.4 (procoagulant/defibrinogenating effects; Echis example §19.3)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "defibrinogenation / venom-induced consumption of coagulation factors",
        "families": ("Viperidae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §19.3.4 (in vivo defibrinogenating effect; incoagulable blood)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "bleeding diathesis",
        "families": ("Viperidae", "Atractaspididae", "Colubridae"),
        "source": f"{WHO_FS_URL} (bleeding disorders / fatal haemorrhage)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "abnormal prothrombin time (laboratory/clinical monitoring)",
        "families": ("Viperidae", "Colubridae", "Elapidae"),
        "source": f"{WHO_TRS_URL} §20.2.3 (prothrombin time as trial/laboratory parameter)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "thrombocytopenia / platelet count changes (interpret with antivenom effects)",
        "families": ("Viperidae", "Elapidae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §20.2.3 (platelet count as surrogate marker; caveat on complement activation from antivenom)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "renal failure / nephrotoxic injury (systemic venom effects)",
        "families": ("Viperidae", "Elapidae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §19.3 opening paragraph (nephrotoxic effects listed among venom pathologies)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "irreversible kidney failure (population-level outcome described by WHO)",
        "families": ("Viperidae", "Elapidae", "Colubridae"),
        "source": f"{WHO_FS_URL} (irreversible kidney failure)",
    },
    {
        "venom_type": "Hemotoxic",
        "symptom": "cardiac effects (systemic venom effects)",
        "families": ("Viperidae", "Elapidae", "Colubridae"),
        "source": f"{WHO_TRS_URL} §19.3 opening paragraph (cardiac effects listed among venom pathologies)",
    },
    {
        "venom_type": "Cytotoxic",
        "symptom": "local dermonecrosis / necrotizing skin injury",
        "families": ("Viperidae", "Elapidae"),
        "source": f"{WHO_TRS_URL} §19.3.2 (venom-induced local dermonecrosis in humans bitten by snakes)",
    },
    {
        "venom_type": "Cytotoxic",
        "symptom": "local tissue effects / necrosis (trial endpoint)",
        "families": ("Viperidae", "Elapidae"),
        "source": f"{WHO_TRS_URL} §20.2.3 (development of local tissue effects such as necrosis)",
    },
    {
        "venom_type": "Cytotoxic",
        "symptom": "myonecrosis / myotoxic injury (muscle damage, CK release)",
        "families": ("Viperidae", "Elapidae"),
        "source": f"{WHO_TRS_URL} §19.3.5 (myotoxicity, myonecrosis, muscle enzyme release)",
    },
    {
        "venom_type": "Cytotoxic",
        "symptom": "oedema (local muscle oedema in experimental myotoxicity)",
        "families": ("Viperidae", "Elapidae"),
        "source": f"{WHO_TRS_URL} §19.3.5 (oedema listed alongside inflammatory infiltration in muscle injury)",
    },
    {
        "venom_type": "Cytotoxic",
        "symptom": "myoglobinuria (myoglobin in urine after myotoxic injury)",
        "families": ("Viperidae", "Elapidae"),
        "source": f"{WHO_TRS_URL} §19.3.5 (myoglobin in urine)",
    },
    {
        "venom_type": "Cytotoxic",
        "symptom": "severe local tissue destruction (limb threat / disability)",
        "families": ("Viperidae", "Elapidae"),
        "source": f"{WHO_FS_URL} (severe local tissue destruction; permanent disability/amputation risk)",
    },
]


def _load_pdf_path() -> Path:
    dest = ORIG_DIR / PDF_NAME
    if not dest.exists():
        tmp = Path("/tmp/who_trs1004.pdf")
        if not tmp.exists():
            raise FileNotFoundError(
                "Place WHO TRS No.1004 Annex 5 PDF at "
                f"{dest} or /tmp/who_trs1004.pdf (download from WHO)"
            )
        shutil.copy(tmp, dest)
    return dest


# Epithets that are English words / PDF artefacts (not Latin species names).
_EPITHET_STOP = {
    "and",
    "or",
    "the",
    "of",
    "in",
    "to",
    "for",
    "with",
    "from",
    "by",
    "on",
    "at",
    "as",
    "is",
    "it",
    "an",
    "a",
    "no",
    "not",
    "only",
    "per",
    "via",
    "spp",
    "complex",
}

# Place / prose words that appear as Title Case before "and …" in geography sentences.
_GENUS_BLOCKLIST = {
    "Cameroon",
    "Gabon",
    "Chad",
    "Niger",
    "Benin",
    "Togo",
    "Ghana",
    "Mali",
    "Peru",
    "Chile",
    "Brazil",
    "India",
    "Nepal",
    "Bhutan",
    "Japan",
    "China",
    "Taiwan",
    "Korea",
    "Mongolia",
    "Russia",
    "Turkey",
    "Israel",
    "Jordan",
    "Lebanon",
    "Syria",
    "Iraq",
    "Iran",
    "Kuwait",
    "Qatar",
    "Oman",
    "Yemen",
    "Saudi",
    "Egypt",
    "Libya",
    "Tunisia",
    "Algeria",
    "Morocco",
    "Western",
    "United",
    "Arab",
    "Democratic",
    "Republic",
    "South",
    "North",
    "East",
    "West",
    "Central",
    "Islands",
    "Island",
    "African",
    "Asian",
    "American",
    "Amazonian",
    "Atlantic",
    "Caribbean",
    "European",
    "Mediterranean",
    "Australian",
    "Australo",
    "Papuan",
    "Indonesian",
    "Malaysian",
    "Philippine",
    "Borneo",
    "Sulawesi",
    "Bali",
    "Lombok",
    "Wallace",
    "Madagascar",
    "Mauritius",
    "Seychelles",
    "Comoros",
    "Canary",
    "Cabo",
    "Verde",
    "Rodrigues",
    "Lamu",
    "Zanzibar",
    "Pemba",
    "Mafia",
    "Bazaruto",
    "Inhaca",
    "Principe",
    "Bioko",
    "Fernando",
    "Dahlak",
    "Antigua",
    "Barbuda",
    "Cayman",
    "Cuba",
    "Jamaica",
    "Haiti",
    "Dominican",
    "Puerto",
    "Rico",
    "Virgin",
    "Guinea",
    "Bissau",
    "Equatorial",
    "Burundi",
    "Rwanda",
    "Uganda",
    "Kenya",
    "Tanzania",
    "Somalia",
    "Djibouti",
    "Eritrea",
    "Ethiopia",
    "Sudan",
    "Angola",
    "Namibia",
    "Botswana",
    "Zimbabwe",
    "Zambia",
    "Malawi",
    "Mozambique",
    "Eswatini",
    "Lesotho",
    "Mayotte",
    "Reunion",
    "Sri",
    "Bangladesh",
    "Pakistan",
    "Afghanistan",
    "Myanmar",
    "Laos",
    "Cambodia",
    "Vietnam",
    "Thailand",
    "Malaysia",
    "Singapore",
    "Brunei",
    "Philippines",
    "Palau",
    "Fiji",
    "Samoa",
    "Tonga",
    "Vanuatu",
    "Solomon",
    "Australia",
    "Zealand",
    "Caledonia",
    "Argentina",
    "Uruguay",
    "Paraguay",
    "Bolivia",
    "Colombia",
    "Venezuela",
    "Guyana",
    "Suriname",
    "Ecuador",
    "Panama",
    "Costa",
    "Rica",
    "Nicaragua",
    "Honduras",
    "Guatemala",
    "Belize",
    "Mexico",
    "Canada",
    "Greenland",
    "Iceland",
    "Norway",
    "Sweden",
    "Finland",
    "Denmark",
    "Germany",
    "France",
    "Spain",
    "Portugal",
    "Italy",
    "Greece",
    "Poland",
    "Ukraine",
    "Romania",
    "Bulgaria",
    "Serbia",
    "Croatia",
    "Bosnia",
    "Montenegro",
    "Albania",
    "Macedonia",
    "Slovakia",
    "Czech",
    "Hungary",
    "Austria",
    "Switzerland",
    "Belgium",
    "Netherlands",
    "Luxembourg",
    "Ireland",
    "Britain",
    "Scotland",
    "Wales",
    "England",
    "Off",
    "Gulf",
    "Middle",
    "Near",
    "Far",
    "Sub",
    "Saharan",
    "Hong",
    "Kong",
    "Special",
    "Administrative",
    "Region",
    "Province",
    "State",
    "Territory",
    "Territories",
    "Ocean",
    "Sea",
    "Bay",
    "Lake",
    "River",
    "Mount",
    "New",
    "Old",
    "Great",
    "Lesser",
    "Upper",
    "Lower",
    "Inner",
    "Outer",
    "Cat",
    "This",
    "They",
    "There",
    "These",
    "Users",
    "Appendix",
    "Model",
}


def _parse_taxon_segment(segment: str) -> str | None:
    """Return 'Genus species' or 'Genus species subspecies' from one comma/semicolon chunk."""
    segment = segment.strip()
    if not segment:
        return None
    segment = re.sub(r"\([^)]*\)", " ", segment)
    segment = re.sub(r"\s+", " ", segment).strip()
    segment = re.sub(r"^Cat\s*[12]\s*:\s*", "", segment, flags=re.I)
    # Trinomial
    m3 = re.match(r"^([A-Z][a-z]+)\s+([a-z][a-z0-9\-]+)\s+([a-z][a-z0-9\-]+)$", segment)
    if m3:
        g, s, t = m3.group(1), m3.group(2), m3.group(3)
        if s in _EPITHET_STOP or t in _EPITHET_STOP:
            return None
        if g in _GENUS_BLOCKLIST:
            return None
        if len(s) < 3 or not s.replace("-", "").isalpha():
            return None
        if not t.replace("-", "").isalpha():
            return None
        return f"{g} {s} {t}"
    # Binomial
    m2 = re.match(r"^([A-Z][a-z]+)\s+([a-z][a-z0-9\-]+)$", segment)
    if not m2:
        return None
    g, s = m2.group(1), m2.group(2)
    if s in _EPITHET_STOP:
        return None
    if g in _GENUS_BLOCKLIST:
        return None
    if len(s) < 3 or not s.replace("-", "").isalpha():
        return None
    return f"{g} {s}"


def _extract_taxa_from_family_chunk(chunk: str) -> set[str]:
    out: set[str] = set()
    chunk = re.sub(r"\([^)]*\)", " ", chunk)
    parts = re.split(r"[,;]", chunk)
    for raw in parts:
        taxon = _parse_taxon_segment(raw)
        if taxon:
            out.add(taxon)
    return out


def parse_appendix_species(pdf_path: Path) -> dict[str, set[str]]:
    """Return family -> set of scientific names parsed from WHO Appendix 1 tables."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit("Install pypdf: pip install pypdf") from e

    reader = PdfReader(str(pdf_path))
    # Pages containing Appendix 1 country/species lists (PDF page refs in printed doc differ).
    text = "\n".join((reader.pages[i].extract_text() or "") for i in range(156, len(reader.pages)))
    text = re.sub(r"\s+", " ", text)

    fam_sets: dict[str, set[str]] = {k: set() for k in ("Elapidae", "Viperidae", "Colubridae", "Atractaspididae", "Hydrophiidae")}
    # Split on family labels so we keep multi-species chunks like
    # "Viperidae: Echis carinatus; Macrovipera lebetina" (semicolon does NOT end the chunk).
    parts = re.split(
        r"(Elapidae|Viperidae|Colubridae|Atractaspididae|Hydrophiidae)\s*:\s*",
        text,
        flags=re.I,
    )
    # parts: [preamble, fam1, body1, fam2, body2, ...]
    for i in range(1, len(parts), 2):
        fam = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if fam not in fam_sets:
            continue
        fam_sets[fam] |= _extract_taxa_from_family_chunk(body)
    return fam_sets


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)
    pdf = _load_pdf_path()

    fam_to_species = parse_appendix_species(pdf)
    total_specs = sum(len(v) for v in fam_to_species.values())

    rows: list[list[str]] = []
    for sd in SYMPTOM_DEFS:
        vt = str(sd["venom_type"])
        sym = str(sd["symptom"])
        src = str(sd["source"])
        fams = tuple(sd["families"])  # type: ignore[arg-type]
        for fam in fams:
            for sp in sorted(fam_to_species.get(fam, ())):
                rows.append([vt, sym, sp, src])

    meta_path = ORIG_DIR / "symptom_build_meta.json"
    import json

    meta_path.write_text(
        json.dumps(
            {
                "who_pdf": str(pdf),
                "who_pdf_url": WHO_TRS_URL,
                "who_fact_sheet_url": WHO_FS_URL,
                "species_per_family": {k: len(v) for k, v in fam_to_species.items()},
                "total_unique_species": total_specs,
                "symptom_concepts": len(SYMPTOM_DEFS),
                "total_csv_rows": len(rows),
                "coverage_scope": (
                    "Medically important snake species listed in WHO TRS No.1004 Annex 5 Appendix 1 "
                    "(not every snake species worldwide). Sea-snake genera are not labelled as Hydrophiidae "
                    "in this appendix edition; many marine elapids may appear under Elapidae in regional lists."
                ),
                "method": (
                    "Symptoms enumerated from WHO TRS §19.3 / §20.2.3 and WHO snakebite fact sheet only. "
                    "Species parsed from Appendix 1 PDF text with comma/semicolon splitting and genus blocklists "
                    "to remove geographic false positives. Rows = symptom × species (family-filtered join)."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    cat_path = OUT_DIR / "symptom_catalog.csv"
    with cat_path.open("w", encoding="utf-8", newline="") as f:
        wc = csv.writer(f)
        wc.writerow(["venom_type", "symptom", "source"])
        for sd in SYMPTOM_DEFS:
            wc.writerow([sd["venom_type"], sd["symptom"], sd["source"]])

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["venom_type", "symptom", "possible_snakes", "source"])
        w.writerows(rows)

    print("Wrote", OUT_CSV, "rows:", len(rows))
    print("Wrote", cat_path, "symptom concepts:", len(SYMPTOM_DEFS))
    print("Meta:", meta_path)


if __name__ == "__main__":
    main()
