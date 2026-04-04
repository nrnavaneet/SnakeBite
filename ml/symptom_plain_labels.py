"""
Plain-language labels for symptom checkboxes (patient-facing).

Aligned by index with ``symptoms`` in ``models/symptom_catalog.json``. If the catalog
grows, extend this list or entries fall back to a shortened technical string.
"""
from __future__ import annotations

# (short_label, category) — categories kept simple for grouping in the UI
ORDERED_UI: list[tuple[str, str]] = [
    ("Very unwell with muscle or nerve effects (Australia)", "Regional notes"),
    ("Blood clotting problems (saw-scaled viper type)", "Bleeding & clotting"),
    ("Bleeding with low platelets (rattlesnake-type)", "Bleeding & clotting"),
    ("Blood clotting failure (Asian pit viper context)", "Bleeding & clotting"),
    ("Kidney problems / less urine", "Kidneys & urine"),
    ("Bleeding from gums, nose, or bite area", "Bleeding & clotting"),
    ("Bleeding with clotting problems (early on)", "Bleeding & clotting"),
    ("Blisters or large blisters on skin", "Bite & skin"),
    ("Trouble speaking or swallowing", "Nerves, eyes & face"),
    ("Clotting problems with tissue damage", "Bleeding & clotting"),
    ("Blood not clotting normally", "Bleeding & clotting"),
    ("Clotting tests very abnormal (Hypnale-type)", "Bleeding & clotting"),
    ("Bleeding tendency (Malayan pit viper context)", "Bleeding & clotting"),
    ("Bleeding with low platelets (keelback context)", "Bleeding & clotting"),
    ("Muscle and nerve effects together", "Nerves & muscles"),
    ("Dark or cola-colored urine", "Kidneys & urine"),
    ("Muscle breakdown appearing later", "Muscles"),
    ("Double vision", "Nerves, eyes & face"),
    ("Sea snake bite (known case)", "Regional notes"),
    ("Bruising around the bite", "Bite & skin"),
    ("Face weakness or drooping", "Nerves, eyes & face"),
    ("Vomiting blood", "Stomach"),
    ("Blood in urine", "Kidneys & urine"),
    ("Bleeding problems (sand viper type)", "Bleeding & clotting"),
    ("Bleeding problems (lancehead type)", "Bleeding & clotting"),
    ("Severe tissue bleeding (some vipers)", "Bleeding & clotting"),
    ("Bleeding problems (Russell’s viper type)", "Bleeding & clotting"),
    ("Bleeding problems (saw-scaled viper type)", "Bleeding & clotting"),
    ("Very low blood pressure", "Shock & circulation"),
    ("Stroke-like bleeding in the brain", "Bleeding & clotting"),
    ("Paralysis like a krait bite (throat/face)", "Nerves, eyes & face"),
    ("Pain, swelling, or tissue damage at bite", "Bite & skin"),
    ("Severe muscle damage at bite (viper)", "Bite & skin"),
    ("Muscle or tissue damage at bite (pit viper)", "Bite & skin"),
    ("Tissue death at bite (cobra-type)", "Bite & skin"),
    ("Tissue death or bad swelling (Malayan pit viper)", "Bite & skin"),
    ("Very swollen limb or compartment risk (child)", "Bite & skin"),
    ("Pain at bite site", "Bite & skin"),
    ("Pain and swelling with clotting problems", "Bite & skin"),
    ("Pain and swelling getting worse", "Bite & skin"),
    ("Swelling with clotting risk (child)", "Bite & skin"),
    ("Tissue damage at bite (pit viper)", "Bite & skin"),
    ("Pain and swelling soon after bite", "Bite & skin"),
    ("Serious viper bite (blunt-nosed type)", "Regional notes"),
    ("Only mild pain at bite", "Bite & skin"),
    ("Almost no swelling at bite", "Bite & skin"),
    ("Muscle aches", "Muscles"),
    ("Weakness in muscles", "Muscles"),
    ("Muscle damage from venom", "Muscles"),
    ("Muscle breakdown risk (tiger snake)", "Muscles"),
    ("Nausea or vomiting", "Stomach"),
    ("Nerve symptoms with skin damage (cobra-type)", "Nerves & muscles"),
    ("Nerve paralysis (death adder type)", "Nerves, eyes & face"),
    ("Nerve symptoms (brown snake, Australia)", "Nerves, eyes & face"),
    ("Nerve symptoms (coral snake)", "Nerves, eyes & face"),
    ("Nerve symptoms (tiger snake)", "Nerves, eyes & face"),
    ("No major body symptoms", "General"),
    ("Eye movement problems", "Nerves, eyes & face"),
    ("Paralysis (sea snake)", "Nerves, eyes & face"),
    ("Nerve paralysis (Russell’s viper type)", "Nerves, eyes & face"),
    ("Severe nerve paralysis (krait-type)", "Nerves, eyes & face"),
    ("Clotting problems (brown snake, Australia)", "Bleeding & clotting"),
    ("Getting worse locally and overall (viper)", "General"),
    ("Weakness getting worse", "Nerves, eyes & face"),
    ("Drooping eyelids", "Nerves, eyes & face"),
    ("Very fast nerve symptoms (mamba)", "Nerves, eyes & face"),
    ("Very fast paralysis (taipan)", "Nerves, eyes & face"),
    ("Kidney problems from venom", "Kidneys & urine"),
    ("Severe breathing problem / respiratory failure", "Breathing"),
    ("Weak breathing muscles", "Breathing"),
    ("Severe muscle breakdown", "Muscles"),
    ("Muscle breakdown (some rattlesnakes)", "Muscles"),
    ("Infection at wound", "Bite & skin"),
    ("Severe pain at bite", "Bite & skin"),
    ("Severe nerve effects (king cobra)", "Nerves, eyes & face"),
    ("Severe nerve symptoms (eyelids, breathing)", "Nerves, eyes & face"),
    ("Needed breathing support soon after bite", "Breathing"),
    ("Severe viper bite (North Africa context)", "Regional notes"),
    ("Very severe whole-body illness (bushmaster)", "General"),
    ("Collapse or shock", "Shock & circulation"),
    ("Swelling around bite", "Bite & skin"),
    ("Local swelling", "Bite & skin"),
    ("Nerve symptoms after cobra bite", "Nerves, eyes & face"),
    ("Dead skin / deep wound damage", "Bite & skin"),
    ("Open sore or ulcer at bite", "Bite & skin"),
    ("Venom in the eyes (spitting cobra)", "Nerves, eyes & face"),
    ("Blood clotting failure (VICC)", "Bleeding & clotting"),
]


def _fallback(value: str) -> tuple[str, str]:
    t = value.split("(")[0].strip()
    if len(t) > 56:
        t = t[:53] + "…"
    return (t or value[:56], "Other")


def attach_plain_labels(symptoms: list[str]) -> list[dict[str, str]]:
    """Build API/UI items: internal ``value`` must stay exact for scoring."""
    out: list[dict[str, str]] = []
    for i, value in enumerate(symptoms):
        if i < len(ORDERED_UI):
            label, category = ORDERED_UI[i]
        else:
            label, category = _fallback(value)
        out.append({"value": value, "label": label, "category": category})
    return out
