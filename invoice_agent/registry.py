"""The vendor registry: a JSON file in the repo, loaded once on import.

Names are matched through a normalised index built from each entry's name and
its aliases, because the model extracts the supplier exactly as printed and the
printed name carries legal suffixes the registry string does not.
"""

import json
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(_ROOT, "data", "vendor_registry.json")

# Dots and slashes are dropped rather than spaced out, so "A.S." and "A/S"
# reach the same token as "AS" and the suffix list can then remove it.
_JOINERS = re.compile(r"[./]")
_PUNCTUATION = re.compile(r"[^a-z0-9 ]+")
_WHITESPACE = re.compile(r"\s+")

# Dropped before matching so "Halden Industrial Fasteners AS" reaches the same
# key as "Halden Industrial Fasteners".
_LEGAL_SUFFIXES = {
    "ab", "as", "asa", "aps", "bv", "nv", "gmbh", "ag", "sa", "sl", "sas",
    "srl", "spa", "oy", "oyj", "ltd", "limited", "llc", "inc", "incorporated",
    "plc", "co", "corp", "corporation", "kb", "hb",
}


def normalise(name: str) -> str:
    """Lower-case, strip punctuation and drop trailing legal suffixes."""
    text = _PUNCTUATION.sub(" ", _JOINERS.sub("", name.lower()))
    words = _WHITESPACE.sub(" ", text).strip().split()
    while words and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def _load() -> list[dict]:
    with open(REGISTRY_PATH, encoding="utf-8") as handle:
        return json.load(handle)


SUPPLIERS: list[dict] = _load()

# Every spelling that should resolve to a supplier, normalised.
_INDEX: dict[str, dict] = {}
for _entry in SUPPLIERS:
    for _spelling in [_entry["name"], *_entry["aliases"]]:
        _INDEX.setdefault(normalise(_spelling), _entry)


def find(name: str) -> dict | None:
    """Return the registry entry for a printed supplier name, or None."""
    return _INDEX.get(normalise(name))


def nearest(name: str) -> str | None:
    """The closest registry name to an unmatched one, when there is an obvious one.

    Only reports a suggestion when the two share a distinctive first word, which
    is enough for the workshop and needs no fuzzy-matching library on stage.
    """
    words = normalise(name).split()
    if not words:
        return None
    head = words[0]
    for entry in SUPPLIERS:
        if normalise(entry["name"]).split()[:1] == [head]:
            return entry["name"]
    return None
