# Door access pilot

Face AI runs as a local **door access kiosk**. A person can be authorized with
a live face, a personal PIN, an RFID/NFC card adapter, or an authenticated
administrator. Every method goes through the same person, door, schedule and
credential policy, and every decision is written to a local audit trail.

This is a local-first pilot. It deliberately separates the simulated relay from
physical hardware, and it refuses to pretend that optional hardware or
liveness providers exist.

## Architecture

```
Kivy kiosk
  ├─ face detection + recognition (ONNX, local)
  ├─ PIN verification (PBKDF2-HMAC-SHA256, local SQLite)
  ├─ RFID/NFC adapter boundary (none / keyboard-wedge)
  ├─ administrator assistance (role + PIN + reason, optional approver)
  ├─ access registry + credentials + policy (SQLite)
  ├─ snapshots for face events only       outputs/access/
  ├─ access + administrative audit trail  access.db
  └─ door controller                     config/doors.json
       ├─ simulated  (local pilot only)
       └─ webhook    (signed HTTPS POST, secret required)
```

### Data model

| Table | Contents |
| --- | --- |
| `people` | identity, role, department, allowed doors, active flag, photo, schedule, salted PIN hash and lockout state |
| `face_templates` | one or more normalized face embeddings per person |
| `card_credentials` | card UID (unique), status (`active`/`revoked`/`lost`), validity, note |
| `access_events` | timestamp, person, door, method, credential reference, score, decision, reason, admin/approver, event key |
| `audit_events` | administrative changes: enrollment, PIN/card changes, status changes, admin authentication, controller errors |

Public person records never include the PIN hash, salt or iteration count.
Card references are masked to the last four characters outside the credential
entry form. PINs are never written to logs or exported CSV files.

## Access workflow

1. Start the face engine on Home. PIN and administrator assistance still work
   if the face engine is off; the Access screen says so explicitly.
2. On **Access**, the camera is a compact live panel. **Scan & unlock** uses
   face recognition; **Alternative** opens PIN, card and administrator methods.
3. Every decision passes the policy chain below. The result card shows the
   outcome, reason, person, method, door and time; the recent-activity list
   shows timestamp, person/credential, method and outcome.
4. The controller card states whether the relay is **simulated**, **verified**,
   **unverified** or **disconnected**, and shows the fail mode and reader status.

### Policy chain

All methods check, in order:

1. door method is enabled (`allowed_methods`)
2. the person exists and is active (suspended people are denied)
3. the person's allowed-door list contains this door
4. the person's access days and hours allow the current local time
5. the door's open days and hours allow the current local time
6. method-specific credential state:
   - face: configured threshold, exactly one face, face template exists
   - PIN: enrolled, not revoked, not locked, hash comparison succeeds
   - card: reader available, card active, in validity window, person policy
   - administrator: active admin role, valid admin PIN, reason, optional approver
7. duplicate/cooldown check, then the controller call

A backup method cannot turn a suspended or revoked card into an active one.
Two-factor doors require face/card **plus** PIN; PIN alone is refused. Refusals
are recorded as denied events and the UI does not silently fall back to a
weaker method.

### Two-factor doors

Set `"require_two_factor": true` in `config/doors.json`. Face or card returns a
single-use challenge valid for 120 seconds. The kiosk asks for the same
person's PIN, then grants through the normal policy and controller path. The
challenge and final decision are both logged.

## PIN credentials

- 4–8 digits, entered in a password field and never displayed.
- Stored as PBKDF2-HMAC-SHA256 with a random 16-byte salt and 200,000
  iterations. Verification uses `hmac.compare_digest`.
- Failed attempts and `pin_locked_until` are stored per person. The door
  config controls `pin_max_attempts` and `pin_lockout_seconds`.
- Unknown staff IDs get an in-memory throttle so the kiosk does not become an
  enumeration oracle.
- Administrators can set, reset and revoke PINs from **People**. Revoking a PIN
  leaves the person's face/card credentials untouched unless they are separately
  revoked. The last active administrator PIN cannot be revoked, suspended or
  deleted.

## RFID / NFC card credentials

The adapter boundary is in `services/access.py`:

| Adapter | Behaviour |
| --- | --- |
| `none` | Card method is **unavailable**. The UI says no reader is connected and cannot accept a card. |
| `keyboard_wedge` | An external USB/keyboard-wedge reader is configured. Its UID is entered in the card dialog; card authentication is enabled. |

There is no fabricated RFID/NFC driver. Card authentication without a
configured reader returns `unavailable`, never a simulated grant. Card UIDs
are normalized, unique, admin-enrolled, and support expiry, revocation and a
distinct `lost` state. Marking a card lost revokes it immediately.

## Administrator assistance

Administrator assistance is a deliberate, audited method, not an unrestricted
override. It requires:

- an active person whose role is in `admin_roles` (`admin`, `security` by default)
- that administrator's PIN
- a recorded reason of at least 5 characters
- the subject to pass the normal active/door/schedule policy
- the subject not to be PIN-locked
- no self-authorization (the administrator cannot assist themselves)
- a second, different administrator when `admin_second_approver` is true

