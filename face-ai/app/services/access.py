"""Local door access: people, credentials, policy, audit and controllers.

Security model for this pilot:

* PINs are stored only as salted PBKDF2-HMAC-SHA256 hashes.
* Card UIDs are handled by an adapter boundary. With no reader the card
  method is explicitly unavailable rather than simulated.
* Face access is allowed in the simulated pilot only. A webhook controller
  needs a configured liveness provider; this build has none, so face access
  is blocked for physical hardware.
* Every decision goes through the same person/status/door/schedule policy.
* Two-factor doors require face/card + PIN; PIN alone is refused.
* Administrator assistance requires an active administrator credential, a
  reason, and optionally a second different approver.
"""

import csv
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.request

import cv2
import numpy as np

PIN_ITERATIONS = 200_000
METHODS = ("face", "pin", "card", "admin")

DEFAULT_DOOR_CONFIG = {
    "door_id": "main-gate",
    "door_name": "Main Gate",
    "controller": "simulated",  # simulated | webhook
    "webhook_url": "",
    "secret": "",
    "threshold": 0.65,
    "cooldown_seconds": 3,
    "allowed_methods": ["face", "pin", "card", "admin"],
    "require_two_factor": False,
    "pin_max_attempts": 5,
    "pin_lockout_seconds": 300,
    "card_reader": "none",  # none | keyboard_wedge
    "liveness_provider": "none",  # reserved; no verified provider in this build
    "fail_mode": "fail_secure",  # fail_secure | fail_safe; never an automatic open
    "admin_roles": ["admin", "security"],
    "admin_second_approver": False,
    "open_start": "00:00",
    "open_end": "23:59",
    "open_days": "0,1,2,3,4,5,6",
}


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now_dt():
    return datetime.datetime.now()


def _parse_days(value):
    days = set()
    for item in str(value or "").split(","):
        item = item.strip()
        if item.isdigit() and 0 <= int(item) <= 6:
            days.add(int(item))
    return days


def _within_window(start, end, now=None):
    if not _valid_time(start) or not _valid_time(end):
        return False
    now = now or _now_dt().time()
    try:
        sh, sm = [int(x) for x in str(start).split(":")[:2]]
        eh, em = [int(x) for x in str(end).split(":")[:2]]
    except (TypeError, ValueError):
        return False
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    now_min = now.hour * 60 + now.minute
    if start_min == end_min:
        return True
    if start_min < end_min:
        return start_min <= now_min <= end_min
    return now_min >= start_min or now_min <= end_min


def _valid_time(value):
    return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(value or "").strip()))


def _mask_ref(value):
    value = str(value or "")
    return f"**** {value[-4:]}" if len(value) >= 4 else "-"


def _normalize_card_uid(value):
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def _valid_card_uid(value):
    return 4 <= len(value) <= 64 and bool(re.fullmatch(r"[A-Z0-9]+", value))


class CardReaderAdapter:
    """Boundary for a card reader. Implementations must be explicit."""

    name = "none"
    available = False
    requires_manual_entry = False

    def status_text(self):
        return "No card reader connected"

    def read_uid(self):
        raise NotImplementedError("This card reader cannot read cards")


class NullCardReader(CardReaderAdapter):
    def __init__(self, reason="No card reader connected"):
        self.reason = reason

    def status_text(self):
        return self.reason


class KeyboardWedgeCardReader(CardReaderAdapter):
    """A configured USB/keyboard-wedge reader. The UID arrives as text."""

    name = "keyboard_wedge"
    available = True
    requires_manual_entry = True

    def status_text(self):
        return "Keyboard-wedge reader configured (external reader required)"

    def read_uid(self):
        return None


