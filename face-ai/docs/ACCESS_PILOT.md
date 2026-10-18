# Door access pilot

Face AI can run as a local **door access kiosk**: an operator registers people
with their details, the kiosk matches a live face against the local registry,
and a granted match calls a door controller and writes an audit event.

This document describes exactly what is implemented, how to connect a door,
and what must be fixed before a real deployment.

## Architecture

```
Kiosk (this Kivy app)
  ├─ face detection + recognition (ONNX, local)
  ├─ access registry (SQLite)      app data: databases/access.db
  ├─ face templates (embeddings)   same database, face_templates table
  ├─ snapshots                      app data: outputs/access/
  ├─ audit trail                    access_events table, CSV export
  └─ door controller                config/doors.json
                                     ├─ simulated  (pilot default)
                                     └─ webhook    (HTTP POST + HMAC)
```

The kiosk is local-first: recognition, registration and logs work without a
network. Only the optional webhook call needs the controller/network.

## Data

| Table | Contents |
| --- | --- |
| `people` | full name, staff/resident ID, role, department/zone, allowed doors, active flag, photo path |
| `face_templates` | one or more normalized ArcFace embeddings per person |
| `access_events` | timestamp, person, door, cosine score, granted/denied/error, reason, snapshot |

`allowed doors` is `all`/`*`, empty, or a comma-separated list of door ids.
The kiosk checks the person's permission against the configured door id.

## Register a person

1. Start the face engine on Home.
2. Open **Access → Register person** (or **People → Register someone**).
3. Fill in full name (required), staff/resident ID, role, department/zone and
   allowed doors. `all` means every door.
4. Frame exactly one face and press **Capture & register face**.
   A second face in the frame is rejected on purpose (ambiguous identity).
5. The person and template appear under **People**; every enrollment is logged
   with a snapshot in `outputs/access/`.

## Scan (unlock)

1. On **Access**, frame one face and press **Scan & unlock**.
2. A match is granted only when all of these hold:
   - best cosine similarity ≥ `threshold` in `config/doors.json`
   - the person is active
   - the person's `allowed doors` includes this door
   - the cooldown between grants has elapsed
3. A granted match calls the door controller, then writes an audit event.
   If the controller fails, the event is recorded as `error` and the UI says so.
4. Unknown faces are **not** attributed to a person in the log; only the score
   and the anonymized event are stored.

## Door configuration

`config/doors.json` (created on first launch, editable from Settings → Door
controller config, then **Reload door config**):

```json
{
  "door_id": "main-gate",
  "door_name": "Main Gate",
  "controller": "simulated",
  "webhook_url": "",
  "secret": "",
  "threshold": 0.65,
  "cooldown_seconds": 3
}
```

`controller` is `simulated` (relay pulse only, for demos) or `webhook`.

### Webhook contract

When a match is granted the kiosk sends:

```http
POST <webhook_url>
Content-Type: application/json
X-FaceAI-Signature: <hex HMAC-SHA256 of the body using `secret`>
```

```json
{
  "ts": "2026-10-18 12:00:01",
  "door_id": "main-gate",
  "door_name": "Main Gate",
  "person_id": 12,
  "person_name": "Jane Doe",
  "score": 0.8123,
  "decision": "granted",
  "reason": "Face matched and door permission granted",
  "snapshot_path": "/.../outputs/access/access_....jpg"
}
```

The controller (or a small relay bridge: ESP32, Raspberry Pi, PLC) should
verify the signature, check `door_id`, drive the relay for a few seconds and
return `2xx`. The kiosk treats any non-2xx or timeout as a failure and logs an
`error` event. There are no retries by design: an access event must not open a
door twice due to a network retry.

The webhook adapter is the pilot integration point. A vendor controller can be
added in `services/access.py` (`DoorController.unlock`) without touching the UI.

## Before a real deployment (required)

This pilot is **face matching only**. It is not yet a security system:

- **Liveness / anti-spoofing.** A printed or on-screen photo of an enrolled
  person can currently match. Do not connect a real door until a certified
  liveness check (or face + PIN/QR second factor) is enforced for every grant.
- **Threshold and quality gates.** Add face-size, blur and pose checks; tune the
  threshold on site with real people and report false accept/reject rates.
- **Embeddings and snapshots at rest.** SQLite stores embeddings and JPEG
  snapshots in clear. Encrypt the database/at-rest volume and restrict file
  permissions; define retention for snapshots.
- **Legal/consent.** Biometric data is sensitive personal data in most
  jurisdictions. Run a DPIA, obtain consent or a valid legal basis, publish a
  retention policy, and document the operator/admin roles.
- **Admin authentication and RBAC.** The current app has no login for the
  operator. Add an admin PIN/account, protect People/Access exports, and audit
  changes to the registry.
- **Physical fail-safe.** The door must fail safely on power/network loss, with
  a manual release and an emergency override; the webhook bridge should be a
  separate watchdog process.
- **Kiosk hardening.** Auto-start in kiosk mode, disable OS shortcuts, pin the
  DB/config paths, back up the registry, and monitor disk space.
- **Multi-door deployment.** One kiosk per door with a central sync/aggregation
  service (people updates + audit uploads) is the next step; the local schema
  already supports per-door permissions and offline grants.

## Tested flows

- Registration from a clear single-face frame.
- Grant with details shown (`name`, `role`, `department`, `score`, `door`, time).
- Denial for an unknown face, below-threshold match, inactive/forbidden person
  and cooldown.
- Simulated relay grant.
- Webhook grant with HMAC signature (local HTTP test server).
- Audit log stored and exported to CSV.
- People registry list and delete.