The access event records the administrator, subject, reason and approver. The
UI exposes it only under **Alternative access → ADMIN**. `/People` management
actions also require an administrator PIN; the PIN is used for that one dialog
and is not stored in application state.

### First administrator

Before any administrator PIN exists, the People page shows a setup banner:

- **SET PIN** assigns a PIN to an existing person whose role is `admin`/`security`.
- **REGISTER** registers a new administrator (with a face) and its PIN.

After that, all credential and person mutations require administrator
authorization. Initial provisioning is a local trust decision: anyone with
physical access before the first administrator exists can perform it.

## Registration

Registration is a modal, not a section of the Access page. **Access → register
icon** or **People → register icon** opens it. From People, the app first moves
to Access so the one shared camera can be used.

The form captures full name, staff/resident ID, role, department/zone, allowed
doors, access days, start/end times, and an optional PIN with confirmation.
Exactly one frontal face is required. Registration is admin-authorized once an
administrator PIN exists. Cancelling closes the modal without registering.

## People workspace

- Search by name, ID, role or department; filter by all/active/suspended/no face.
- Each row shows identity, credentials (`FACE`, `PIN`, `CARDS`) and status.
- Selecting a row opens an administrator-authorized person sheet with access
  policy (doors, days, hours), face enrollment, PIN set/reset/revoke, card
  enrollment, lost/revoke actions, suspend/activate, edit and delete.
- The access log and administrative audit are visible below the directory.
- All changes are real SQLite changes; there is no mock directory.

## Door configuration

`config/doors.json` is created on first launch and is written with mode `0600`.
Edit it from **Settings → Door controller config**, then **Reload**.

```json
{
  "door_id": "main-gate",
  "door_name": "Main Gate",
  "controller": "simulated",
  "webhook_url": "",
  "secret": "",
  "threshold": 0.65,
  "cooldown_seconds": 3,
  "allowed_methods": ["face", "pin", "card", "admin"],
  "require_two_factor": false,
  "pin_max_attempts": 5,
  "pin_lockout_seconds": 300,
  "card_reader": "none",
  "liveness_provider": "none",
  "fail_mode": "fail_secure",
  "admin_roles": ["admin", "security"],
  "admin_second_approver": false,
  "open_start": "00:00",
  "open_end": "23:59",
  "open_days": "0,1,2,3,4,5,6"
}
```

`open_days` uses Python weekday numbering (`0` = Monday). `open_start`/`end`
cross midnight when start is later than end. `fail_mode` is a site decision;
this app only displays it and never auto-opens because of it.

### Real hardware (webhook)

`controller: "webhook"` is the real-hardware boundary. It requires both a
`webhook_url` and a non-empty `secret`; without a secret the kiosk reports the
controller as unverified and refuses the unlock call. Physical URLs must use
HTTPS; `http://127.0.0.1` and `http://localhost` are allowed only for local
testing. The request includes:

```http
POST <webhook_url>
Content-Type: application/json
X-FaceAI-Event-ID: <unique event key>
X-FaceAI-Signature: <hex HMAC-SHA256 of the body using secret>
```

The response must be `2xx` within 5 seconds. Non-2xx, timeout and connection
errors are reported to the UI and logged as `error`; the door is not opened.
Duplicate event keys and the cooldown are rejected in memory. There are no
automatic retries, because an access event must never open a door twice.

**Physical face access is blocked in this build.** A webhook controller has no
certified liveness provider; `DoorController.face_access_state()` returns
disabled and the Access screen explains why. Face access works only against the
explicit `simulated` relay, where the UI labels it a pilot and does not claim
identity proof. Do not connect a physical door to the simulated relay.

## Tests

From `face-ai/app`:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

The suite uses a fake face engine and a temporary SQLite database. It covers
face grant/deny, PIN hashing and lockout, PIN revocation, card grant/expiry/
lost/revoked/unavailable, door permissions and schedules, two-factor
challenges, administrator assistance, second approvers, self-approval denial,
last-administrator protection, unknown-credential disclosure, controller
failure, duplicate event keys, cooldown, masked export and audit actions.

## Remaining production gaps

- No certified liveness/anti-spoofing provider is integrated. Physical face
  access is therefore blocked rather than simulated.
- No RFID/NFC hardware protocol is implemented. The keyboard-wedge adapter is a
  UID input boundary; a vendor SDK adapter and hardware test are still needed.
- The webhook controller has not been tested against a real relay or door.
- Snapshots and embeddings remain unencrypted at rest. Encrypt the volume,
  restrict permissions and define biometric retention.
- No central multi-door sync/aggregation or revocation propagation yet.
- Only macOS was runtime-tested for this UI pass; Android, iOS, Windows and
  Linux need target smoke tests, especially camera and safe-area behaviour.
- The app is not hardened as an unattended kiosk OS session; add auto-start,
  OS lockdown, watchdog monitoring, backups and an emergency manual release.
