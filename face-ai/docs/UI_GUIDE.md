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

## Shell and navigation

- The 248 px rail runs the full window height, with the product mark and
  grouped destinations: Workspace, Face tools, Door access, System.
- The active destination has a filled indigo surface plus a 3 px accent bar;
  destinations are never identified by text colour alone.
- The rail collapses to an 80 px icon rail with tooltips. The chevron in the
  brand row collapses it; the chevron in the icon rail restores it.
- From 760–979 px the compact 80 px rail stays visible so a normal desktop
  window never loses navigation. Below 760 px the rail slides away; the
  context-bar menu opens the same grouped navigation as a 248 px drawer with a
  scrim and an explicit close button. Escape, the scrim, or choosing a
  destination closes it.
- Navigation items act on release, not press, so dragging/scrolling the rail
  does not change screens. The context bar always shows the current page title,
  including on phones; the product mark lives in the rail/drawer.
- The navigation list scrolls independently on short screens, with privacy and
  version anchored at the bottom.
- The neutral 58 px context bar carries the current workspace label, live
  engine state, theme and help. It replaces the old full-width indigo app bar.

## Responsive rules

- Layout breakpoint: `app.is_wide` is true at **980 px** and above. A separate
  navigation breakpoint keeps the compact rail visible down to **760 px**.
- Desktop windows are snapped to even dimensions before layout. The SDL/OpenGL
  surface on macOS shears at odd logical widths; this keeps resizing clean.
- Two-column content (vault auth, Face Finder and Access camera/actions)
  becomes one column.
- The Access camera preview shrinks on phones so the primary actions and result
  stay near the top of the page rather than below a tall preview.
- Page padding is 24/18 on wide and 16-24 on phones; all long pages scroll.
- Upload tiles and result panes stack vertically under the breakpoint.
- The dashboard quick-action grid is 4 columns on desktop, 2 on phones and 1
  column below 360 px.
- Phone context bars show the product mark, engine state, theme and help; the
  large page title lives in the page body so it never has to wrap in the bar.

## Screen patterns

- Home is a command centre: one engine card with real model/engine/vault/data
  values, then a quick-action grid, recent matches and the privacy row. It is
  not a hero billboard.
- Face Finder uses a four-segment progress strip (Source, Target, Match,
  Results) tied to `app.match_step_index`; the active segment is filled and the
  redundant tip banner and duplicate engine pills were removed.
- Secure Vault shows a dedicated page header, a centred locked/enrolment state
  when the engine is off, and the existing face-auth or encrypted file list
  when it is running.
- Door Access leads with a compact live camera, then the two primary actions
  (**Scan & unlock**, **Alternative**), a compact result card and the controller
  card. Registration is a modal; it is never embedded in the Access page.
- Alternative access is a focused dialog with PIN, card and administrator
  options. PIN/card fields are password/UID forms; administrator assistance
  records a reason and optional second approver. Two-factor doors open a
  single-use PIN challenge.
- People is a searchable directory with credential badges and status, followed
  by access and administrative audit logs. Row actions open an
  administrator-authorized person sheet for enrollment, PIN, cards, policy,
  suspension and deletion.
- Dialogs use a custom scrollable form when they contain fields. Content is
  measured from the fields, not a fixed height, so short PIN forms stay compact
  and the registration form scrolls on a phone. Cancel is always present.

## Interaction integrity

- The mobile drawer scrim only exists — including its hit area — while the
  drawer is open. `MDCard` is a `ButtonBehavior`, so an opacity-0/disabled
  full-screen scrim still swallows every pointer event. Closed scrims get zero
  size; this was the cause of the app appearing completely unresponsive.
- The labelled rail, compact rail and drawer share one panel. Hidden variants
  are disabled and their `on_touch_down` returns `False`, so hidden children
  cannot steal a click from the visible navigation.
- Dialogs and file pickers are modal only while open; dismissing one restores
  interaction with the page underneath. The closed-drawer scrim and hidden
  navigation variants are covered by real-pointer regression tests.
- Camera attach failures render an inline `CameraCard.show_error` state with
  the reason and a retry control; a machine with no camera no longer crashes
  the vault or Access screen. This path is covered by the pointer test.
