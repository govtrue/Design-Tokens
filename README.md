# govtrue-design-tokens

**Single source of truth** for GovTrue's authenticated product-shell design
system: navy app shell, warm-white workspace, cream/white cards, a teal accent,
Inter, a 4px spacing scale, 10/14/20px radii, warm navy-tinted shadows. Light
mode only. It also carries the **legal-document type scale** (font families +
per-role typography) for the federated citation/document surfaces — the Codify
public code portal that renders the law as a typeset document.

This repo is **colors + type only** — no components, no build step, no IP — so it
is public, which lets consumer repos vendor it with **zero build-time
authentication** (the failure mode that killed the earlier private `@govtrue/ui`
package in Cloud Build).

## Files

- **`tokens.css`** — the authoritative artifact. CSS custom properties in two
  layers: a **raw** palette (authoritative hex + exact `*-hsl` mirrors) and a
  **semantic** layer that components consume.
- **`tokens.json`** — a data mirror for non-CSS consumers / tooling.

## The one rule

Components reference **semantic tokens only** (`--surface-shell`,
`--action-primary`, `--accent`, `--text-body`, `--accent-citation`, …) — never
the raw `--gt-*` palette.

Two consumption styles are supported by design:
- **shadcn/ui apps** (Platform, Archive) bridge their `hsl(var(--token))`
  component tokens to the semantic layer via the raw `*-hsl` mirrors.
- **non-shadcn apps** (Codify) consume the **hex semantic tokens directly**
  (`var(--surface-card)`, `text-[var(--accent-citation)]`, …) — the `*-hsl`
  mirrors are simply unused there.

## Distribution: vendor + drift-check against an immutable tag

This package is **not** installed at build time. Each consumer **vendors a
byte-identical copy** of `tokens.css` + `tokens.json` into its repo (e.g.
`src/theme/` or `lib/design-tokens/`) and pins an **immutable version tag** in a
`VERSION` file. A CI drift-check re-fetches that pinned tag's raw files and fails
the build if the vendored copy diverges.

**Immutable tags only.** Every token change cuts a **new** tag
(`v1.0.0 → v1.1.0 → …`). Tags are **never moved or re-pointed**, and there is no
moving `latest` tag — a moving tag could flip a consumer's CI red with no local
change, or mask real drift. To roll a change out: cut the new tag here, then bump
each consumer's `VERSION` and re-run its sync script.

The repository identity change in `tokens.css` changes the authoritative bytes.
Release it as the next immutable tag, `v1.4.1`, after the repository is renamed
to `govtrue/Design-Tokens`. Consumers keep their existing `v1.4.0` copy until
that tag exists, then sync the new files and record the new CSS SHA-256. The
`v1.4.0` tag and its bytes remain historical evidence.

```
# in a consumer repo
node scripts/sync-design-tokens.mjs    # fetch pinned tag -> overwrite vendored copy
node scripts/check-design-tokens.mjs   # CI: assert vendored copy == pinned tag
```

## Contract validation (CI)

The consumer drift-checks above prove *"my vendored copy matches the SSOT."*
Nothing in them proves *the SSOT is internally coherent* — so an incoherent
commit here would propagate to every consumer at the next tag with all of their
drift-checks still green.

`scripts/validate_tokens.py` closes that gap and runs in CI on every push and
pull request. It is stdlib Python, no network, no dependencies — this repo keeps
its no-build-step, no-package-manager posture.

```
python3 scripts/validate_tokens.py
```

It enforces what the files already claim about themselves:

1. `tokens.json` parses and declares the sections consumers read.
2. **Raw parity** — `tokens.css` and `tokens.json` agree on raw token names and
   hex values ("hex values are authoritative").
3. **HSL exactness** — every `--gt-*-hsl` mirror, in both files, is *recomputed*
   from its hex and must match ("the mirror is a derived, exact conversion").
4. **Semantic resolution** — every `var(--gt-*)` resolves to a defined raw token,
   and each JSON semantic entry agrees on both the ref and its hex.
5. **Mirrored non-color values** — spacing, radii, shadows, motion, font families
   and the per-role type scale agree between the two files.

It deliberately does **not** require every `tokens.css` token to appear in
`tokens.json`. `tokens.json` is a *curated* mirror for non-CSS consumers, not a
one-to-one dump — `--chip-*`, for instance, is CSS-only by design. Asserting full
parity would fail on intent rather than on error.

