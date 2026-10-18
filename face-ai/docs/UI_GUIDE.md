# Face AI interface guide

Face AI is a native **Kivy + KivyMD** application. There is no web view or
browser shell: the same Python UI runs on macOS, Windows, Linux, Android and
iOS, with native file pickers and camera access via platform services.

## Structure

```
app/main.py              app state, routing, services, dialogs, toasts
app/main_layout.kv       app bar, navigation rail, drawer, screen manager
app/screens/palette.py   observable light/dark design tokens
app/screens/ui.py        shared cards, pills, banners, uploads, empty states
app/screens/*.py         one module per screen + its kv rules
app/services/            face engine, vault, door access (no UI here)
```

## Design tokens

`screens/palette.py` exposes a single observable `theme` object. Screens bind
to `theme.<token>` in kv, so switching themes updates existing widgets. Never
add a raw light-only colour to a screen.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `primary` | `#4F46E5` | `#4F46E5` | filled buttons, app bar, hero |
| `primary_text` | `#4F46E5` | `#B0B4FF` | links/icons on surfaces |
| `primary_soft` | `#EEF2FF` | `#232544` | selected nav, tinted badges |
| `surface` | `#F5F6FA` | `#0E1117` | page background |
| `card` | `#FFFFFF` | `#171B24` | cards, rail, drawer |
| `line` | `#E4E7F0` | `#2A3040` | borders and dividers |
| `text` / `muted` | `#151A24` / `#667085` | `#F2F4F8` / `#9AA4B2` | copy hierarchy |
| `success` / `warning` / `error` | green / amber / red | brighter variants | status only |

Typography uses KivyMD's Roboto scale with `sp()`; spacing and radii use `dp()`.
Existing components: `AppCard`, `IconBadge`, `Pill`, `StatusPill`,
`FeatureChip`, `InfoBanner`, `EmptyState`, `BusyState`, `UploadTile`,
`ResultPane`, `RecentTile`, `SettingsRow`.

## Responsive rules

- Breakpoint: `app.is_wide` is true at **980 px** and above.
- Wide: 232 px rail, or a 76 px icon-only rail via the app-bar chevron.
- Narrow: rail slides off-screen; hamburger opens a 232 px drawer with a scrim.
  Escape, the scrim, or navigating closes it.
- Two-column content (vault auth and Face Finder) becomes one column.
- Page padding is 24/18 on wide and 16-24 on phones; all long pages scroll.
- Upload tiles and result panes stack vertically under the breakpoint.
- The Face Finder status pill and page-level status pills collapse on phones;
  the engine state remains visible in the step line and warning banner.

## States and feedback

- Engine, model, vault, and door statuses use live app properties. Vault shows
  `Locked` unless the current session has been unlocked; leaving the vault
  locks it again.
- Routine success uses the compact toast. Errors stay for at least 6 seconds
  and errors that need action also appear inline (for example Face Finder
  failure states).
- Loading: busy bars/spinners on upload tiles, match panes, and vault/door
  operations.
- Empty: purpose-written empty states, never mock data.
- Disabled: primary actions disable while their operation runs.

## Themes and motion

- The app bar moon/sun button and **Settings → Appearance** switch light/dark.
  The preference is stored in `config/preferences.json`.
- **Reduce motion** disables drawer, toast and screen-transition animations.
  The setting is stored in the same file.
- Status colours are reserved for state, never decoration.

## Keyboard and accessibility

- `Ctrl/Cmd+1..6`: Home, Access, People, Face Finder, Vault, Settings.
- `Ctrl/Cmd+O`: pick a Face Finder image.
- `Ctrl/Cmd+R`: reset Face Finder.
- `Ctrl/Cmd+L`: lock the vault.
- `Esc`: close the drawer or an open dialog.
- Text fields and navigation items have visible focus/pressed states from
  KivyMD. Full screen-reader labelling is not implemented; see the remaining
  gaps in the project report.

## Platform notes

- Camera: AVFoundation on macOS, standard Kivy providers elsewhere; Android
  adds cutout/safe-area padding.
- File selection: `plyer` native pickers; drag/drop is enabled only on desktop
  (`Window.on_drop_file`).
- Vault encryption is unchanged: Fernet-encrypted files on non-Android, app
  private storage on Android. The UI only lists metadata and never logs keys.
- Window sizing is applied only on desktop; phones run fullscreen.

## Verification matrix used for this redesign

| Viewport | Light | Dark | Screens checked |
| --- | --- | --- | --- |
| 1200 × 820 (desktop) | yes | yes | Home, Face Finder, Vault, Settings, Access, People |
| 760 × 820 (small laptop/tablet) | yes | yes | shell, drawer, Face Finder, Home |
| 420 × 820 (large phone) | yes | yes | Home, drawer, dialogs, Face Finder |
| 360 × 800 (phone) | yes | yes | Home, Face Finder, Access, People, dialogs |

Only macOS was available for runtime testing in this environment. Android,
iOS, Windows and Linux builds must be smoke-tested on their targets before a
release; the responsive code paths are platform-neutral but camera/file-picker
behaviour is provider-specific.