class DoorController:
    """Relay/webhook adapter with explicit health and no fail-open behaviour."""

    def __init__(self, config_path):
        self.config_path = config_path
        self.config = {}
        self.last_success_at = ""
        self.last_error = ""
        self._sent_keys = []
        self._sent_lock = threading.Lock()
        self.reload()

    def reload(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump(DEFAULT_DOOR_CONFIG, f, indent=2)
            try:
                os.chmod(self.config_path, 0o600)
            except OSError:
                pass
        try:
            with open(self.config_path) as f:
                loaded = json.load(f)
        except Exception as e:
            print(f"Could not read door config: {e}")
            loaded = {}
        self.config = {**DEFAULT_DOOR_CONFIG, **loaded}
        self.last_error = ""
        self.last_success_at = ""
        try:
            if os.stat(self.config_path).st_mode & 0o077:
                os.chmod(self.config_path, 0o600)
        except OSError:
            pass
        return self.config

    @property
    def door_id(self):
        return str(self.config.get("door_id", "main-gate"))

    @property
    def door_name(self):
        return str(self.config.get("door_name", "Main Gate"))

    @property
    def controller(self):
        return str(self.config.get("controller", "simulated")).lower()

    @property
    def threshold(self):
        try:
            return float(self.config.get("threshold", 0.65))
        except (TypeError, ValueError):
            return 0.65

    @property
    def cooldown_seconds(self):
        try:
            return float(self.config.get("cooldown_seconds", 3))
        except (TypeError, ValueError):
            return 3.0

    @property
    def allowed_methods(self):
        value = self.config.get("allowed_methods", list(METHODS))
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        normalized = [str(item).strip().lower() for item in value if str(item).strip()]
        return [item for item in normalized if item in METHODS]

    def method_allowed(self, method):
        return str(method).lower() in self.allowed_methods

    @property
    def require_two_factor(self):
        return bool(self.config.get("require_two_factor", False))

    @property
    def pin_max_attempts(self):
        try:
            return max(1, int(self.config.get("pin_max_attempts", 5)))
        except (TypeError, ValueError):
            return 5

    @property
    def pin_lockout_seconds(self):
        try:
            return max(1, int(self.config.get("pin_lockout_seconds", 300)))
        except (TypeError, ValueError):
            return 300

    @property
    def admin_roles(self):
        value = self.config.get("admin_roles", ["admin", "security"])
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        return {str(item).strip().lower() for item in value if str(item).strip()}

    @property
    def admin_second_approver(self):
        return bool(self.config.get("admin_second_approver", False))

    @property
    def card_reader_kind(self):
        return str(self.config.get("card_reader", "none")).lower()

    @property
    def liveness_provider(self):
        return str(self.config.get("liveness_provider", "none")).lower()

    @property
    def fail_mode(self):
        return str(self.config.get("fail_mode", "fail_secure")).lower()

    def face_access_state(self):
        if not self.method_allowed("face"):
            return {
                "enabled": False,
                "pilot": False,
                "detail": "Face is disabled at this door.",
            }
        if self.controller == "webhook":
            return {
                "enabled": False,
                "pilot": False,
                "detail": "Liveness verification is not available in this build. Face access is blocked for physical hardware.",
            }
        if self.controller == "simulated":
            return {
                "enabled": True,
                "pilot": True,
                "detail": "Simulated pilot: face matching only, not proof of identity.",
            }
        return {
            "enabled": True,
            "pilot": False,
            "detail": "Liveness provider configured.",
        }

    def status(self):
        if self.controller == "simulated":
            return {
                "state": "simulated",
                "label": "Simulated relay",
                "detail": "No physical door is connected.",
                "ok": True,
            }
        if self.controller != "webhook":
            return {
                "state": "disconnected",
                "label": "Controller unavailable",
                "detail": f"Unknown controller type: {self.controller}",
                "ok": False,
            }
        if not str(self.config.get("webhook_url", "")).strip():
            return {
                "state": "disconnected",
                "label": "Controller disconnected",
                "detail": "Webhook URL is not configured.",
                "ok": False,
            }
        if not self._webhook_transport_ok():
            return {
                "state": "disconnected",
                "label": "Controller unverified",
                "detail": "Physical controller URLs must use HTTPS (localhost HTTP is allowed for testing).",
                "ok": False,
            }
        if not str(self.config.get("secret", "")).strip():
            return {
                "state": "disconnected",
                "label": "Controller unverified",
                "detail": "Webhook secret is not configured. Refusing physical unlock calls.",
                "ok": False,
            }
        if self.last_error:
            return {
                "state": "disconnected",
                "label": "Controller error",
                "detail": self.last_error,
                "ok": False,
            }
        if self.last_success_at:
            return {
                "state": "connected",
                "label": "Controller verified",
                "detail": f"Last successful unlock: {self.last_success_at}",
                "ok": True,
            }
        return {
            "state": "unverified",
            "label": "Controller unverified",
            "detail": "Webhook configured; waiting for a verified response.",
            "ok": False,
        }

    def status_text(self):
        return self.status()["label"]

    def _webhook_transport_ok(self):
        url = str(self.config.get("webhook_url", "")).strip().lower()
        if url.startswith("https://"):
            return True
        return bool(re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?(/|$)", url))

    def unlock(self, event):
        key = str(event.get("event_key", "") or "")
        with self._sent_lock:
            if key and key in self._sent_keys:
                return {
                    "ok": False,
                    "detail": "Duplicate unlock request suppressed",
                    "controller": self.controller,
                    "duplicate": True,
                }
            if key:
                self._sent_keys.append(key)
                if len(self._sent_keys) > 1000:
                    self._sent_keys = self._sent_keys[-500:]
        if self.controller == "simulated":
            self.last_success_at = _now()
            return {
                "ok": True,
                "detail": "Simulated relay pulse",
                "controller": "simulated",
                "duplicate": False,
            }
        if self.controller == "webhook":
            url = str(self.config.get("webhook_url", "")).strip()
            if not url:
                self.last_error = "Webhook URL is not configured"
                return {"ok": False, "detail": self.last_error, "controller": "webhook"}
            if not self._webhook_transport_ok():
                self.last_error = "Physical controller URLs must use HTTPS"
                return {"ok": False, "detail": self.last_error, "controller": "webhook"}
            body = json.dumps(event, sort_keys=True).encode("utf-8")
            secret = str(self.config.get("secret", ""))
            if not secret:
                self.last_error = "Webhook secret is not configured"
                return {"ok": False, "detail": self.last_error, "controller": "webhook"}
            headers = {"Content-Type": "application/json"}
            if key:
                headers["X-FaceAI-Event-ID"] = key
            if secret:
                headers["X-FaceAI-Signature"] = hmac.new(
                    secret.encode("utf-8"), body, hashlib.sha256
                ).hexdigest()
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    code = getattr(resp, "status", 200)
                if 200 <= code < 300:
                    self.last_success_at = _now()
                    self.last_error = ""
                    return {
                        "ok": True,
                        "detail": f"Webhook responded with {code}",
                        "controller": "webhook",
                    }
                self.last_error = f"Webhook responded with {code}"
                return {"ok": False, "detail": self.last_error, "controller": "webhook"}
            except Exception as e:
                print(f"Door webhook failed: {e}")
                self.last_error = f"Webhook failed: {e}"
                return {"ok": False, "detail": self.last_error, "controller": "webhook"}
        return {
            "ok": False,
            "detail": f"Unknown controller type: {self.controller}",
            "controller": self.controller,
        }


class AccessDb:
    """SQLite store for people, credentials, decisions and audits."""

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _ensure_column(self, table, column, ddl):
        columns = {
            row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _init_schema(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    external_id TEXT DEFAULT '',
                    role TEXT DEFAULT '',
                    department TEXT DEFAULT '',
                    doors TEXT DEFAULT 'all',
                    active INTEGER DEFAULT 1,
                    photo_path TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
                    embedding BLOB NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS access_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    person_id INTEGER,
                    person_name TEXT DEFAULT '',
                    door_id TEXT DEFAULT '',
                    door_name TEXT DEFAULT '',
                    score REAL DEFAULT 0,
                    decision TEXT DEFAULT '',
                    reason TEXT DEFAULT '',
                    snapshot_path TEXT DEFAULT ''
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS card_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
                    card_uid TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'active',
                    valid_from TEXT DEFAULT '',
                    valid_until TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor_id INTEGER,
                    actor_name TEXT DEFAULT '',
                    person_id INTEGER,
                    person_name TEXT DEFAULT '',
                    detail TEXT DEFAULT ''
                )
                """
            )
            for column, ddl in (
                ("pin_hash", "TEXT DEFAULT ''"),
                ("pin_salt", "TEXT DEFAULT ''"),
                ("pin_iterations", "INTEGER DEFAULT 0"),
                ("pin_failed", "INTEGER DEFAULT 0"),
                ("pin_locked_until", "TEXT DEFAULT ''"),
                ("pin_revoked", "INTEGER DEFAULT 0"),
                ("pin_updated_at", "TEXT DEFAULT ''"),
                ("schedule_start", "TEXT DEFAULT '00:00'"),
                ("schedule_end", "TEXT DEFAULT '23:59'"),
                ("schedule_days", "TEXT DEFAULT '0,1,2,3,4,5,6'"),
            ):
                self._ensure_column("people", column, ddl)
            for column, ddl in (
                ("method", "TEXT DEFAULT 'face'"),
                ("credential_ref", "TEXT DEFAULT ''"),
                ("admin_id", "INTEGER"),
                ("admin_name", "TEXT DEFAULT ''"),
                ("approver_id", "INTEGER"),
                ("approver_name", "TEXT DEFAULT ''"),
                ("second_factor", "TEXT DEFAULT ''"),
                ("event_key", "TEXT DEFAULT ''"),
                ("policy", "TEXT DEFAULT ''"),
            ):
                self._ensure_column("access_events", column, ddl)
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_ts ON access_events(ts)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cards_person ON card_credentials(person_id)"
            )
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_event_key ON access_events(event_key) WHERE event_key <> ''"
            )

    # -- people ----------------------------------------------------
    def add_person(self, details, photo_path=""):
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO people
                    (full_name, external_id, role, department, doors, active,
                     photo_path, created_at, schedule_start, schedule_end, schedule_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    details.get("full_name", "").strip(),
                    details.get("external_id", "").strip(),
                    details.get("role", "").strip(),
                    details.get("department", "").strip(),
                    details.get("doors", "all").strip() or "all",
                    1 if details.get("active", True) else 0,
                    photo_path,
                    _now(),
                    details.get("schedule_start", "00:00"),
                    details.get("schedule_end", "23:59"),
                    details.get("schedule_days", "0,1,2,3,4,5,6"),
                ),
            )
            return cur.lastrowid

    def update_person(self, person_id, details):
        allowed = {
            "full_name",
            "external_id",
            "role",
            "department",
            "doors",
            "schedule_start",
            "schedule_end",
            "schedule_days",
        }
        updates = {k: v for k, v in details.items() if k in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self.conn:
            self.conn.execute(
                f"UPDATE people SET {assignments} WHERE id = ?",
                (*updates.values(), person_id),
            )

    def set_active(self, person_id, active):
        with self.conn:
            self.conn.execute(
                "UPDATE people SET active = ? WHERE id = ?",
                (1 if active else 0, person_id),
            )

    def get_person(self, person_id):
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.execute("SELECT * FROM people WHERE id = ?", (person_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def find_person(self, reference):
        self.conn.row_factory = sqlite3.Row
        ref = str(reference or "").strip()
        if not ref:
            return None
        row = self.conn.execute(
            "SELECT * FROM people WHERE external_id = ? COLLATE NOCASE", (ref,)
        ).fetchone()
        if row is None and ref.isdigit():
            row = self.conn.execute(
                "SELECT * FROM people WHERE id = ?", (int(ref),)
            ).fetchone()
        return dict(row) if row else None

    def set_photo(self, person_id, path):
        with self.conn:
            self.conn.execute("UPDATE people SET photo_path = ? WHERE id = ?", (path, person_id))

    def list_people(self, query="", filter_by="all"):
        self.conn.row_factory = sqlite3.Row
        sql = """
            SELECT p.*,
              (SELECT COUNT(*) FROM face_templates f WHERE f.person_id = p.id) AS face_count,
              (SELECT COUNT(*) FROM card_credentials c WHERE c.person_id = p.id AND c.status = 'active') AS card_count
            FROM people p
        """
        params = []
        clauses = []
        if query:
            clauses.append("(p.full_name LIKE ? OR p.external_id LIKE ? OR p.role LIKE ? OR p.department LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like, like, like])
        if filter_by == "active":
            clauses.append("p.active = 1")
        elif filter_by == "suspended":
            clauses.append("p.active = 0")
        elif filter_by == "no_face":
            clauses.append(
                "(SELECT COUNT(*) FROM face_templates f WHERE f.person_id = p.id) = 0"
            )
        elif filter_by == "no_pin":
            clauses.append("(p.pin_hash = '' OR p.pin_revoked = 1)")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY p.full_name COLLATE NOCASE"
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def count_admins_with_pin(self):
        row = self.conn.execute(
            "SELECT COUNT(*) FROM people WHERE active = 1 AND pin_hash <> '' AND pin_revoked = 0"
        ).fetchone()
        return int(row[0]) if row else 0

    def delete_person(self, person_id):
        with self.conn:
            self.conn.execute("DELETE FROM people WHERE id = ?", (person_id,))

    # -- pin -------------------------------------------------------
    def set_pin(self, person_id, pin_hash, pin_salt, iterations):
        with self.conn:
            self.conn.execute(
                """
                UPDATE people SET pin_hash = ?, pin_salt = ?, pin_iterations = ?,
                    pin_failed = 0, pin_locked_until = '', pin_revoked = 0,
                    pin_updated_at = ?
                WHERE id = ?
                """,
                (pin_hash, pin_salt, iterations, _now(), person_id),
            )

    def revoke_pin(self, person_id):
        with self.conn:
            self.conn.execute(
                """
                UPDATE people SET pin_hash = '', pin_salt = '', pin_iterations = 0,
                    pin_failed = 0, pin_locked_until = '', pin_revoked = 1,
                    pin_updated_at = ?
                WHERE id = ?
                """,
                (_now(), person_id),
            )

    def pin_failed(self, person_id, failed, locked_until):
        with self.conn:
            self.conn.execute(
                "UPDATE people SET pin_failed = ?, pin_locked_until = ? WHERE id = ?",
                (failed, locked_until, person_id),
            )

    def reset_pin_failures(self, person_id):
        with self.conn:
            self.conn.execute(
                "UPDATE people SET pin_failed = 0, pin_locked_until = '' WHERE id = ?",
                (person_id,),
            )

    # -- cards -----------------------------------------------------
    def add_card(self, person_id, card_uid, valid_until="", note=""):
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO card_credentials
                    (person_id, card_uid, status, valid_until, note, created_at, updated_at)
                VALUES (?, ?, 'active', ?, ?, ?, ?)
                """,
                (person_id, card_uid, valid_until, note, _now(), _now()),
            )
            return cur.lastrowid

    def list_cards(self, person_id=None):
        self.conn.row_factory = sqlite3.Row
        if person_id is None:
            rows = self.conn.execute(
                "SELECT c.*, p.full_name FROM card_credentials c JOIN people p ON p.id = c.person_id ORDER BY c.id DESC"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT c.*, p.full_name FROM card_credentials c JOIN people p ON p.id = c.person_id WHERE c.person_id = ? ORDER BY c.id DESC",
                (person_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def find_card(self, card_uid):
        self.conn.row_factory = sqlite3.Row
        row = self.conn.execute(
            """
            SELECT c.*, p.full_name, p.external_id, p.role, p.department,
                   p.doors, p.active, p.photo_path, p.schedule_start,
                   p.schedule_end, p.schedule_days, p.pin_hash, p.pin_revoked,
                   p.pin_failed, p.pin_locked_until
            FROM card_credentials c JOIN people p ON p.id = c.person_id
            WHERE c.card_uid = ?
            """,
            (card_uid,),
        ).fetchone()
        return dict(row) if row else None

    def set_card_status(self, card_id, status, note=None):
        with self.conn:
            if note is None:
                self.conn.execute(
                    "UPDATE card_credentials SET status = ?, updated_at = ? WHERE id = ?",
                    (status, _now(), card_id),
                )
            else:
                self.conn.execute(
                    "UPDATE card_credentials SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                    (status, note, _now(), card_id),
                )

    def card_by_id(self, card_id):
        self.conn.row_factory = sqlite3.Row
        row = self.conn.execute(
            "SELECT * FROM card_credentials WHERE id = ?", (card_id,)
        ).fetchone()
        return dict(row) if row else None

    # -- face templates -------------------------------------------
    def add_template(self, person_id, embedding):
        with self.conn:
            self.conn.execute(
                "INSERT INTO face_templates (person_id, embedding, created_at) VALUES (?, ?, ?)",
                (person_id, embedding.astype(np.float32).tobytes(), _now()),
            )

    def templates(self):
        rows = self.conn.execute(
            """
            SELECT t.id, t.person_id, t.embedding, p.full_name, p.role, p.department,
                   p.doors, p.active, p.external_id, p.photo_path,
                   p.schedule_start, p.schedule_end, p.schedule_days
            FROM face_templates t JOIN people p ON p.id = t.person_id
            """
        ).fetchall()
        out = []
        for row in rows:
            out.append(
                {
                    "template_id": row[0],
                    "person_id": row[1],
                    "embedding": np.frombuffer(row[2], dtype=np.float32),
                    "full_name": row[3],
                    "role": row[4],
                    "department": row[5],
                    "doors": row[6],
                    "active": bool(row[7]),
                    "external_id": row[8],
                    "photo_path": row[9],
                    "schedule_start": row[10],
                    "schedule_end": row[11],
                    "schedule_days": row[12],
                }
            )
        return out

    def face_count(self, person_id):
        row = self.conn.execute(
            "SELECT COUNT(*) FROM face_templates WHERE person_id = ?", (person_id,)
        ).fetchone()
        return int(row[0]) if row else 0

    # -- audit -----------------------------------------------------
    def log_event(self, event):
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO access_events
                    (ts, person_id, person_name, door_id, door_name, score,
                     decision, reason, snapshot_path, method, credential_ref,
                     admin_id, admin_name, approver_id, approver_name,
                     second_factor, event_key, policy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("ts", _now()),
                    event.get("person_id"),
                    event.get("person_name", ""),
                    event.get("door_id", ""),
                    event.get("door_name", ""),
                    float(event.get("score", 0.0)),
                    event.get("decision", ""),
                    event.get("reason", ""),
                    event.get("snapshot_path", ""),
                    event.get("method", ""),
                    event.get("credential_ref", ""),
                    event.get("admin_id"),
                    event.get("admin_name", ""),
                    event.get("approver_id"),
                    event.get("approver_name", ""),
                    event.get("second_factor", ""),
                    event.get("event_key", ""),
                    event.get("policy", ""),
                ),
            )
            return cur.lastrowid

    def list_events(self, limit=50):
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute(
            "SELECT * FROM access_events ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [dict(r) for r in rows]

    def export_events(self, path):
        rows = self.list_events(limit=100000)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["timestamp", "person_id", "person_name", "door_id", "door_name",
                 "method", "credential_ref", "score", "decision", "reason",
                 "admin_name", "approver_name", "second_factor", "snapshot_path"]
            )
            for row in reversed(rows):
                writer.writerow(
                    [
                        row["ts"], row["person_id"], row["person_name"],
                        row["door_id"], row["door_name"], row.get("method", ""),
                        row.get("credential_ref", ""), f"{row['score']:.4f}",
                        row["decision"], row["reason"], row.get("admin_name", ""),
                        row.get("approver_name", ""), row.get("second_factor", ""),
                        row["snapshot_path"],
                    ]
                )
        return path

    def log_audit(self, action, actor=None, person=None, detail=""):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO audit_events
                    (ts, action, actor_id, actor_name, person_id, person_name, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(),
                    action,
                    (actor or {}).get("id"),
                    (actor or {}).get("full_name", ""),
                    (person or {}).get("id"),
                    (person or {}).get("full_name", ""),
                    detail,
                ),
            )

    def list_audit(self, limit=50):
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute(
            "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [dict(r) for r in rows]


class AccessSvc:
    """Authorize people through face, PIN, card or administrator assistance."""

    def __init__(self, db_path, face_ai, door_config_path, snapshot_dir, db=None, card_reader=None):
        self.face_ai = face_ai
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)
        self.db = db or AccessDb(db_path)
        self.door = DoorController(door_config_path)
        self.card_reader = card_reader or self._make_card_reader()
        self._lock = threading.RLock()
        self._challenges = {}
        self._last_grant = 0.0
        self._unknown_pin_failures = {}

    # -- setup / status -------------------------------------------
    @property
    def ready(self):
        return bool(
            self.face_ai
            and self.face_ai.face_detect
            and self.face_ai.face_detect.session is not None
            and self.face_ai.face_recog
            and self.face_ai.face_recog.session is not None
        )

    def _make_card_reader(self):
        if self.door.card_reader_kind == "keyboard_wedge":
            return KeyboardWedgeCardReader()
        return NullCardReader()

    def reload_door(self):
        self.door.reload()
        self.card_reader = self._make_card_reader()
        return self.controller_status()

    def controller_status(self):
        return self.door.status()

    def face_state(self):
        return self.door.face_access_state()

    def card_reader_status(self):
        return {
            "available": bool(self.card_reader.available),
            "name": self.card_reader.name,
            "label": self.card_reader.status_text(),
            "manual": bool(self.card_reader.requires_manual_entry),
        }

    def admin_required(self):
        return self._admin_pin_exists()

    def _is_active_admin(self, person):
        return bool(
            person
            and person.get("active")
            and person.get("pin_hash")
            and not person.get("pin_revoked")
            and str(person.get("role", "")).lower() in self.door.admin_roles
        )

    def _active_admin_count(self):
        return sum(1 for person in self.db.list_people() if self._is_active_admin(person))

    def _is_last_admin(self, person):
        return self._is_active_admin(person) and self._active_admin_count() <= 1

    def _admin_pin_exists(self):
        # An existing administrator credential keeps the bootstrap flow closed
        # even when that administrator is currently suspended. Suspending is
        # not a way to re-open unauthenticated provisioning.
        for person in self.db.list_people():
            if (
                person.get("pin_hash")
                and not person.get("pin_revoked")
                and str(person.get("role", "")).lower() in self.door.admin_roles
            ):
                return True
        return False

    def _public_person(self, person):
        if not person:
            return None
        clean = {
            key: value
            for key, value in person.items()
            if key not in ("pin_hash", "pin_salt", "pin_iterations")
        }
        clean["active"] = bool(person.get("active", 0))
        clean["face_count"] = int(person.get("face_count") or self.db.face_count(person.get("id")))
        clean["card_count"] = int(person.get("card_count") or 0)
        if not person.get("pin_hash"):
            pin_status = "revoked" if person.get("pin_revoked") else "not_set"
        elif self._pin_locked_until(person):
            pin_status = "locked"
        else:
            pin_status = "active"
        clean["pin_status"] = pin_status
        clean["status"] = "active" if clean["active"] else "suspended"
        return clean

    # -- helpers ---------------------------------------------------
    def _pin_locked_until(self, person):
        raw = str(person.get("pin_locked_until", "") or "")
        if not raw:
            return None
        try:
            until = datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        return until if until > _now_dt() else None

    @staticmethod
    def _hash_pin(pin, salt_hex, iterations=PIN_ITERATIONS):
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac(
            "sha256", str(pin).encode("utf-8"), salt, int(iterations)
        )
        return digest.hex()

    def _verify_pin_for_person(self, person, pin):
        if person.get("pin_revoked"):
            return False, "PIN is revoked."
        if not person.get("pin_hash"):
            return False, "PIN is not enrolled."
        locked = self._pin_locked_until(person)
        if locked:
            remaining = max(1, int((locked - _now_dt()).total_seconds()))
            return False, f"PIN locked. Try again in {remaining}s."
        try:
            iterations = int(person.get("pin_iterations") or PIN_ITERATIONS)
        except (TypeError, ValueError):
            iterations = PIN_ITERATIONS
        expected = str(person.get("pin_hash", ""))
        actual = self._hash_pin(pin, str(person.get("pin_salt", "")), iterations)
        if hmac.compare_digest(expected, actual):
            self.db.reset_pin_failures(person["id"])
            return True, ""
        failed = int(person.get("pin_failed") or 0) + 1
        max_attempts = self.door.pin_max_attempts
        locked_until = ""
        if failed >= max_attempts:
            until = _now_dt() + datetime.timedelta(seconds=self.door.pin_lockout_seconds)
            locked_until = until.strftime("%Y-%m-%d %H:%M:%S")
        self.db.pin_failed(person["id"], failed, locked_until)
        if locked_until:
            return False, f"Too many failed attempts. PIN locked for {self.door.pin_lockout_seconds}s."
        return False, f"Invalid PIN. {max_attempts - failed} attempt(s) remaining."

    def _person_locked(self, person):
        return bool(self._pin_locked_until(person))

    def _allowed(self, person, door_id):
        doors = str(person.get("doors") or "all").strip().lower()
        if doors in ("", "all", "*"):
            return True
        return door_id.lower() in [d.strip().lower() for d in doors.split(",")]

    def _check_person(self, person, method, now=None):
        now = now or _now_dt()
        if not person or not person.get("active"):
            return False, "This person is suspended."
        if not self.door.method_allowed(method):
            return False, f"{method.title()} is not allowed at {self.door.door_name}."
        if not self._allowed(person, self.door.door_id):
            return False, f"{person['full_name']} is not allowed at {self.door.door_name}."
        if now.weekday() not in _parse_days(person.get("schedule_days", "0,1,2,3,4,5,6")):
            return False, "Outside this person's access days."
        if not _within_window(
            person.get("schedule_start", "00:00"),
            person.get("schedule_end", "23:59"),
            now.time(),
        ):
            return False, "Outside this person's access hours."
        if now.weekday() not in _parse_days(self.door.config.get("open_days", "0,1,2,3,4,5,6")):
            return False, "The door is closed today."
        if not _within_window(
            self.door.config.get("open_start", "00:00"),
            self.door.config.get("open_end", "23:59"),
            now.time(),
        ):
            return False, "The door is closed at this time."
        return True, ""

    def _event_key(self):
        return secrets.token_hex(12)

    def _log_event(
        self,
        method,
        decision,
        reason,
        person=None,
        credential_ref="",
        score=0.0,
        snapshot_path="",
        admin=None,
        approver=None,
        second_factor="",
        policy="",
        event_key=None,
    ):
        person = person or {}
        event = {
            "ts": _now(),
            "person_id": person.get("person_id") or person.get("id"),
            "person_name": person.get("full_name", ""),
            "door_id": self.door.door_id,
            "door_name": self.door.door_name,
            "score": float(score or 0.0),
            "decision": decision,
            "reason": reason,
            "snapshot_path": snapshot_path or "",
            "method": method,
            "credential_ref": credential_ref,
            "admin_id": (admin or {}).get("id"),
            "admin_name": (admin or {}).get("full_name", ""),
            "approver_id": (approver or {}).get("id"),
            "approver_name": (approver or {}).get("full_name", ""),
            "second_factor": second_factor,
            "event_key": event_key or self._event_key(),
            "policy": policy,
        }
        event["id"] = self.db.log_event(event)
        return event

    def _result(self, event, door_result=None, person=None, extra=None):
        person = person or {}
        result = {
            "ok": event.get("decision") == "granted",
            "decision": event.get("decision"),
            "message": event.get("reason", ""),
            "method": event.get("method", ""),
            "score": event.get("score", 0.0),
            "threshold": self.door.threshold,
            "door_id": self.door.door_id,
            "door_name": self.door.door_name,
            "door_controller": self.door.controller,
            "door_status": self.door.status(),
            "door_detail": (door_result or {}).get("detail", ""),
            "door_ok": bool(door_result and door_result.get("ok")),
            "person": self._public_person(person) if person else None,
            "person_id": person.get("person_id") or person.get("id"),
            "person_name": person.get("full_name", ""),
            "role": person.get("role", ""),
            "department": person.get("department", ""),
            "external_id": person.get("external_id", ""),
            "credential_ref": event.get("credential_ref", ""),
            "second_factor": event.get("second_factor", ""),
            "policy": event.get("policy", ""),
            "ts": event.get("ts", ""),
            "event_id": event.get("id"),
        }
        if extra:
            result.update(extra)
        return result

    def _deny(self, method, reason, person=None, credential_ref="", score=0.0, snapshot_path="", admin=None, approver=None, second_factor="", policy="", decision="denied"):
        event = self._log_event(
            method,
            decision,
            reason,
            person,
            credential_ref,
            score,
            snapshot_path,
            admin,
            approver,
            second_factor,
            policy,
        )
        return self._result(event, person=person)

    def _grant(self, person, method, reason, credential_ref="", score=0.0, snapshot_path="", admin=None, approver=None, second_factor="", policy=""):
        now = time.monotonic()
        if (now - self._last_grant) < self.door.cooldown_seconds:
            return self._deny(
                method,
                "Cooldown: please wait before trying again.",
                person,
                credential_ref,
                score,
                snapshot_path,
                admin,
                approver,
                second_factor,
                policy,
            )
        # Record the request before touching the relay. If the process dies
        # during the controller call, the audit shows a pending request rather
        # than falsely claiming that a door was opened.
        event = self._log_event(
            method,
            "pending",
            "Controller request pending",
            person,
            credential_ref,
            score,
            snapshot_path,
            admin,
            approver,
            second_factor,
            policy,
        )
        request = dict(event)
        request["decision"] = "granted"
        request["reason"] = reason
        try:
            door_result = self.door.unlock(request)
        except Exception as e:
            print(f"Door controller exception: {e}")
            door_result = {"ok": False, "detail": f"Door controller exception: {e}"}
        if not door_result.get("ok"):
            event["decision"] = "error"
            event["reason"] = door_result.get("detail", "Door controller failed")
            self.db.log_audit(
                "controller_error",
                actor=admin,
                person=person,
                detail=event["reason"],
            )
        else:
            event["decision"] = "granted"
            event["reason"] = reason
            self._last_grant = now
        with self.db.conn:
            self.db.conn.execute(
                "UPDATE access_events SET decision = ?, reason = ? WHERE id = ?",
                (event["decision"], event["reason"], event["id"]),
            )
        return self._result(event, door_result, person)

    def _issue_challenge(self, method, person, reason, credential_ref="", score=0.0, snapshot_path=""):
        token = secrets.token_urlsafe(24)
        self._challenges[token] = {
            "expires": time.monotonic() + 120,
            "method": method,
            "person_id": person["id"],
            "door_id": self.door.door_id,
            "credential_ref": credential_ref,
            "score": score,
            "snapshot_path": snapshot_path,
        }
        event = self._log_event(
            method,
            "challenge",
            reason,
            person,
            credential_ref,
            score,
            snapshot_path,
            second_factor="pin",
            policy="two_factor",
        )
        result = self._result(
            event,
            person=person,
            extra={
                "next_factor": "pin",
                "challenge_token": token,
                "message": reason,
            },
        )
        result["decision"] = "second_factor_required"
        result["ok"] = False
        return result

    def complete_challenge(self, token, pin):
        with self._lock:
            challenge = self._challenges.pop(token, None)
            if not challenge or challenge["expires"] < time.monotonic():
                return self._deny("second_factor", "The second-factor challenge expired. Start again.")
            if challenge["door_id"] != self.door.door_id:
                return self._deny("second_factor", "The door configuration changed. Start again.")
            person = self.db.get_person(challenge["person_id"])
            if not person:
                return self._deny("second_factor", "The person record is no longer available.")
            method = f"{challenge['method']}+pin"
            allowed, reason = self._check_person(person, challenge["method"])
            if not allowed:
                return self._deny(method, reason, person, challenge["credential_ref"], challenge["score"], challenge["snapshot_path"], second_factor="pin", policy="two_factor")
            if not str(pin).strip():
                return self._deny(method, "Enter your PIN to complete the second factor.", person, "PIN", challenge["score"], "", second_factor="pin", policy="two_factor")
            ok, reason = self._verify_pin_for_person(person, pin)
            if not ok:
                return self._deny(method, reason, person, "PIN", challenge["score"], "", second_factor="pin", policy="two_factor")
            return self._grant(
                person,
                method,
                "Face/card and PIN verified; door permission granted.",
                challenge["credential_ref"],
                challenge["score"],
                challenge["snapshot_path"],
                second_factor="pin",
                policy="two_factor",
            )

    # -- registration / management --------------------------------
    def _verify_admin(self, actor_ref, actor_pin, audit=True):
        actor = self.db.find_person(actor_ref)
        if not actor:
            if audit:
                self.db.log_audit("admin_auth_denied", detail=f"Unknown admin reference: {actor_ref}")
            return None, "Administrator credentials were not recognized."
        if not actor.get("active"):
            if audit:
                self.db.log_audit("admin_auth_denied", person=actor, detail="Suspended administrator")
            return None, "This administrator is suspended."
        if str(actor.get("role", "")).lower() not in self.door.admin_roles:
            if audit:
                self.db.log_audit("admin_auth_denied", person=actor, detail="Role is not authorized")
            return None, "This person does not have administrator permissions."
        ok, reason = self._verify_pin_for_person(actor, actor_pin)
        if not ok:
            if audit:
                self.db.log_audit("admin_auth_denied", person=actor, detail=reason)
            return None, reason
        if audit:
            self.db.log_audit("admin_auth", person=actor, detail="Administrator authenticated")
        return actor, ""

    def verify_admin(self, actor_ref, actor_pin):
        with self._lock:
            actor, reason = self._verify_admin(actor_ref, actor_pin)
        if actor is None:
            return {"ok": False, "message": reason}
        return {"ok": True, "person": self._public_person(actor)}

    def _actor_for_management(self, actor_ref, actor_pin):
        if actor_ref or actor_pin:
            actor, reason = self._verify_admin(actor_ref, actor_pin)
            if actor is None:
                return None, reason
            return actor, ""
        if not self._admin_pin_exists():
            return None, ""
        return None, "Administrator authorization required."

    def register_person(self, details, frame, actor_ref=None, actor_pin=None):
        with self._lock:
            if self._admin_pin_exists():
                actor, reason = self._verify_admin(actor_ref, actor_pin)
                if actor is None:
                    return {"ok": False, "message": reason}
            elif actor_ref or actor_pin:
                actor, reason = self._verify_admin(actor_ref, actor_pin)
                if actor is None:
                    return {"ok": False, "message": reason}
            if not self.ready:
                return {"ok": False, "message": "Face engine is not running."}
            name = str(details.get("full_name", "")).strip()
            if len(name) < 2:
                return {"ok": False, "message": "Please enter a full name."}
            external_id = str(details.get("external_id", "")).strip()
            if external_id and self.db.find_person(external_id):
                return {"ok": False, "message": "That staff/resident ID is already in use."}
            for key in ("schedule_start", "schedule_end"):
                value = details.get(key)
                if value and not _valid_time(value):
                    return {"ok": False, "message": "Access times must be valid HH:MM values."}
            cropped = self.face_ai.face_detect.get_single_face_cropped(frame)
            if cropped is None:
                return {
                    "ok": False,
                    "message": "Exactly one clear face is required. Look straight at the camera.",
                }
            embedding = self.face_ai.face_recog.get_face_embedding(cropped)
            if embedding is None:
                return {"ok": False, "message": "Could not compute a face template."}
            snapshot = self._save_snapshot(frame, "enroll")
            person_id = self.db.add_person(details, snapshot)
            if snapshot:
                target = os.path.join(self.snapshot_dir, f"person_{person_id}.jpg")
                try:
                    os.replace(snapshot, target)
                    snapshot = target
                    self.db.set_photo(person_id, target)
                except OSError:
                    pass
            self.db.add_template(person_id, embedding)
            person = self.db.get_person(person_id)
            self.db.log_audit("person_enrolled", person=person, detail=f"Face template enrolled at {self.door.door_name}")
            return {"ok": True, "person": self._public_person(person)}

    def enroll_face(self, person_id, frame, actor_ref=None, actor_pin=None):
        """Add another face template through an authenticated admin workflow."""
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            if not self.ready:
                return {"ok": False, "message": "Face engine is not running."}
            cropped = self.face_ai.face_detect.get_single_face_cropped(frame)
            if cropped is None:
                return {"ok": False, "message": "Exactly one clear face is required."}
            embedding = self.face_ai.face_recog.get_face_embedding(cropped)
            if embedding is None:
                return {"ok": False, "message": "Could not compute a face template."}
            snapshot = self._save_snapshot(frame, "enroll")
            self.db.add_template(person_id, embedding)
            if snapshot:
                target = os.path.join(self.snapshot_dir, f"person_{person_id}.jpg")
                try:
                    os.replace(snapshot, target)
                    self.db.set_photo(person_id, target)
                except OSError:
                    pass
            self.db.log_audit(
                "face_enrolled",
                actor=actor,
                person=person,
                detail=f"Additional face template enrolled at {self.door.door_name}",
            )
            return {
                "ok": True,
                "person": self._public_person(self.db.get_person(person_id)),
                "message": "Face template enrolled.",
            }

    def set_pin(self, person_id, pin, actor_ref=None, actor_pin=None):
        with self._lock:
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            pin = str(pin or "")
            if not re.fullmatch(r"\d{4,8}", pin):
                return {"ok": False, "message": "PIN must be 4 to 8 digits."}
            actor = None
            if actor_ref or actor_pin:
                actor, reason = self._verify_admin(actor_ref, actor_pin)
                if actor is None:
                    return {"ok": False, "message": reason}
            elif self._admin_pin_exists():
                return {"ok": False, "message": "Administrator authorization required."}
            elif str(person.get("role", "")).lower() not in self.door.admin_roles:
                return {"ok": False, "message": "The first PIN must belong to an administrator role."}
            salt = secrets.token_hex(16)
            self.db.set_pin(person_id, self._hash_pin(pin, salt), salt, PIN_ITERATIONS)
            self.db.log_audit("pin_set", actor=actor, person=person, detail="PIN credential set or reset")
            return {"ok": True, "message": "PIN set."}

    def revoke_pin(self, person_id, actor_ref=None, actor_pin=None):
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            if self._is_last_admin(person):
                return {"ok": False, "message": "Cannot revoke the last administrator PIN."}
            self.db.revoke_pin(person_id)
            self.db.log_audit("pin_revoked", actor=actor, person=person, detail="PIN credential revoked")
            return {"ok": True, "message": "PIN revoked."}

    def assign_card(self, person_id, card_uid, valid_until="", note="", actor_ref=None, actor_pin=None):
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            uid = _normalize_card_uid(card_uid)
            if not _valid_card_uid(uid):
                return {"ok": False, "message": "Enter a valid card UID (4-64 letters/digits)."}
            if valid_until:
                try:
                    datetime.date.fromisoformat(valid_until)
                except ValueError:
                    return {"ok": False, "message": "Expiry must be YYYY-MM-DD."}
            try:
                self.db.add_card(person_id, uid, valid_until, note)
            except sqlite3.IntegrityError:
                return {"ok": False, "message": "That card is already enrolled."}
            self.db.log_audit("card_enrolled", actor=actor, person=person, detail=f"Card ending {_mask_ref(uid)} enrolled")
            return {"ok": True, "message": f"Card ending {_mask_ref(uid)} enrolled."}

    def revoke_card(self, card_id, actor_ref=None, actor_pin=None, lost=False):
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            card = self.db.card_by_id(card_id)
            if not card:
                return {"ok": False, "message": "Card not found."}
            person = self.db.get_person(card["person_id"])
            status = "lost" if lost else "revoked"
            self.db.set_card_status(card_id, status)
            self.db.log_audit(
                "card_lost" if lost else "card_revoked",
                actor=actor,
                person=person,
                detail=f"Card ending {_mask_ref(card['card_uid'])} marked {status}",
            )
            return {"ok": True, "message": f"Card marked {status}."}

    def update_person(self, person_id, details, actor_ref=None, actor_pin=None):
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            new_role = str(details.get("role", person.get("role", ""))).lower()
            if self._is_last_admin(person) and new_role not in self.door.admin_roles:
                return {"ok": False, "message": "Cannot remove the last administrator role."}
            new_external = str(details.get("external_id", "")).strip()
            if new_external:
                other = self.db.find_person(new_external)
                if other and other["id"] != person_id:
                    return {"ok": False, "message": "That staff/resident ID is already in use."}
            for key in ("schedule_start", "schedule_end"):
                value = details.get(key)
                if value and not _valid_time(value):
                    return {"ok": False, "message": "Access times must be valid HH:MM values."}
            self.db.update_person(person_id, details)
            self.db.log_audit("person_updated", actor=actor, person=person, detail="Person details updated")
            return {"ok": True, "person": self._public_person(self.db.get_person(person_id))}

    def set_active(self, person_id, active, actor_ref=None, actor_pin=None):
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            if not active and self._is_last_admin(person):
                return {"ok": False, "message": "Cannot suspend the last active administrator."}
            self.db.set_active(person_id, active)
            self.db.log_audit(
                "person_activated" if active else "person_suspended",
                actor=actor,
                person=person,
                detail="Person status changed",
            )
            return {"ok": True, "message": "Person activated." if active else "Person suspended."}

    def delete_person(self, person_id, actor_ref=None, actor_pin=None):
        with self._lock:
            actor, reason = self._actor_for_management(actor_ref, actor_pin)
            if actor is None:
                return {"ok": False, "message": reason or "Administrator authorization required."}
            person = self.db.get_person(person_id)
            if not person:
                return {"ok": False, "message": "Person not found."}
            if self._is_last_admin(person):
                return {"ok": False, "message": "Cannot delete the last active administrator."}
            self.db.delete_person(person_id)
            self.db.log_audit("person_deleted", actor=actor, person=person, detail="Person and credentials deleted")
            return {"ok": True}

    # -- face ------------------------------------------------------
    def _save_snapshot(self, frame, prefix):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(self.snapshot_dir, f"{prefix}_{stamp}.jpg")
        try:
            cv2.imwrite(path, frame)
        except Exception as e:
            print(f"Could not save access snapshot: {e}")
            return ""
        return path

    def authenticate_face(self, frame):
        with self._lock:
            state = self.door.face_access_state()
            if not state["enabled"]:
                return self._deny(
                    "face",
                    state["detail"],
                    credential_ref="Face",
                    policy="policy",
                    decision="error",
                )
            if not self.ready:
                return self._deny(
                    "face",
                    "Face engine is not running.",
                    credential_ref="Face",
                    decision="error",
                )
            cropped = self.face_ai.face_detect.get_single_face_cropped(frame)
            if cropped is None:
                return self._deny("face", "No single face found. Look straight at the camera.", credential_ref="Face")
            embedding = self.face_ai.face_recog.get_face_embedding(cropped)
            templates = self.db.templates()
            if embedding is None or not templates:
                return self._deny(
                    "face",
                    "No face template" if embedding is None else "No registered people",
                    credential_ref="Face",
                )
            matrix = np.vstack([t["embedding"] for t in templates]).astype(np.float32)
            scores = matrix @ embedding.astype(np.float32)
            best_index = int(np.argmax(scores))
            best = templates[best_index]
            score = float(scores[best_index])
            if score < self.door.threshold:
                snapshot = self._save_snapshot(frame, "access")
                return self._deny(
                    "face",
                    "Face not recognised. Try again or use another method.",
                    credential_ref="Face",
                    score=score,
                    snapshot_path=snapshot,
                )
            person = self.db.get_person(best["person_id"])
            allowed, reason = self._check_person(person, "face")
            snapshot = self._save_snapshot(frame, "access")
            if not allowed:
                return self._deny("face", reason, person, "Face", score, snapshot)
            if self.door.require_two_factor:
                return self._issue_challenge(
                    "face", person, f"PIN required for {person['full_name']} at {self.door.door_name}.", "Face", score, snapshot
                )
            return self._grant(
                person,
                "face",
                "Face verified and door permission granted.",
                "Face",
                score,
                snapshot,
                policy="face",
            )

    def identify(self, frame):
        """Backward-compatible alias used by earlier callers."""
        return self.authenticate_face(frame)

    # -- PIN -------------------------------------------------------
    def authenticate_pin(self, person_ref, pin):
        with self._lock:
            ref = str(person_ref or "").strip()
            now = time.monotonic()
            throttle = self._unknown_pin_failures.get(ref.lower())
            if throttle and throttle[1] > now:
                return self._deny("pin", "Too many failed attempts. Try again later.", credential_ref="PIN")
            if not self.door.method_allowed("pin"):
                return self._deny("pin", "PIN is not allowed at this door.", credential_ref="PIN")
            if self.door.require_two_factor:
                return self._deny(
                    "pin",
                    "Two-factor policy: this door requires face or card plus PIN. PIN alone is not accepted.",
                    credential_ref="PIN",
                    policy="two_factor",
                )
            person = self.db.find_person(person_ref)
            if not person:
                count, until = self._unknown_pin_failures.get(ref.lower(), (0, 0))
                count += 1
                if count >= self.door.pin_max_attempts:
                    until = now + self.door.pin_lockout_seconds
                    count = 0
                self._unknown_pin_failures[ref.lower()] = (count, until)
                return self._deny("pin", "Credential reference not recognized.", credential_ref="PIN")
            allowed, reason = self._check_person(person, "pin")
            if not allowed:
                return self._deny("pin", reason, person, "PIN")
            ok, reason = self._verify_pin_for_person(person, pin)
            if not ok:
                return self._deny("pin", reason, person, "PIN")
            return self._grant(person, "pin", "PIN verified and door permission granted.", "PIN", policy="pin")

    # -- card ------------------------------------------------------
    def authenticate_card(self, card_uid):
        with self._lock:
            if not self.card_reader.available:
                return {
                    "ok": False,
                    "decision": "unavailable",
                    "message": self.card_reader.status_text(),
                    "method": "card",
                    "door_id": self.door.door_id,
                    "door_name": self.door.door_name,
                    "door_status": self.door.status(),
                }
            uid = _normalize_card_uid(card_uid)
            if not _valid_card_uid(uid):
                return self._deny("card", "Invalid card credential.", credential_ref="-")
            card = self.db.find_card(uid)
            credential_ref = _mask_ref(uid)
            if not card:
                return self._deny("card", "Card is not enrolled at this door.", credential_ref=credential_ref)
            if card.get("status") != "active":
                return self._deny("card", f"Card is {card.get('status')}.", {"id": card["person_id"], "full_name": card.get("full_name", ""), "active": card.get("active", 0), "doors": card.get("doors", ""), "schedule_start": card.get("schedule_start", "00:00"), "schedule_end": card.get("schedule_end", "23:59"), "schedule_days": card.get("schedule_days", "")}, credential_ref)
            valid_from = str(card.get("valid_from", "") or "")
            if valid_from:
                try:
                    if datetime.date.fromisoformat(valid_from) > _now_dt().date():
                        return self._deny("card", "Card is not valid yet.", credential_ref=credential_ref)
                except ValueError:
                    return self._deny("card", "Card has an invalid start date.", credential_ref=credential_ref)
            valid_until = str(card.get("valid_until", "") or "")
            if valid_until:
                try:
                    if datetime.date.fromisoformat(valid_until) < _now_dt().date():
                        return self._deny("card", "Card has expired.", {"id": card["person_id"], "full_name": card.get("full_name", ""), "active": card.get("active", 0), "doors": card.get("doors", ""), "schedule_start": card.get("schedule_start", "00:00"), "schedule_end": card.get("schedule_end", "23:59"), "schedule_days": card.get("schedule_days", "")}, credential_ref)
                except ValueError:
                    return self._deny("card", "Card has an invalid expiry.", credential_ref=credential_ref)
            person = self.db.get_person(card["person_id"])
            allowed, reason = self._check_person(person, "card")
            if not allowed:
                return self._deny("card", reason, person, credential_ref)
            if self.door.require_two_factor:
                return self._issue_challenge(
                    "card", person, f"PIN required for {person['full_name']} after card scan.", credential_ref
                )
            return self._grant(person, "card", "Card verified and door permission granted.", credential_ref, policy="card")

    # -- administrator assistance ---------------------------------
    def authorize_admin_access(self, admin_ref, admin_pin, subject_ref, reason, approver_ref="", approver_pin=""):
        with self._lock:
            admin, admin_error = self._verify_admin(admin_ref, admin_pin)
            if admin is None:
                return self._deny("admin", admin_error, credential_ref="Administrator", decision="denied")
            subject = self.db.find_person(subject_ref)
            if not subject:
                return self._deny("admin", "Subject person not found.", admin=admin, credential_ref="Administrator")
            if len(str(reason or "").strip()) < 5:
                return self._deny("admin", "A recorded reason is required.", subject, "Administrator", admin=admin)
            if subject["id"] == admin["id"]:
                return self._deny("admin", "Administrators cannot self-authorize assistance.", subject, "Administrator", admin=admin)
            allowed, why = self._check_person(subject, "admin")
            if not allowed:
                return self._deny("admin", why, subject, "Administrator", admin=admin)
            if self._person_locked(subject):
                return self._deny("admin", "The subject is security-locked. Assistance cannot override it.", subject, "Administrator", admin=admin)
            if self.door.admin_second_approver:
                if not approver_ref or not approver_pin:
                    return self._deny("admin", "A second administrator approval is required.", subject, "Administrator", admin=admin)
                approver, err = self._verify_admin(approver_ref, approver_pin)
                if approver is None:
                    return self._deny("admin", f"Second approver: {err}", subject, "Administrator", admin=admin)
                if approver["id"] in (admin["id"], subject["id"]):
                    return self._deny("admin", "The second approver must be a different administrator.", subject, "Administrator", admin=admin, approver=approver)
            else:
                approver = None
            return self._grant(
                subject,
                "admin",
                f"Administrator assistance: {str(reason).strip()}",
                "Administrator",
                admin=admin,
                approver=approver,
                policy="admin_assistance",
            )

    # -- read helpers ---------------------------------------------
    def list_people(self, query="", filter_by="all"):
        with self._lock:
            people = self.db.list_people(query, filter_by)
            return [self._public_person(person) for person in people]

    def person_profile(self, person_id):
        with self._lock:
            person = self.db.get_person(person_id)
            if not person:
                return None
            cards = [
                {
                    "id": card["id"],
                    "card_ref": _mask_ref(card["card_uid"]),
                    "status": card["status"],
                    "valid_until": card.get("valid_until", ""),
                    "note": card.get("note", ""),
                }
                for card in self.db.list_cards(person_id)
            ]
            profile = self._public_person(person)
            profile["cards"] = cards
            profile["face_count"] = self.db.face_count(person_id)
            return profile

    def list_cards(self, person_id=None):
        return [
            {
                **card,
                "card_ref": _mask_ref(card.get("card_uid", "")),
                "card_uid": _mask_ref(card.get("card_uid", "")),
            }
            for card in self.db.list_cards(person_id)
        ]

    def list_events(self, limit=50):
        return self.db.list_events(limit)

    def list_audit(self, limit=50):
        return self.db.list_audit(limit)

    def export_events(self, path):
        return self.db.export_events(path)
