#!/usr/bin/env python3
"""Validate the GovTrue design-token contract.

This repository is the SINGLE SOURCE OF TRUTH for the estate's design tokens.
Every consumer (Platform, Codify, Archive, Meetings, Obligations, Licensing)
vendors a BYTE-IDENTICAL copy of tokens.css and tokens.json and guards it with a
drift-check against an immutable version tag. Consumers verify that their copy
matches this repo -- nobody verifies that this repo is internally coherent.

That is the gap this script closes. A tokens.css / tokens.json divergence, or an
hsl mirror that does not actually correspond to its hex, ships silently to every
consumer at the next tag: every downstream drift-check still passes, because they
compare against the wrong-but-canonical source.

What is enforced -- each of these is a requirement the files state about
themselves, not a convention invented here:

  1. tokens.json parses, and declares the sections consumers read.
  2. RAW PARITY. The raw palette in tokens.css and tokens.json declare the same
     token names with the same hex values. ("Hex values are authoritative.")
  3. HSL EXACTNESS. Every --gt-*-hsl mirror, in both files, is recomputed from
     its hex and must match. ("The hex value is authoritative; the mirror is a
     derived, exact conversion of it.")
  4. SEMANTIC RESOLUTION. Every var(--gt-*) reference resolves to a raw token
     that exists, and each JSON semantic entry agrees with tokens.css on both
     the raw token it refs and that token's hex value.
  5. MIRRORED NON-COLOR VALUES. Where tokens.json mirrors a non-color scale
     (spacing, radii, shadows, motion, font families, the type scale), the
     values must agree with tokens.css.

What is deliberately NOT enforced: that every token in tokens.css appears in
tokens.json. The README describes tokens.json as "a data mirror for non-CSS
consumers / tooling" -- it is curated, not a one-to-one dump. --chip-*, for
instance, is CSS-only by design. Asserting full parity would fail on intent
rather than on error.

Stdlib only, no network, no package manager. The repo has no build step; adding
a toolchain to run a validator would be a larger change than the thing validated.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = ROOT / "tokens.css"
JSON_PATH = ROOT / "tokens.json"

RAW_HEX_RE = re.compile(r"--gt-([a-z0-9-]+?):\s*(#[0-9A-Fa-f]{6})\s*;")
RAW_HSL_RE = re.compile(r"--gt-([a-z0-9-]+?)-hsl:\s*([0-9]+)\s+([0-9]+)%\s+([0-9]+)%\s*;")
SEM_VAR_RE = re.compile(r"^\s*--(?!gt-)([a-z0-9-]+):\s*var\(--gt-([a-z0-9-]+)\)\s*;", re.M)
DECL_RE = re.compile(r"^\s*--([a-z0-9-]+):\s*(.+?);\s*$", re.M)
VAR_REF_RE = re.compile(r"var\(--gt-([a-z0-9-]+)\)")

# CSS custom property -> path into tokens.json, for the non-color scales.
SCALE_MAP: dict[str, tuple[str, ...]] = {}
for _n in range(1, 11):
    SCALE_MAP[f"space-{_n}"] = ("spacing", "scale", str(_n))
for _r in ("sm", "button", "card", "panel", "pill"):
    SCALE_MAP[f"radius-{_r}"] = ("radii", _r)
for _s in ("sm", "md", "lg", "xl"):
    SCALE_MAP[f"shadow-{_s}"] = ("shadows", _s)
for _d in ("fast", "base", "slow"):
    SCALE_MAP[f"dur-{_d}"] = ("motion", "duration", _d)
for _e in ("out", "in-out"):
    SCALE_MAP[f"ease-{_e}"] = ("motion", "easing", _e)
for _f in ("serif-reading", "sans", "mono"):
    SCALE_MAP[f"font-{_f}"] = ("typography", "families", _f)

TYPE_ROLES = (
    "section-number",
    "catchline",
    "body",
    "subsection",
    "metadata-label",
    "breadcrumb",
    "toc",
)


def strip_comments(text: str) -> str:
    """Remove /* ... */ blocks so commentary never parses as a declaration."""
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def hex_to_hsl(hex_value: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to an (H, S%, L%) integer triplet, CSS hsl() convention."""
    r = int(hex_value[1:3], 16) / 255.0
    g = int(hex_value[3:5], 16) / 255.0
    b = int(hex_value[5:7], 16) / 255.0

    hi, lo = max(r, g, b), min(r, g, b)
    lightness = (hi + lo) / 2.0
    delta = hi - lo

    if delta == 0:
        hue, sat = 0.0, 0.0
    else:
        sat = delta / (1.0 - abs(2.0 * lightness - 1.0))
        if hi == r:
            hue = 60.0 * (((g - b) / delta) % 6.0)
        elif hi == g:
            hue = 60.0 * (((b - r) / delta) + 2.0)
        else:
            hue = 60.0 * (((r - g) / delta) + 4.0)

    return round(hue) % 360, round(sat * 100), round(lightness * 100)