- Home exposes both **Start face engine** and **Stop face engine**. Stopping
  tears down the camera, engine service handles, vault session and Access face
  capability; it does not merely change a badge.

## States and feedback

- Engine, model, vault, and door statuses use live app properties. Vault shows
  `Locked` unless the current session has been unlocked; leaving the vault
  locks it again. Stopping the engine locks the vault and disables face access.
- Routine success uses the compact toast. Errors stay for at least 6 seconds
  and errors that need action also appear inline (for example Face Finder
  failure states).
- Loading: busy bars/spinners on upload tiles, match panes, and vault/door
  operations. Vault encryption runs off the UI thread; the Upload button shows
  `Working...` while busy and the file list refreshes on completion.
- Empty: purpose-written empty states, never mock data.
- Disabled: primary actions disable while their operation runs. Face scan is
  disabled when the engine or the door's face policy is unavailable; the
  Alternative button remains available.
- Door and credential outcomes use `granted`, `denied`, `error`, `unavailable`
  and `challenge` states with distinct icon/colour. Unknown face/PIN attempts
  are not attributed to a person; card references are masked.
- Registration and management forms show validation inline as a toast and keep
  the dialog open for correction. Successful actions refresh the registry,
  logs and audit.

## Themes and motion

- The context-bar moon/sun button and **Settings → Appearance** switch light/dark.
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
  KivyMD. The register, manage and export icon actions have tooltips.
- `Ctrl/Cmd+1..6` navigation is tested with actual key dispatch, not just a
  direct handler call.
- Access/People actions use 42–48 px touch targets. Credential fields are
  password fields for PINs and never display a stored PIN.
- Full screen-reader labelling and a complete keyboard focus order for every
  custom row are not implemented; see the remaining gaps in
  [`ACCESS_PILOT.md`](ACCESS_PILOT.md).

## Platform notes

- Camera: AVFoundation on macOS, standard Kivy providers elsewhere; Android
  adds cutout/safe-area padding.
- File selection: `plyer` native pickers; drag/drop is enabled only on desktop
  (`Window.on_drop_file`).
- Vault encryption is unchanged: Fernet-encrypted files on non-Android, app
  private storage on Android. The UI only lists metadata and never logs keys.
- Camera widgets are reused and stopped on a short delay instead of being
  destroyed on every route change. This avoids AVFoundation crashes when the
  user moves between Access and other sections while the camera is starting.
- Window sizing is applied only on desktop; phones run fullscreen.

## Verification matrix used for this redesign

| Viewport | Light | Dark | Screens checked |
| --- | --- | --- | --- |
| 1200 × 820 (desktop) | yes | yes | Home, Face Finder, Vault, Settings, Access, People, registration, alternative access, person sheet |
| 800 × 700 (small desktop window) | yes | yes | compact rail, Access, page title |
| 760 × 820 (small laptop/tablet) | yes | yes | compact rail, shell, Home |
| 756 × 700 (drawer threshold) | yes | yes | drawer, scrim, destination change |
| 420 × 820 (large phone) | yes | yes | Home, drawer, dialogs, Face Finder |
| 360 × 800 (phone) | yes | yes | Home, Face Finder, Access, People, Settings, vault, registration, administrator PIN setup |
| 320 × 700 (small phone) | yes | yes | Home, shell, quick actions |

### Interaction test

```bash
cd app
FACEAI_UI_TESTS=1 ./.venv/bin/python -m unittest tests.test_ui_interactions -v
```

The desktop-only test dispatches real mouse down/up events through `Window`.
It covers navigation, quick actions, theme/help, engine start/stop, Access
dialogs and registration, People filters, Settings confirmation, compact rail,
drawer scrim, keyboard shortcuts, vault upload/download/delete and Face Finder
image selection/matching. It is skipped in headless CI unless the environment
variable is set.

Only macOS was available for runtime testing in this environment. Android,
iOS, Windows and Linux builds must be smoke-tested on their targets before a
release; the responsive code paths are platform-neutral but camera/file-picker
behaviour is provider-specific.
