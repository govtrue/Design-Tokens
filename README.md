# govtrue-design-tokens

**Single source of truth** for GovTrue's authenticated product-shell design
system: navy app shell, warm-white workspace, cream/white cards, a teal accent,
Inter, a 4px spacing scale, 10/14/20px radii, warm navy-tinted shadows. Light
mode only.

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

```
# in a consumer repo
node scripts/sync-design-tokens.mjs    # fetch pinned tag -> overwrite vendored copy
node scripts/check-design-tokens.mjs   # CI: assert vendored copy == pinned tag
```

## Token groups

| Group | Tokens |
|-------|--------|
| Surfaces | `--surface-shell`, `--surface-shell-raised`, `--surface-workspace`, `--surface-card`, `--border-hairline` |
| Actions | `--action-primary`, `--action-primary-hover`, `--action-primary-press` |
| Accent | `--accent` (active/links) |
| Citation | `--accent-citation`, `--accent-citation-surface`, `--accent-citation-hover` — render only on federated citation surfaces (Codify, Archive), not Platform |
| Text | `--text-body`, `--text-muted` |
| On-navy | `--on-navy`, `--on-navy-muted`, `--on-navy-accent` (AA-verified on navy + raised navy) |
| Chips | `--chip-on-navy-*`, `--chip-on-light-*` |
| Scale / radii / shadow / motion | `--space-*`, `--radius-*`, `--shadow-*`, `--dur-*`, `--ease-*` |

Light mode only — consumers' `.dark` blocks stay dormant; the contract is not
expanded to dark.

## Accessibility (WCAG AA, verified against the actual backing surface)

| Foreground | on `#0B1F3A` (shell) | on `#142A4C` (shell-raised) |
|------------|----------------------|------------------------------|
| `--on-navy` `#FAFAF7` | 15.80:1 | — |
| `--on-navy-muted` `#9AA6BD` | 6.74:1 | 5.84:1 |
| `--on-navy-accent` `#3DBE96` | 7.08:1 | 6.14:1 |

All pass AA for normal text (≥ 4.5:1). `teal-deep` is illegible on navy — the
shell uses `--on-navy-accent` for teal cues.