def dig(obj, path: tuple[str, ...]):
    """Walk a path into nested dicts, returning None if any hop is missing."""
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    return obj


def main() -> int:
    failures: list[str] = []
    fail = failures.append

    for path in (CSS_PATH, JSON_PATH):
        if not path.is_file():
            print(f"FAIL: missing required file {path.name}", file=sys.stderr)
            return 1

    css = strip_comments(CSS_PATH.read_text(encoding="utf-8"))

    # --- 1. tokens.json parses and declares its sections -------------------
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: tokens.json is not valid JSON: {exc}", file=sys.stderr)
        return 1

    for section in ("raw", "semantic", "typography", "spacing", "radii", "shadows", "motion"):
        if not isinstance(data.get(section), dict) or not data[section]:
            fail(f"tokens.json is missing a non-empty '{section}' section")

    json_raw = data.get("raw") or {}
    json_sem = data.get("semantic") or {}

    css_raw = {n: h.upper() for n, h in RAW_HEX_RE.findall(css) if not n.endswith("-hsl")}
    css_hsl = {m[0]: (int(m[1]), int(m[2]), int(m[3])) for m in RAW_HSL_RE.findall(css)}

    if not css_raw:
        fail("tokens.css declares no raw --gt-* hex tokens (parser found nothing)")

    # --- 2. raw parity -----------------------------------------------------
    for name in sorted(set(css_raw) - set(json_raw)):
        fail(f"raw '{name}': in tokens.css but missing from tokens.json")
    for name in sorted(set(json_raw) - set(css_raw)):
        fail(f"raw '{name}': in tokens.json but missing from tokens.css")

    for name in sorted(set(css_raw) & set(json_raw)):
        json_hex = str((json_raw[name] or {}).get("hex", "")).upper()
        if css_raw[name] != json_hex:
            fail(f"raw '{name}': hex mismatch — tokens.css {css_raw[name]} vs tokens.json {json_hex}")

    # --- 3. hsl mirrors are exact conversions of their hex -----------------
    for name, hexv in sorted(css_raw.items()):
        expected = hex_to_hsl(hexv)
        exp_s = f"{expected[0]} {expected[1]}% {expected[2]}%"

        if name not in css_hsl:
            fail(f"raw '{name}': tokens.css declares no --gt-{name}-hsl mirror")
        elif css_hsl[name] != expected:
            got = css_hsl[name]
            fail(
                f"raw '{name}' ({hexv}): tokens.css hsl is "
                f"{got[0]} {got[1]}% {got[2]}%, exact conversion is {exp_s}"
            )

        entry = json_raw.get(name)
        if isinstance(entry, dict) and "hsl" in entry:
            m = re.match(r"^([0-9]+)\s+([0-9]+)%\s+([0-9]+)%$", str(entry["hsl"]).strip())
            if not m:
                fail(f"raw '{name}': tokens.json hsl '{entry['hsl']}' is not an 'H S% L%' triplet")
            elif (int(m[1]), int(m[2]), int(m[3])) != expected:
                fail(
                    f"raw '{name}' ({hexv}): tokens.json hsl is "
                    f"{m[1]} {m[2]}% {m[3]}%, exact conversion is {exp_s}"
                )

    # --- 4. semantic references resolve, and json agrees -------------------
    for ref in sorted(set(VAR_REF_RE.findall(css))):
        if ref not in css_raw:
            fail(f"tokens.css references var(--gt-{ref}), which is not a defined raw token")

    css_sem_alias = dict(SEM_VAR_RE.findall(css))
    for name, ref in sorted(css_sem_alias.items()):
        entry = json_sem.get(name)
        if not isinstance(entry, dict):
            continue
        json_ref = entry.get("ref")
        if json_ref is not None and json_ref != ref:
            fail(
                f"semantic '{name}': tokens.css aliases --gt-{ref} but "
                f"tokens.json records ref '{json_ref}'"
            )
        json_value = str(entry.get("value", "")).upper()
        expected_value = css_raw.get(ref, "").upper()
        if json_value and expected_value and json_value != expected_value:
            fail(
                f"semantic '{name}': tokens.json value {json_value} does not equal "
                f"raw '{ref}' hex {expected_value}"
            )

    # Every JSON semantic entry that mirrors a DIRECT css alias must name a raw
    # token that exists. Computed tokens are exempt: where tokens.css derives a
    # value via color-mix(), tokens.json records `ref` as a human description of
    # the mix ("teal 12% on white") rather than a raw token name. That is the
    # file's convention for derived values, not a dangling reference.
    for name, entry in sorted(json_sem.items()):
        if isinstance(entry, dict) and name in css_sem_alias:
            ref = entry.get("ref")
            if ref is not None and ref not in css_raw:
                fail(f"semantic '{name}': tokens.json refs raw '{ref}', which tokens.css does not define")

    # --- 5. mirrored non-color values agree --------------------------------
    css_decls = {n: v.strip() for n, v in DECL_RE.findall(css)}

    for prop, path in sorted(SCALE_MAP.items()):
        css_value = css_decls.get(prop)
        if css_value is None:
            fail(f"tokens.css is missing the '--{prop}' declaration that tokens.json mirrors")
            continue
        json_value = dig(data, path)
        if json_value is None:
            fail(f"tokens.json is missing {'.'.join(path)}, the mirror of --{prop}")
        elif str(json_value).strip() != css_value:
            fail(
                f"--{prop}: tokens.css '{css_value}' != tokens.json "
                f"{'.'.join(path)} '{json_value}'"
            )

    for role in TYPE_ROLES:
        scale = dig(data, ("typography", "scale", role))
        if scale is None:
            fail(f"tokens.json is missing typography.scale.{role}")
            continue
        for field in ("size", "leading", "weight"):
            css_value = css_decls.get(f"type-{role}-{field}")
            if css_value is None:
                fail(f"tokens.css is missing --type-{role}-{field}")
                continue
            json_value = str(scale.get(field, "")).strip()
            if json_value != css_value:
                fail(
                    f"--type-{role}-{field}: tokens.css '{css_value}' != "
                    f"tokens.json typography.scale.{role}.{field} '{json_value}'"
                )
        # `family` is stored by family KEY in json (e.g. "mono"), and as a
        # var(--font-*) reference in css. Compare after normalising.
        css_family = css_decls.get(f"type-{role}-family", "")
        m = re.match(r"^var\(--font-([a-z-]+)\)$", css_family)
        if not m:
            fail(f"--type-{role}-family: expected a var(--font-*) reference, got '{css_family}'")
        elif str(scale.get("family", "")).strip() != m[1]:
            fail(
                f"--type-{role}-family: tokens.css names font '{m[1]}' but "
                f"tokens.json typography.scale.{role}.family is '{scale.get('family')}'"
            )

    if failures:
        print(f"FAIL: {len(failures)} design-token contract violation(s)\n", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)
        print(
            "\nThis repo is the estate SSOT: consumers byte-vendor these files, so a "
            "violation here reaches every consumer with their drift-checks still green.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK — design-token contract valid: {len(css_raw)} raw tokens "
        f"(css/json hex parity, hsl mirrors exact), {len(css_sem_alias)} semantic "
        f"aliases resolved, {len(SCALE_MAP)} scale values and "
        f"{len(TYPE_ROLES)} type roles mirrored."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