Derived values are handled as such: where `tokens.css` computes a token via
`color-mix()`, `tokens.json` records `ref` as a description of the mix
(`"teal 12% on white"`) rather than a raw token name, and the validator exempts
those from name resolution.

## Token groups

| Group | Tokens |
|-------|--------|
| Surfaces | `--surface-shell`, `--surface-shell-raised`, `--surface-workspace`, `--surface-card`, `--surface-document-meta`, `--border-hairline` |
| Actions | `--action-primary`, `--action-primary-hover`, `--action-primary-press` |
| Accent | `--accent` (active/links) |
| Citation | `--accent-citation`, `--accent-citation-surface`, `--accent-citation-hover` — render only on federated citation surfaces (Codify, Archive), not Platform |
| True | `--accent-true` `#EA580C`, `--accent-true-hover` `#C2410C` — the True assistant activation button (GAX header). Brand orange, deliberately distinct from the warning ramp. Graphical/large-label affordance carrying the on-navy label (~3.4:1 — AA graphical, not small body text) |
| Status / feedback | `--status-{success,warning,danger,info,neutral}-{fg,surface,border}` — light-only. `-fg` is AA-legible text/icon, `-surface` a 12% tint, `-border` the highlight hue. Workflow mapping: danger=overdue, warning=needs-attention, neutral=waiting, success=complete, info=informational |
| Text | `--text-body`, `--text-muted` |
| On-navy | `--on-navy`, `--on-navy-muted`, `--on-navy-accent` (AA-verified on navy + raised navy) |
| Chips | `--chip-on-navy-*`, `--chip-on-light-*` |
| Typography | `--font-serif-reading`, `--font-sans`, `--font-mono`; per-role `--type-*` scale (`section-number`, `catchline`, `body`, `subsection`, `metadata-label`, `breadcrumb`, `toc`) |
| Scale / radii / shadow / motion | `--space-*`, `--radius-*`, `--shadow-*`, `--dur-*`, `--ease-*` |

Light mode only — consumers' `.dark` blocks stay dormant; the contract is not
expanded to dark.

## Typography (legal-document type scale)

Three faces, named so the SSOT — not consumer CSS — owns which face a role uses:
`--font-serif-reading` (the reading face, **Source Serif 4**), `--font-sans`
(Inter, chrome) and `--font-mono` (identifiers). The per-role `--type-*` scale
bakes a face + size + leading + weight into each role (`body`, `catchline`,
`section-number`, `subsection` — serif text with a mono enumerator —,
`metadata-label`, `breadcrumb`, `toc`), so a consumer applies a role rather than
hand-picking a font. **Two weights only** — 400 regular, 500 medium (no 600/700).
Sizes are `rem` (they scale with the user's root font-size).

The reading face is **self-hosted `woff2` by the consumer** (the Codify Phase 2
PR), **not** a CDN — this repo names the family + a Georgia fallback but, per its
no-build/no-IP charter, ships no font files. `--font-serif-reading` degrades to
Georgia until the woff2 loads. Type tokens are not colors, so they carry no `*-hsl`
mirror.

## Accessibility (WCAG AA, verified against the actual backing surface)

| Foreground | on `#0B1F3A` (shell) | on `#142A4C` (shell-raised) |
|------------|----------------------|------------------------------|
| `--on-navy` `#FAFAF7` | 15.80:1 | — |
| `--on-navy-muted` `#9AA6BD` | 6.74:1 | 5.84:1 |
| `--on-navy-accent` `#3DBE96` | 7.08:1 | 6.14:1 |

All pass AA for normal text (≥ 4.5:1). `teal-deep` is illegible on navy — the
shell uses `--on-navy-accent` for teal cues.

Status `-fg` colors are AA as text on **both** white and their own 12% `-surface`
tint; the raw status highlight hue (used by `-border`) is **not** AA as text and
must not be used for text — use `-fg`.

| Status `-fg` | on white | on its `-surface` tint |
|--------------|----------|------------------------|
| `--status-success-fg` `#15673A` | 6.92:1 | 5.96:1 |
| `--status-warning-fg` `#8A5200` | 6.39:1 | 5.51:1 |
| `--status-danger-fg` `#9A1C13` | 8.24:1 | 6.76:1 |
| `--status-info-fg` `#155E9C` | 6.75:1 | 5.74:1 |
| `--status-neutral-fg` `#525252` | 7.81:1 | 6.67:1 |
