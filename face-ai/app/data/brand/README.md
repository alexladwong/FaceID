# Face AI brand assets

This directory is the single source of truth for Face AI launcher and
application branding. Supplied artwork was normalized from the extracted
`Face_AI_Modified_Assets` package. The archive itself is intentionally not
committed.

## Canonical files

| File | Size | Purpose |
| --- | --- | --- |
| `faceai-logo.png` | 512×512 RGBA | Primary logo, sidebar/header mark, README artwork, desktop window icon source |
| `faceai.ico` | 16–256 px, 7 embedded sizes | Windows executable icon; PyInstaller fallback |
| `faceai.icns` | macOS icon family | macOS bundle/dock icon generated from `faceai-logo.png` |
| `presplash.png` | 1024×1024 RGB | Android/iOS launch artwork, generated on the coordinated `#0E1438` navy |
| `adaptive-foreground.png` | 512×512 RGBA | Android adaptive foreground; alpha bbox 86–426 px, inside the central safe zone |
| `adaptive-background.png` | 512×512 RGB | Android adaptive background; supplied coordinated navy/indigo artwork |

The original supplied names mapped as follows:

- `favicon.png` → `faceai-logo.png`
- `favicon.ico` → `faceai.ico`
- `icon_fg.png` → `adaptive-foreground.png`
- `icon_bg.png` → `adaptive-background.png`
- `favicon(1).png` and `favicon-1.png` were byte-identical duplicates of the
  primary logo, were not referenced anywhere, and were removed.

## Rules

- Use `faceai-logo.png` only for brand slots (rail/drawer lockup, compact rail,
  phone context bar, README). Do not replace action, navigation, status or
  control icons with the full logo.
- Use the MDI icon set for interface meaning. Brand artwork never substitutes
  for a semantic icon.
- `adaptive-background.png` is a launcher layer, not a page background.
- Screens keep the existing themed navy/indigo/light surfaces. No decorative
  gradients or full-screen logo backgrounds.
- Platform builders derive launcher densities and splash variants from these
  canonical files; do not hand-maintain density-specific copies.
