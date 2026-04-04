#!/usr/bin/env python3
"""
Build symptom_dataset.csv and context_features.csv (ML feature catalog): one row per
discriminating (feature_type, venom_type, symptom, family, snake context) with severity, importance rank,
uniform weight, temporal bounds, local-sign hints, and sources.

Scope: **clinical observations / syndromes** only. Bite circumstances (time of day,
sleeping indoors) and pure temporal summaries from cohort studies belong in a
separate fusion/context pipeline, not here.

Rules:
  - Symptoms and mappings are backed only by listed WHO URLs and PubMed records.
  - onset_min_hours / onset_max_hours: numeric bounds for typical symptom onset
    or presentation delay; empty cells mean unknown / not applicable (e.g.
    epidemiological clock-time-only rows).
  - local_signs_absent_or_minimal: yes / no / variable / na (see meta JSON).
  - Legacy per-row `weight` in CURATED is an ordinal prior (not survey prevalence);
    exported `importance_rank` (1–7) and `weight` (= rank/7) avoid spurious
    decimal precision; optional `importance_rank` override on a row for class
    separation (unknown vs non_venomous).

Output columns:
  feature_type, venom_type, symptom, severity, importance_rank, weight_tier, weight,
  possible_snakes, family, onset_min_hours, onset_max_hours,
  local_signs_absent_or_minimal, source

  feature_type is ``symptom`` for clinical syndrome labels in symptom_dataset.csv, and
  ``context`` for bite circumstance / epidemiology / timing metadata in
  symptom_data/processed/context_features.csv (fusion layer inputs — not symptoms).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "symptom_data" / "processed"
ORIG_DIR = ROOT / "symptom_data" / "original"
OUT_CSV = OUT_DIR / "symptom_dataset.csv"
OUT_CONTEXT_CSV = OUT_DIR / "context_features.csv"
META_PATH = ORIG_DIR / "production_build_meta.json"

WHO_FS = "https://www.who.int/news-room/fact-sheets/detail/snakebite-envenoming"
WHO_TRS = (
    "https://cdn.who.int/media/docs/default-source/biologicals/blood-products/"
    "document-migration/antivenomglrevwho_trs_1004_web_annex_5.pdf?sfvrsn=ef4b2aa5_3"
)

# Curated rows: each must have an https source (WHO or PubMed).
# Optional: onset_min_hours, onset_max_hours, local_signs_absent_or_minimal,
# importance_rank (override). Legacy float `weight` is converted to rank/7 export.
CURATED: list[dict[str, object]] = [
    # --- Neurotoxic (Elapidae; Russell's viper neuro signs per cited study) ---
    {
        "venom_type": "neurotoxic",
        "symptom": "ptosis",
        "severity": "early",
        "weight": 0.9,
        "possible_snakes": "cobra; krait; mamba; coral snake",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/30274500/ "
            "(black mamba envenomation: severe ptosis); "
            f"{WHO_FS} (paralysis/neuromuscular effects)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "ptosis",
        "severity": "early",
        "weight": 0.9,
        "possible_snakes": "Russell's viper",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26923566/ "
            "(Russell's viper neurotoxicity: ptosis in all with neurotoxicity)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "diplopia",
        "severity": "early",
        "weight": 0.7,
        "possible_snakes": "Russell's viper",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26923566/ "
            "(diplopia with ophthalmoplegia in Russell's viper neurotoxicity)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "diplopia",
        "severity": "early",
        "weight": 0.7,
        "possible_snakes": "cobra; krait; mamba; coral snake",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/32138479/ "
            "(prospective cohort: diplopia among neuro signs in snakebite); "
            f"{WHO_FS} (neuromuscular paralysis spectrum)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "ophthalmoplegia",
        "severity": "early",
        "weight": 0.75,
        "possible_snakes": "Russell's viper",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26923566/ "
            "(ophthalmoplegia in Russell's viper neurotoxicity)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "ophthalmoplegia",
        "severity": "early",
        "weight": 0.75,
        "possible_snakes": "krait",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/29169382/ "
            "(Ceylon krait: ophthalmoplegia with neuromuscular paralysis)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "facial paralysis",
        "severity": "moderate",
        "weight": 0.72,
        "possible_snakes": "krait",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/29169382/ "
            "(Ceylon krait: facial muscle weakness)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "bulbar palsy (speech and swallow dysfunction)",
        "severity": "severe",
        "weight": 0.92,
        "possible_snakes": "krait",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/32068871/ "
            "(krait-related neuroparalysis cohort: bulbar palsy)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "bulbar palsy (speech and swallow dysfunction)",
        "severity": "severe",
        "weight": 0.92,
        "possible_snakes": "coral snake",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/30660557/ "
            "(coral snake: paralysis of bulbar muscles)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "respiratory failure",
        "severity": "critical",
        "weight": 1.0,
        "possible_snakes": "coral snake; mamba",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/30660557/ "
            "(coral snake: respiratory failure requiring mechanical ventilation); "
            f"{WHO_FS} (paralysis that may prevent breathing)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "respiratory failure",
        "severity": "critical",
        "weight": 1.0,
        "possible_snakes": "mamba",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/30274500/ "
            "(mamba: labored breathing, need for ventilatory support context)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "progressive muscle weakness",
        "severity": "moderate",
        "weight": 0.88,
        "possible_snakes": "krait",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/32068871/ "
            "(krait-related envenoming: neuroparalysis cohort — progressive weakness)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "respiratory muscle weakness (neuroparalytic)",
        "severity": "critical",
        "weight": 0.98,
        "possible_snakes": "krait; cobra; mamba; coral snake",
        "family": "Elapidae",
        "source": (
            f"{WHO_FS} (paralysis that may prevent breathing); "
            f"{WHO_TRS} §19.3.6 (neurotoxic activity; neuromuscular paralysis risk)"
        ),
    },
    # --- India / Sri Lanka Big Four: Bungarus caeruleus (common krait) syndromes ---
    {
        "venom_type": "neurotoxic",
        "symptom": (
            "minimal or absent local swelling at bite site (syndromic vs many other "
            "venomous snakes in same cohort)"
        ),
        "severity": "early",
        "weight": 0.94,
        "possible_snakes": "common krait (Bungarus caeruleus)",
        "family": "Elapidae",
        "onset_min_hours": None,
        "onset_max_hours": None,
        "local_signs_absent_or_minimal": "yes",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/18784244/ "
            "(prospective Sri Lanka study: only 9% of B. caeruleus bites had local "
            "swelling vs 93% in non-krait bites — all krait swelling cases mild)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": (
            "severe neurotoxicity course with intubation often within hours of bite "
            "(hospital cohort)"
        ),
        "severity": "critical",
        "weight": 0.91,
        "possible_snakes": "common krait (Bungarus caeruleus)",
        "family": "Elapidae",
        "onset_min_hours": 1.0,
        "onset_max_hours": 6.0,
        "local_signs_absent_or_minimal": "variable",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26829229/ "
            "(B. caeruleus: intubation within 7 h post-bite in severe cases; "
            "median antivenom 3.5 h post-bite)"
        ),
    },
    # --- India Big Four: Echis carinatus (saw-scaled viper) ---
    {
        "venom_type": "hemotoxic",
        "symptom": "venom-induced consumption coagulopathy (VICC)",
        "severity": "moderate",
        "weight": 0.9,
        "possible_snakes": "saw-scaled viper (Echis carinatus)",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 1.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41606599/ "
            "(E. carinatus: procoagulant venom, VICC context); "
            "https://pubmed.ncbi.nlm.nih.gov/34345431/ "
            "(E. carinatus: consumption coagulopathy); "
            "https://pubmed.ncbi.nlm.nih.gov/38153416/ "
            "(Indian polyvalent antivenom covers Big Four including E. carinatus)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "localized pain and swelling (early local envenoming)",
        "severity": "moderate",
        "weight": 0.58,
        "possible_snakes": "saw-scaled viper (Echis carinatus)",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 1.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/34345431/ "
            "(E. carinatus envenoming: localized pain and swelling); "
            "https://pubmed.ncbi.nlm.nih.gov/41606599/ "
            "(SSV bite: local swelling among initial manifestations)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "renal impairment / acute kidney injury (systemic envenoming)",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "saw-scaled viper (Echis carinatus)",
        "family": "Viperidae",
        "onset_min_hours": None,
        "onset_max_hours": None,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/34345431/ "
            "(E. carinatus: renal impairment reported in clinical manifestations)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "bleeding and coagulopathy (early presentation)",
        "severity": "moderate",
        "weight": 0.84,
        "possible_snakes": "saw-scaled viper (Echis carinatus)",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 1.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41606599/ "
            "(E. carinatus: mild bleeding with coagulopathy early in course)"
        ),
    },
    # --- Hemotoxic (general viperidae) ---
    {
        "venom_type": "hemotoxic",
        "symptom": "venom-induced consumption coagulopathy (VICC)",
        "severity": "moderate",
        "weight": 0.85,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/35670073/ "
            "(VICC after snakebite; diagnostic monitoring context)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "coagulopathy / incoagulable blood",
        "severity": "moderate",
        "weight": 0.82,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.3–19.3.4 (procoagulant/defibrinogenating effects; "
            "incoagulable blood)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "bleeding (gums, nose, bite site, mucosal)",
        "severity": "moderate",
        "weight": 0.8,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_FS} (bleeding disorders that can lead to fatal haemorrhage); "
            f"{WHO_TRS} §19.3.1 (haemorrhagic activity)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hematemesis",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.1 (haemorrhagic activity; bleeding into major organs "
            "including gastrointestinal tract — systemic haemorrhagic syndrome)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hematuria",
        "severity": "severe",
        "weight": 0.87,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.1 (haemorrhagic activity; systemic bleeding diathesis "
            "including renal tract bleeding in severe coagulopathy); "
            f"{WHO_FS} (bleeding disorders)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "intracranial hemorrhage",
        "severity": "critical",
        "weight": 1.0,
        "possible_snakes": "viper; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.1 (bleeding into the brain as major lethal effect of "
            "many viperid species)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hypotension",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3 opening (cardiovascular/systemic effects in venom "
            "pathophysiology); {WHO_FS} (life-threatening systemic envenoming)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "shock",
        "severity": "critical",
        "weight": 1.0,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_FS} (fatal outcomes including haemorrhage/shock context); "
            f"{WHO_TRS} §19.3 (systemic haemorrhagic/coagulopathic syndromes)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "acute kidney injury",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "viper; Russell's viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            f"{WHO_FS} (kidney failure); "
            f"{WHO_TRS} §19.3 (nephrotoxic effects among venom pathologies)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "swelling (local envenoming)",
        "severity": "moderate",
        "weight": 0.55,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26923566/ "
            "(Russell's viper: local envenoming common); "
            f"{WHO_FS} (local tissue injury)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "local pain",
        "severity": "moderate",
        "weight": 0.5,
        "possible_snakes": "viper; pit viper; rattlesnake; Russell's viper",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §20.2.3 (pain management/analgesia context in clinical care); "
            f"{WHO_FS} (local effects)"
        ),
    },
    # --- Cytotoxic (local tissue injury; overlaps with viper local effects) ---
    {
        "venom_type": "cytotoxic",
        "symptom": "tissue necrosis / dermonecrosis",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.2 (venom-induced local dermonecrosis); "
            f"{WHO_FS} (severe local tissue destruction)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "severe local pain",
        "severity": "moderate",
        "weight": 0.65,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §20.2.3 (analgesia in management of local effects); "
            f"{WHO_FS} (local tissue destruction)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "swelling (local)",
        "severity": "moderate",
        "weight": 0.5,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.5 (oedema in muscle/local injury context); "
            f"{WHO_FS} (local tissue injury)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "blistering / bullae",
        "severity": "moderate",
        "weight": 0.62,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/39466297/ "
            "(pit viper envenoming: hemorrhagic bulla, progressive swelling, wound necrosis); "
            f"{WHO_TRS} §19.3.2 (local dermonecrosis)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "ulceration",
        "severity": "severe",
        "weight": 0.78,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            f"{WHO_FS} (severe local tissue destruction; chronic ulceration/disability "
            "risk); {WHO_TRS} §19.3.2 (local necrosis)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "secondary bacterial infection of wound",
        "severity": "moderate",
        "weight": 0.55,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/28905944/ "
            "(snakebite management: antibiotic therapy used — implies secondary "
            "infection/compromised tissue context)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "ecchymosis / bruising (local)",
        "severity": "moderate",
        "weight": 0.58,
        "possible_snakes": "viper; pit viper; rattlesnake",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.1 (local haemorrhage in haemorrhagic envenoming)"
        ),
    },
    # Elapid local necrosis (some cobras)
    {
        "venom_type": "cytotoxic",
        "symptom": "tissue necrosis / dermonecrosis",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "cobra",
        "family": "Elapidae",
        "source": (
            f"{WHO_TRS} §19.3.2 (local dermonecrosis in humans bitten by snakes "
            "— includes elapid examples in guideline narrative)"
        ),
    },
    # --- Myotoxic (emphasis sea snakes per user + cited ASP data) ---
    {
        "venom_type": "myotoxic",
        "symptom": "myotoxicity (muscle injury)",
        "severity": "severe",
        "weight": 0.92,
        "possible_snakes": "sea snake",
        "family": "Hydrophiidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/35387331/ "
            "(Australian sea snake envenoming: myotoxicity predominant)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "muscle pain",
        "severity": "moderate",
        "weight": 0.7,
        "possible_snakes": "sea snake",
        "family": "Hydrophiidae",
        "source": (
            f"{WHO_TRS} §19.3.5 (myotoxicity, muscle pain/injury); "
            "https://pubmed.ncbi.nlm.nih.gov/35387331/ (sea snake clinical series)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "muscle weakness",
        "severity": "moderate",
        "weight": 0.75,
        "possible_snakes": "sea snake",
        "family": "Hydrophiidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/35387331/ "
            "(sea snake: myotoxicity; prior case reports describe neurotoxicity — "
            "muscle weakness in systemic envenoming)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "rhabdomyolysis",
        "severity": "severe",
        "weight": 0.95,
        "possible_snakes": "sea snake",
        "family": "Hydrophiidae",
        "source": (
            f"{WHO_TRS} §19.3.5 (myonecrosis, muscle enzyme release); "
            "https://pubmed.ncbi.nlm.nih.gov/35387331/ (sea snake myotoxicity)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "dark urine (myoglobinuria)",
        "severity": "severe",
        "weight": 0.93,
        "possible_snakes": "sea snake",
        "family": "Hydrophiidae",
        "source": (
            f"{WHO_TRS} §19.3.5 (myoglobin in urine after myotoxic injury)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "paralysis (reported in some sea snake envenoming)",
        "severity": "critical",
        "weight": 0.95,
        "possible_snakes": "sea snake",
        "family": "Hydrophiidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/35387331/ "
            "(background: prior Australian case reports describe neurotoxicity)"
        ),
    },
    # --- Global medically important species (PubMed/WHO-backed; symptom-level rows) ---
    # Africa
    {
        "venom_type": "cytotoxic",
        "symptom": "local myonecrosis / prolonged muscle damage (viperid envenoming)",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": "puff adder (Bitis arietans)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41150197/ "
            "(Bitis arietans: clinically relevant; unresolved skeletal muscle damage "
            "after envenoming)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "coagulopathy / cytotoxic venom effects (systemic and local)",
        "severity": "moderate",
        "weight": 0.82,
        "possible_snakes": "puff adder (Bitis arietans)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41089656/ "
            "(Bitis arietans venom: cytotoxic effects and coagulopathy)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "rapid neurotoxic envenoming (mamba species)",
        "severity": "critical",
        "weight": 0.95,
        "possible_snakes": (
            "green mamba (Dendroaspis viridis); "
            "eastern green mamba (Dendroaspis angusticeps)"
        ),
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41150182/ "
            "(Dendroaspis spp.: rapid complex neurotoxic envenoming; antivenom context); "
            "https://pubmed.ncbi.nlm.nih.gov/30274500/ "
            "(Dendroaspis polylepis — black mamba: severe neurotoxic presentation)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "severe neurotoxicity (ptosis, respiratory compromise risk)",
        "severity": "critical",
        "weight": 0.98,
        "possible_snakes": "black mamba (Dendroaspis polylepis)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/30274500/ "
            "(black mamba envenomation: severe ptosis, ventilatory support); "
            "https://pubmed.ncbi.nlm.nih.gov/41150182/ (Dendroaspis spp. neurotoxicity)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "venom-induced consumption coagulopathy (VICC)",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": "boomslang (Dispholidus typus)",
        "family": "Colubridae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/33205728/ "
            "(Dispholidus typus: VICC via procoagulant venom effects); "
            f"{WHO_TRS} §19.3 (colubrid/Viperidae-related coagulopathy discussion)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hemorrhagic and procoagulant venom effects (Echis spp.)",
        "severity": "severe",
        "weight": 0.86,
        "possible_snakes": "carpet viper (Echis ocellatus)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41013462/ "
            "(Echis ocellatus venom: haemorrhagic/anticoagulant pathophysiology); "
            f"{WHO_FS} (viper envenoming syndromes)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "venom ophthalmia / ocular surface injury (spitting cobra defense)",
        "severity": "severe",
        "weight": 0.85,
        "possible_snakes": "spitting cobra (Naja nigricollis)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/29890230/ "
            "(Naja spitting cobras: venom ophthalmia — pain, corneal injury risk)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "systemic neurotoxicity after bite (Naja spp. elapid)",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "spitting cobra (Naja nigricollis)",
        "family": "Elapidae",
        "source": (
            f"{WHO_TRS} §19.3.6 (neurotoxic activity in elapid venoms); "
            f"{WHO_FS} (paralysis / neurotoxic envenoming); "
            "https://pubmed.ncbi.nlm.nih.gov/29890230/ (Naja genus — spitting cobras)"
        ),
    },
    # Americas
    {
        "venom_type": "cytotoxic",
        "symptom": "local myotoxic / tissue injury (pit viper envenoming)",
        "severity": "severe",
        "weight": 0.82,
        "possible_snakes": "fer-de-lance (Bothrops asper)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41290477/ "
            "(Bothrops asper myotoxin II — skeletal muscle damage in envenoming models)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hemorrhagic / coagulopathic envenoming (Bothrops spp.)",
        "severity": "severe",
        "weight": 0.84,
        "possible_snakes": "fer-de-lance (Bothrops asper)",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.1 (viperid haemorrhagic activity); "
            "https://pubmed.ncbi.nlm.nih.gov/41893541/ "
            "(medically important Colombian snakes incl. Bothrops asper — venomics)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "severe systemic envenoming (bushmaster)",
        "severity": "critical",
        "weight": 0.9,
        "possible_snakes": "bushmaster (Lachesis muta)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/39584046/ "
            "(Lachesis muta: severe human envenomation; antivenom neutralization context)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "VICC / thrombocytopenia (rattlesnake envenoming)",
        "severity": "severe",
        "weight": 0.85,
        "possible_snakes": "rattlesnakes (Crotalus spp.; e.g. C. atrox)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40392118/ "
            "(Crotalus atrox venom detection — medically important North American crotalid); "
            "https://pubmed.ncbi.nlm.nih.gov/41915134/ "
            "(crotalid snakebite / coagulopathy monitoring context)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "rhabdomyolysis / myotoxicity (some crotalid envenomings)",
        "severity": "severe",
        "weight": 0.8,
        "possible_snakes": "rattlesnakes (Crotalus spp.)",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.5 (myotoxic injury in viperid envenoming); "
            f"{WHO_FS} (local tissue destruction)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "neurotoxicity (coral snake envenoming)",
        "severity": "critical",
        "weight": 0.95,
        "possible_snakes": "coral snakes (Micrurus spp.; e.g. eastern coral snake Micrurus fulvius)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40738154/ "
            "(Micrurus / eastern coral snake neurotoxicity treatment context)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "local tissue injury (pit viper bite)",
        "severity": "moderate",
        "weight": 0.65,
        "possible_snakes": "copperhead (Agkistrodon contortrix)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40892140/ "
            "(North American Crotalidae / pit viper envenoming — Fab antivenom efficacy)"
        ),
    },
    # Southeast / South Asia
    {
        "venom_type": "hemotoxic",
        "symptom": "coagulopathy and bleeding diathesis (Malayan pit viper)",
        "severity": "severe",
        "weight": 0.87,
        "possible_snakes": "Malayan pit viper (Calloselasma rhodostoma)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41441570/ "
            "(Calloselasma rhodostoma envenoming — antivenom case context)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "local necrosis / swelling (Calloselasma rhodostoma)",
        "severity": "severe",
        "weight": 0.78,
        "possible_snakes": "Malayan pit viper (Calloselasma rhodostoma)",
        "family": "Viperidae",
        "source": (
            f"{WHO_TRS} §19.3.2 (local dermonecrosis — medically important vipers); "
            "https://pubmed.ncbi.nlm.nih.gov/41441570/ (C. rhodostoma clinical envenoming)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "severe neurotoxic envenoming (king cobra)",
        "severity": "critical",
        "weight": 1.0,
        "possible_snakes": "king cobra (Ophiophagus hannah)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40458835/ "
            "(Ophiophagus hannah bite: severe envenoming, cardiopulmonary arrest reported)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "krait-type neuroparalysis / bulbar involvement (Bungarus spp.)",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "banded krait (Bungarus fasciatus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/12571382/ "
            "(neurotoxic snakebite cohort includes krait species); "
            "https://pubmed.ncbi.nlm.nih.gov/32068871/ "
            "(krait neuroparalysis syndromes); "
            f"{WHO_TRS} §19.3.6 (elapid neurotoxicity)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "neurotoxic and local tissue effects (monocled cobra)",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": "monocled cobra (Naja kaouthia)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41843617/ "
            "(Naja kaouthia: medically important in Thailand; neurotoxic envenoming burden)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "local necrosis (Naja spp. cytotoxic venom components)",
        "severity": "severe",
        "weight": 0.82,
        "possible_snakes": "monocled cobra (Naja kaouthia)",
        "family": "Elapidae",
        "source": (
            f"{WHO_TRS} §19.3.2 (elapid local dermonecrosis possible); "
            "https://pubmed.ncbi.nlm.nih.gov/41843617/ (N. kaouthia medical importance)"
        ),
    },
    # Middle East / North Africa
    {
        "venom_type": "hemotoxic",
        "symptom": "progressive local and systemic envenoming (Palestine viper)",
        "severity": "severe",
        "weight": 0.86,
        "possible_snakes": "Palestine viper (Daboia palaestinae / Vipera palaestinae)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/28103732/ "
            "(Vipera palaestinae: antivenom for systemic and progressive local "
            "manifestations in children)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hemorrhagic / coagulopathic effects (Cerastes spp.)",
        "severity": "moderate",
        "weight": 0.78,
        "possible_snakes": "horned viper (Cerastes cerastes)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/34941741/ "
            "(Cerastes cerastes venom L-amino acid oxidase — envenomation injury mechanisms); "
            f"{WHO_FS} (viperid systemic effects)"
        ),
    },
    # Australia / Oceania (Australian elapids)
    {
        "venom_type": "hemotoxic",
        "symptom": "procoagulant venom effects / VICC (Australian brown snakes)",
        "severity": "severe",
        "weight": 0.9,
        "possible_snakes": "eastern brown snake (Pseudonaja textilis)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40864093/ "
            "(Australian elapid venoms: procoagulant activity — clinical implications; "
            "Pseudonaja among genera discussed)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "neurotoxicity (Australian brown snake envenoming)",
        "severity": "critical",
        "weight": 0.95,
        "possible_snakes": "eastern brown snake (Pseudonaja textilis)",
        "family": "Elapidae",
        "source": (
            f"{WHO_FS} (paralysis / neurotoxic envenoming); "
            "https://pubmed.ncbi.nlm.nih.gov/40864093/ "
            "(Australian elapid venom clinical implications)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "rapid paralysis / neurotoxicity (taipan)",
        "severity": "critical",
        "weight": 0.98,
        "possible_snakes": "taipan (Oxyuranus scutellatus; coastal taipan and related spp.)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/32889027/ "
            "(Oxyuranus scutellatus venom: neuromuscular blockade); "
            "https://pubmed.ncbi.nlm.nih.gov/37755983/ "
            "(Oxyuranus weakness/neurotoxicity experimental context)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "neurotoxicity (tiger snake envenoming)",
        "severity": "critical",
        "weight": 0.95,
        "possible_snakes": "tiger snake (Notechis scutatus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/38804832/ "
            "(Australian myotoxic snake envenoming — Notechis among genera in biomarker study); "
            f"{WHO_FS} (neurotoxic envenoming)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "myotoxicity / rhabdomyolysis risk (tiger snake)",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": "tiger snake (Notechis scutatus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/38804832/ "
            "(Notechis scutatus / Australian myotoxic envenoming biomarkers)"
        ),
    },
    # --- Additional verified taxa (user-requested gaps) ---
    {
        "venom_type": "hemotoxic",
        "symptom": "VICC / procoagulant envenoming (Egyptian saw-scaled viper)",
        "severity": "severe",
        "weight": 0.87,
        "possible_snakes": "Egyptian saw-scaled viper (Echis pyramidum)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40137922/ "
            "(Echis pyramidum — WHO Category 1; procoagulant venom, VICC in humans; "
            "Echis spp. comparison); "
            f"{WHO_FS} (Echis spp. medically important vipers)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hemorrhagic and coagulopathic envenoming (Russell's viper SE Asia)",
        "severity": "severe",
        "weight": 0.86,
        "possible_snakes": "Eastern Russell's viper (Daboia siamensis)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/39330863/ "
            "(Daboia spp. geographic variation in venoms and clinical outcomes; "
            "Thai/Javanese Russell's viper neurotoxins and envenoming context); "
            "https://pubmed.ncbi.nlm.nih.gov/39852967/ "
            "(Taiwan snakebite review — regional Daboia / viper envenoming)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "pre-synaptic neurotoxin-mediated neurotoxicity (Russell's viper venom variation)",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": "Eastern Russell's viper (Daboia siamensis); Daboia spp.",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/39330863/ "
            "(Daboia spp.: variation in neurotoxins and clinical outcomes by geography)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "neurotoxic envenoming (death adder — distinct presynaptic syndrome)",
        "severity": "critical",
        "weight": 0.96,
        "possible_snakes": "death adders (Acanthophis spp.)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/23029595/ "
            "(Australian Snakebite Project: Acanthophis spp. envenoming — neurotoxicity "
            "and antivenom response); "
            f"{WHO_FS} (neurotoxic envenoming)"
        ),
    },
    # --- Internet-verified expansion (PubMed clinical cohorts / case series) ---
    {
        "venom_type": "hemotoxic",
        "symptom": "VICC / venom-induced consumption coagulopathy (Asian pit viper cohort)",
        "severity": "severe",
        "weight": 0.88,
        "possible_snakes": (
            "Stejneger's pit viper (Trimeresurus stejnegeri); "
            "T. mucrosquamatus; Asian pit viper (Agkistrodon halys)"
        ),
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41488074/ "
            "(retrospective human cohort: hemotoxic envenoming by Trimeresurus and "
            "Agkistrodon spp. in Yunnan — coagulopathy and antivenom care); "
            f"{WHO_FS} (hemotoxic envenoming)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "local pain and progressive swelling (Mamushi bite — prospective cohort)",
        "severity": "moderate",
        "weight": 0.72,
        "possible_snakes": "Japanese mamushi (Gloydius blomhoffii)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/39156339/ "
            "(OROCHI study: pain and grade of swelling after G. blomhoffii bite); "
            "https://pubmed.ncbi.nlm.nih.gov/41359485/ "
            "(POCUS findings in Gloydius blomhoffii bites)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "local oedema and limb complications (e.g. compartment syndrome) — paediatric viper cohort",
        "severity": "severe",
        "weight": 0.84,
        "possible_snakes": "European adder / viper (Vipera berus — Romanian cohort)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41893551/ "
            "(retrospective paediatric viper bites in Romania: oedema, compartment "
            "syndrome requiring fasciotomy in severe case)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "documented human bite (pelagic sea snake — case report context)",
        "severity": "early",
        "weight": 0.55,
        "possible_snakes": "yellow-bellied sea snake (Pelamis platurus / Hydrophis platurus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/8728766/ "
            "(human bite by Pelamis platurus); "
            f"{WHO_FS} (sea snake envenoming)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "presynaptic neurotoxin-rich venom (many-banded krait — intervention research)",
        "severity": "critical",
        "weight": 0.94,
        "possible_snakes": "many-banded krait (Bungarus multicinctus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41343543/ "
            "(clinical anticholinergic/cholinesterase agents tested against "
            "B. multicinctus venom); "
            f"{WHO_FS} (neurotoxic krait envenoming)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "hemorrhagic / proteolytic venom phenotype (Type I) — management implications",
        "severity": "severe",
        "weight": 0.87,
        "possible_snakes": "South American rattlesnake (Crotalus durissus ruruima)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40749023/ "
            "(C. d. ruruima: Type I venoms with PIII-SVMPs — hemorrhagic/proteolytic "
            "phenotype vs Type II; clinical management in Roraima)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "crotoxin-related neurotoxic / myotoxic venom phenotype (Type II)",
        "severity": "critical",
        "weight": 0.93,
        "possible_snakes": "South American rattlesnake (Crotalus durissus ruruima)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40749023/ "
            "(Type II venoms: crotoxin PLA2 chains — neurotoxicity, myotoxicity, "
            "lethality; C. d. ruruima phenotypic dichotomy)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "local swelling, coagulopathy, compartment syndrome risk (paediatric cohort)",
        "severity": "severe",
        "weight": 0.86,
        "possible_snakes": "Arabian saw-scaled viper (Echis coloratus)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/34319210/ "
            "(E. coloratus envenomation in children — antivenom indications include "
            "local and systemic signs, abnormal coagulation; fasciotomy cases)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "severe regional viper envenoming (Morocco — antivenom neutralization context)",
        "severity": "severe",
        "weight": 0.85,
        "possible_snakes": (
            "horned viper (Cerastes cerastes); Moorish viper (Daboia mauritanica); "
            "puff adder (Bitis arietans)"
        ),
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/37368720/ "
            "(Morocco: C. cerastes, D. mauritanica, B. arietans among highest "
            "morbidity venomous vipers; antivenom efficacy assessment); "
            f"{WHO_FS} (viperid envenoming)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "medically important blunt-nosed viper envenoming (Palearctic)",
        "severity": "severe",
        "weight": 0.86,
        "possible_snakes": "blunt-nosed viper (Macrovipera lebetina)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/40461826/ "
            "(Macrovipera among highest medical-relevance vipers in the Palearctic); "
            f"{WHO_FS} (hemotoxic viper envenoming)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "coagulopathy, thrombocytopenia, systemic bleeding (keelback cohort)",
        "severity": "severe",
        "weight": 0.83,
        "possible_snakes": "Siamese red-necked keelback (Rhabdophis siamensis)",
        "family": "Colubridae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41369185/ "
            "(retrospective Thailand cohort: coagulopathy, thrombocytopenia, "
            "systemic bleeding after R. siamensis bites)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "local pain and edema with hypofibrinogenemia / coagulopathy (eyelash viper)",
        "severity": "severe",
        "weight": 0.85,
        "possible_snakes": "eyelash pit viper (Bothriechis schlegelii)",
        "family": "Viperidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/38379478/ "
            "(Colombia cohort: pain, edema, hypofibrinogenemia, prolonged PT — "
            "B. schlegelii envenoming)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "Australian elapid envenoming (rough-scaled snake in venom-detected cohort)",
        "severity": "moderate",
        "weight": 0.78,
        "possible_snakes": "rough-scaled snake (Tropidechis carinatus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/33138056/ "
            "(ASP-27: T. carinatus among identified species in Australian elapid "
            "bite cohort with envenomation biomarkers)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "delayed-onset myotoxicity with rhabdomyolysis (red-bellied black snake)",
        "severity": "severe",
        "weight": 0.89,
        "possible_snakes": "red-bellied black snake (Pseudechis porphyriacus)",
        "family": "Elapidae",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/41808211/ "
            "(human case: delayed myotoxicity, CK rise, myoglobinuria after "
            "P. porphyriacus envenoming)"
        ),
    },
    # --- Nausea / vomiting (common early self-reported systemic symptoms) ---
    {
        "venom_type": "neurotoxic",
        "symptom": "nausea and/or vomiting",
        "severity": "early",
        "weight": 0.45,
        "possible_snakes": "multiple venomous snakes",
        "family": "Elapidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 6.0,
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26852775/ "
            "(snakebite case: nausea, vomiting with local pain/swelling); "
            f"{WHO_FS} (systemic envenoming — general clinical assessment context)"
        ),
    },
    {
        "venom_type": "hemotoxic",
        "symptom": "nausea and/or vomiting",
        "severity": "early",
        "weight": 0.45,
        "possible_snakes": "multiple venomous snakes",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 6.0,
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/29305081/ "
            "(viper envenoming: nausea during early assessment); "
            f"{WHO_FS} (systemic effects of envenoming)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "nausea and/or vomiting",
        "severity": "early",
        "weight": 0.4,
        "possible_snakes": "multiple venomous snakes",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 6.0,
        "source": (
            f"{WHO_TRS} §20.2.3 (supportive care/analgesia context in envenoming); "
            "https://pubmed.ncbi.nlm.nih.gov/29305081/ (systemic symptoms with local "
            "envenoming)"
        ),
    },
    {
        "venom_type": "myotoxic",
        "symptom": "nausea and/or vomiting",
        "severity": "early",
        "weight": 0.45,
        "possible_snakes": "sea snake; other myotoxic envenoming",
        "family": "Hydrophiidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 6.0,
        "source": (
            f"{WHO_FS} (systemic envenoming); "
            f"{WHO_TRS} §19.3 (systemic venom pathologies)"
        ),
    },
    # --- Hypnale hypnale (hump-nosed pit viper) ---
    {
        "venom_type": "hemotoxic",
        "symptom": "coagulopathy / prolonged clotting screen (Hypnale envenoming)",
        "severity": "moderate",
        "weight": 0.75,
        "possible_snakes": "hump-nosed pit viper (Hypnale hypnale)",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 12.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/36687535/ "
            "(South India: Hypnale hypnale among hematotoxic bites; coagulation "
            "studies/VICC context); "
            "https://pubmed.ncbi.nlm.nih.gov/34582831/ "
            "(H. hypnale: coagulopathy among systemic effects)"
        ),
    },
    {
        "venom_type": "cytotoxic",
        "symptom": "local manifestations (pain, swelling, tissue injury risk; Hypnale)",
        "severity": "moderate",
        "weight": 0.65,
        "possible_snakes": "hump-nosed pit viper (Hypnale hypnale)",
        "family": "Viperidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 6.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/34582831/ "
            "(Hypnale hypnale: frequent local manifestations; systemic effects less "
            "common but described — coagulopathy, AKI); "
            "https://pubmed.ncbi.nlm.nih.gov/35581300/ "
            "(HNPV clinical local signs in series)"
        ),
    },
    # --- Classifier: non-venomous / dry bite / unknown ---
    {
        "venom_type": "non_venomous",
        "symptom": "no significant systemic symptoms",
        "severity": "early",
        "weight": 0.1,
        "importance_rank": 2,
        "possible_snakes": "non-venomous snakes; dry bite (no significant envenoming)",
        "family": "multiple",
        "onset_min_hours": 0.0,
        "onset_max_hours": 1.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/30758508/ "
            "(clinical spectrum from asymptomatic dry bite to severe envenomation); "
            "https://pubmed.ncbi.nlm.nih.gov/38668745/ "
            "(dry bites classified within snakebite cohort); "
            "https://pubmed.ncbi.nlm.nih.gov/24507436/ "
            "(dry bites observed in viperid cohort — incidence varies by species/setting); "
            f"{WHO_FS} (not all bites inject venom or cause envenoming)"
        ),
    },
    {
        "venom_type": "non_venomous",
        "symptom": "mild local pain at bite site only",
        "severity": "early",
        "weight": 0.15,
        "importance_rank": 3,
        "possible_snakes": "non-venomous snakes; dry bite (local only)",
        "family": "multiple",
        "onset_min_hours": 0.0,
        "onset_max_hours": 1.0,
        "local_signs_absent_or_minimal": "no",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26852775/ "
            "(mild envenoming / local pain and swelling — comparator for minimal presentation); "
            f"{WHO_FS} (local injury without systemic envenoming may occur)"
        ),
    },
    {
        "venom_type": "unknown",
        "symptom": "presentation insufficient for venom syndrome classification",
        "severity": "early",
        "weight": 0.05,
        "importance_rank": 1,
        "possible_snakes": "unknown",
        "family": "multiple",
        "onset_min_hours": None,
        "onset_max_hours": None,
        "local_signs_absent_or_minimal": "variable",
        "source": (
            f"{WHO_TRS} §20 (clinical trials/surveillance emphasize objective syndrome "
            "classification where species unidentified); "
            f"{WHO_FS} (syndromic diagnosis when snake not identified)"
        ),
    },
]

# Bite context / epidemiology / timing (not clinical symptoms) — for fusion with symptom rows.
CONTEXT_FEATURES: list[dict[str, object]] = [
    {
        "venom_type": "neurotoxic",
        "symptom": "nocturnal bite while sleeping indoors",
        "severity": "early",
        "weight": 0.5,
        "possible_snakes": "common krait (Bungarus caeruleus)",
        "family": "Elapidae",
        "onset_min_hours": None,
        "onset_max_hours": None,
        "local_signs_absent_or_minimal": "na",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/18784244/ "
            "(B. caeruleus: nocturnal indoor bites while sleeping — bite circumstance)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": (
            "EMNS: presentation after overnight nocturnal bite (often unwitnessed)"
        ),
        "severity": "moderate",
        "weight": 0.55,
        "possible_snakes": "common krait (Bungarus caeruleus)",
        "family": "Elapidae",
        "onset_min_hours": 6.0,
        "onset_max_hours": 12.0,
        "local_signs_absent_or_minimal": "yes",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/32068871/ "
            "(EMNS: nighttime indoor krait-bite pattern; absent fang marks more likely); "
            "https://pubmed.ncbi.nlm.nih.gov/41583157/ "
            "(early morning presentation of pediatric neurotoxic envenoming "
            "consistent with krait bite); "
            "https://pubmed.ncbi.nlm.nih.gov/18784244/ "
            "(B. caeruleus: nocturnal indoor bites while sleeping)"
        ),
    },
    {
        "venom_type": "neurotoxic",
        "symptom": "neurological signs typically within 6 hours",
        "severity": "early",
        "weight": 0.52,
        "possible_snakes": "common krait (Bungarus caeruleus)",
        "family": "Elapidae",
        "onset_min_hours": 0.0,
        "onset_max_hours": 6.0,
        "local_signs_absent_or_minimal": "variable",
        "source": (
            "https://pubmed.ncbi.nlm.nih.gov/26829229/ "
            "(B. caeruleus cohort: intubation within 7 h post-bite in severe cases — "
            "timing of neurological deterioration); "
            "https://pubmed.ncbi.nlm.nih.gov/32068871/ "
            "(krait neuroparalysis cohort — temporal presentation context)"
        ),
    },
]


TIER_NAMES = (
    "trace",
    "minimal",
    "low",
    "moderate",
    "marked",
    "severe",
    "critical",
)

SEVERITY_ORDER = ("early", "moderate", "severe", "critical")
LOCAL_OK = frozenset({"yes", "no", "variable", "na"})
VENOM_OK = frozenset(
    {
        "neurotoxic",
        "hemotoxic",
        "cytotoxic",
        "myotoxic",
        "non_venomous",
        "unknown",
    }
)


def _apply_default_onset_local(r: dict[str, object]) -> dict[str, object]:
    """Fill onset_min/max and local_signs when omitted."""
    out = dict(r)
    vt = str(out["venom_type"])
    sym = str(out["symptom"]).lower()
    ps = str(out["possible_snakes"]).lower()

    has_bounds = "onset_min_hours" in out or "onset_max_hours" in out
    if not has_bounds:
        if vt == "hemotoxic":
            if "swelling" in sym or "local pain" in sym:
                out["onset_min_hours"], out["onset_max_hours"] = 0.0, 1.0
            else:
                out["onset_min_hours"], out["onset_max_hours"] = None, None
        elif vt == "cytotoxic":
            out["onset_min_hours"], out["onset_max_hours"] = 0.0, 1.0
        elif vt == "neurotoxic":
            out["onset_min_hours"], out["onset_max_hours"] = 1.0, 6.0
        elif vt == "myotoxic":
            out["onset_min_hours"], out["onset_max_hours"] = None, None
        elif vt == "non_venomous":
            out["onset_min_hours"], out["onset_max_hours"] = 0.0, 1.0
        elif vt == "unknown":
            out["onset_min_hours"], out["onset_max_hours"] = None, None
        else:
            out["onset_min_hours"], out["onset_max_hours"] = None, None
    else:
        out.setdefault("onset_min_hours", None)
        out.setdefault("onset_max_hours", None)

    if "local_signs_absent_or_minimal" not in out:
        if vt == "hemotoxic":
            out["local_signs_absent_or_minimal"] = "no"
        elif vt == "cytotoxic":
            out["local_signs_absent_or_minimal"] = "no"
        elif vt == "neurotoxic":
            out["local_signs_absent_or_minimal"] = "variable"
        elif vt == "myotoxic":
            out["local_signs_absent_or_minimal"] = "na"
        elif vt in ("non_venomous", "unknown"):
            out["local_signs_absent_or_minimal"] = "variable"
        else:
            out["local_signs_absent_or_minimal"] = "na"

    if (
        vt == "neurotoxic"
        and "krait" in ps
        and "common krait" not in ps
        and any(
            x in sym
            for x in (
                "ptosis",
                "diplopia",
                "ophthalmoplegia",
                "facial paralysis",
                "bulbar",
                "progressive muscle weakness",
            )
        )
    ):
        out["local_signs_absent_or_minimal"] = "variable"

    return out


def _finalize_importance(r: dict[str, object]) -> dict[str, object]:
    """Derive importance_rank (1–7), weight_tier, uniform weight from legacy float."""
    out = dict(r)
    raw = float(out["weight"])
    if "importance_rank" in out:
        rank = int(out["importance_rank"])
    else:
        rank = max(1, min(7, math.ceil(raw * 7.0)))
    out["importance_rank"] = rank
    out["weight_tier"] = TIER_NAMES[rank - 1]
    out["weight_uniform"] = round(rank / 7.0, 4)
    del out["weight"]
    return out


def _fmt_num(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        if v == int(v):
            return str(int(v))
        return str(v)
    return str(v)


def _dedupe(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, ...]] = set()
    out: list[dict[str, object]] = []
    for r in rows:
        key = (
            str(r["venom_type"]),
            str(r["symptom"]),
            str(r["family"]),
            str(r["possible_snakes"]),
            str(r.get("onset_min_hours")),
            str(r.get("onset_max_hours")),
            str(r["local_signs_absent_or_minimal"]),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)

    enriched = [_apply_default_onset_local(x) for x in CURATED]
    deduped = _dedupe(enriched)
    rows = [_finalize_importance(x) for x in deduped]

    for r in rows:
        if r["severity"] not in SEVERITY_ORDER:
            raise ValueError(f"Bad severity: {r}")
        if r["venom_type"] not in VENOM_OK:
            raise ValueError(f"Bad venom_type: {r}")
        ir = int(r["importance_rank"])
        if not 1 <= ir <= 7:
            raise ValueError(f"Bad importance_rank: {r}")
        for k in (
            "venom_type",
            "symptom",
            "possible_snakes",
            "family",
            "source",
            "weight_tier",
            "local_signs_absent_or_minimal",
        ):
            if not str(r[k]).strip():
                raise ValueError(f"Empty {k}: {r}")
        if r["local_signs_absent_or_minimal"] not in LOCAL_OK:
            raise ValueError(f"Bad local_signs_absent_or_minimal: {r}")

    ctx_enriched = [_apply_default_onset_local(x) for x in CONTEXT_FEATURES]
    ctx_deduped = _dedupe(ctx_enriched)
    context_out = [_finalize_importance(x) for x in ctx_deduped]

    for r in context_out:
        if r["severity"] not in SEVERITY_ORDER:
            raise ValueError(f"Bad severity (context): {r}")
        if r["venom_type"] not in VENOM_OK:
            raise ValueError(f"Bad venom_type (context): {r}")
        ir = int(r["importance_rank"])
        if not 1 <= ir <= 7:
            raise ValueError(f"Bad importance_rank (context): {r}")
        for k in (
            "venom_type",
            "symptom",
            "possible_snakes",
            "family",
            "source",
            "weight_tier",
            "local_signs_absent_or_minimal",
        ):
            if not str(r[k]).strip():
                raise ValueError(f"Empty {k} (context): {r}")
        if r["local_signs_absent_or_minimal"] not in LOCAL_OK:
            raise ValueError(f"Bad local_signs_absent_or_minimal (context): {r}")

    csv_columns = [
        "feature_type",
        "venom_type",
        "symptom",
        "severity",
        "importance_rank",
        "weight_tier",
        "weight",
        "possible_snakes",
        "family",
        "onset_min_hours",
        "onset_max_hours",
        "local_signs_absent_or_minimal",
        "source",
    ]

    meta = {
        "output_csv": str(OUT_CSV),
        "row_count": len(rows),
        "context_features_csv": str(OUT_CONTEXT_CSV),
        "context_row_count": len(context_out),
        "venom_types": sorted({str(r["venom_type"]) for r in rows}),
        "families": sorted({str(r["family"]) for r in rows}),
        "columns": csv_columns,
        "onset_hours_semantics": (
            "onset_min_hours and onset_max_hours are numeric bounds (hours post-exposure) "
            "for symptom onset or presentation delay where applicable; empty cells mean "
            "unknown or not applicable (e.g. clock-time epidemiology without symptom-onset "
            "interval, or insufficient data)."
        ),
        "local_signs_semantics": (
            "yes = prominent local bite findings often absent or minimal; "
            "no = prominent local findings typical; variable = context-dependent; "
            "na = not applicable."
        ),
        "importance_semantics": (
            "importance_rank 1–7 is an ordinal training label derived from legacy "
            "per-row priors: rank = ceil(legacy_weight * 7) clamped to [1,7], except "
            "optional importance_rank overrides on classifier rows. Exported weight "
            "= rank/7 (uniform steps; not venom prevalence). For mentor review: "
            "do not interpret decimals as epidemiological proportions."
        ),
        "sources_policy": "Each row's source column lists WHO and/or PubMed URLs.",
        "big_four_india": (
            "Explicit rows for Bungarus caeruleus and Echis carinatus as before."
        ),
        "scope_exclusions": (
            "Bite circumstance and cohort-level timing metadata live in "
            "symptom_data/processed/context_features.csv (feature_type=context), not in "
            "symptom_dataset.csv (feature_type=symptom only). Join or fuse for models that "
            "need bite context."
        ),
        "global_species_coverage": (
            "Added symptom-level rows for major WHO/PubMed-cited taxa across Africa, "
            "Americas, Asia, MENA, and Australia. Some sources are species-specific "
            "case series; others cite genus-level or regional cohorts — see each "
            "row's source field. This list is not exhaustive of all world species."
        ),
        "verified_taxonomic_scope": (
            "Thousands of snake species are described globally. A row appears here ONLY "
            "if a WHO or PubMed-indexed source supports the clinical or "
            "venom-toxicology statement. Species with no usable published envenoming "
            "or venom data for syndrome mapping are omitted — not from lack of "
            "interest, but because invented symptom rows would be non-factual. "
            "A complete species checklist is a separate taxonomy product; this file "
            "is a verified symptom–taxon association catalog."
        ),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _write_feature_csv(
        path: Path, data: list[dict[str, object]], feature_type: str
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(csv_columns)
            for r in data:
                w.writerow(
                    [
                        feature_type,
                        r["venom_type"],
                        r["symptom"],
                        r["severity"],
                        r["importance_rank"],
                        r["weight_tier"],
                        f'{float(r["weight_uniform"]):.4f}',
                        r["possible_snakes"],
                        r["family"],
                        _fmt_num(r.get("onset_min_hours")),
                        _fmt_num(r.get("onset_max_hours")),
                        r["local_signs_absent_or_minimal"],
                        r["source"],
                    ]
                )

    _write_feature_csv(OUT_CSV, rows, "symptom")
    _write_feature_csv(OUT_CONTEXT_CSV, context_out, "context")

    print("Wrote", OUT_CSV, "rows:", len(rows))
    print("Wrote", OUT_CONTEXT_CSV, "rows:", len(context_out))
    print("Meta:", META_PATH)


if __name__ == "__main__":
    main()
