"""Door access pilot: people registry, face templates, audit log and a
pluggable door controller (simulated relay or HTTP webhook).

This layer is deliberately local-first: a kiosk can keep working when the
network is down and a real controller can be attached later by changing
``controller`` in ``config/doors.json``.
"""

import csv
import datetime
import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.request

import cv2
import numpy as np

DEFAULT_DOOR_CONFIG = {
    "door_id": "main-gate",
    "door_name": "Main Gate",
    "controller": "simulated",  # simulated | webhook
    "webhook_url": "",
    "secret": "",
    "threshold": 0.65,
    "cooldown_seconds": 3,
}


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class DoorController:
    """Talks to the door hardware. The pilot starts with a simulated relay."""

    def __init__(self, config_path):
        self.config_path = config_path
        self.config = {}
        self.reload()

    def reload(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump(DEFAULT_DOOR_CONFIG, f, indent=2)
        try:
            with open(self.config_path) as f:
                loaded = json.load(f)
        except Exception as e:
            print(f"Could not read door config: {e}")
            loaded = {}
        self.config = {**DEFAULT_DOOR_CONFIG, **loaded}
        return self.config

    @property
    def door_id(self):
        return str(self.config.get("door_id", "main-gate"))

    @property
    def door_name(self):
        return str(self.config.get("door_name", "Main Gate"))

    @property
    def controller(self):
        return str(self.config.get("controller", "simulated"))

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

    def status_text(self):
        if self.controller == "webhook":
            return "Webhook controller"
        if self.controller == "simulated":
            return "Simulated relay (pilot)"
        return f"Unknown controller: {self.controller}"

    def unlock(self, event):
        if self.controller == "simulated":
            return {
                "ok": True,
                "detail": "Simulated relay pulse",
                "controller": "simulated",
            }
        if self.controller == "webhook":
            url = str(self.config.get("webhook_url", "")).strip()
            if not url:
                return {
                    "ok": False,
                    "detail": "Webhook URL is not configured",
                    "controller": "webhook",
                }
            body = json.dumps(event, sort_keys=True).encode("utf-8")
            secret = str(self.config.get("secret", ""))
            headers = {"Content-Type": "application/json"}
            if secret:
                headers["X-FaceAI-Signature"] = hmac.new(
                    secret.encode("utf-8"), body, hashlib.sha256
                ).hexdigest()
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    code = getattr(resp, "status", 200)
                return {
                    "ok": 200 <= code < 300,
                    "detail": f"Webhook responded with {code}",
                    "controller": "webhook",
                }
            except Exception as e:
                print(f"Door webhook failed: {e}")
                return {
                    "ok": False,
                    "detail": f"Webhook failed: {e}",
                    "controller": "webhook",
                }
        return {
            "ok": False,
            "detail": f"Unknown controller type: {self.controller}",
            "controller": self.controller,
        }


class AccessDb:
    """SQLite store for people, face templates and the access audit trail."""

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

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
                "CREATE INDEX IF NOT EXISTS idx_events_ts ON access_events(ts)"
            )

    # -- people ----------------------------------------------------
    def add_person(self, details, photo_path=""):
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO people
                    (full_name, external_id, role, department, doors, active, photo_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            return cur.lastrowid

    def get_person(self, person_id):
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.execute("SELECT * FROM people WHERE id = ?", (person_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_photo(self, person_id, path):
        with self.conn:
            self.conn.execute("UPDATE people SET photo_path = ? WHERE id = ?", (path, person_id))

    def list_people(self):
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute(
            "SELECT * FROM people ORDER BY full_name COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_person(self, person_id):
        with self.conn:
            self.conn.execute("DELETE FROM people WHERE id = ?", (person_id,))

    # -- templates -------------------------------------------------
    def add_template(self, person_id, embedding):
        with self.conn:
            self.conn.execute(
                "INSERT INTO face_templates (person_id, embedding, created_at) VALUES (?, ?, ?)",
                (person_id, embedding.astype(np.float32).tobytes(), _now()),
            )

    def templates(self):
        rows = self.conn.execute(
            """
            SELECT t.person_id, t.embedding, p.full_name, p.role, p.department,
                   p.doors, p.active, p.external_id, p.photo_path
            FROM face_templates t JOIN people p ON p.id = t.person_id
            """
        ).fetchall()
        out = []
        for row in rows:
            out.append(
                {
                    "person_id": row[0],
                    "embedding": np.frombuffer(row[1], dtype=np.float32),
                    "full_name": row[2],
                    "role": row[3],
                    "department": row[4],
                    "doors": row[5],
                    "active": bool(row[6]),
                    "external_id": row[7],
                    "photo_path": row[8],
                }
            )
        return out

    # -- audit -----------------------------------------------------
    def log_event(self, event):
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO access_events
                    (ts, person_id, person_name, door_id, door_name, score,
                     decision, reason, snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                 "score", "decision", "reason", "snapshot_path"]
            )
            for row in reversed(rows):
                writer.writerow(
                    [
                        row["ts"], row["person_id"], row["person_name"],
                        row["door_id"], row["door_name"], f"{row['score']:.4f}",
                        row["decision"], row["reason"], row["snapshot_path"],
                    ]
                )
        return path


class AccessSvc:
    """Register people and authorize a face against the configured door."""

    def __init__(self, db_path, face_ai, door_config_path, snapshot_dir, db=None):
        self.face_ai = face_ai
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)
        self.db = db or AccessDb(db_path)
        self.door = DoorController(door_config_path)
        self._last_grant = 0.0

    @property
    def ready(self):
        return bool(
            self.face_ai
            and self.face_ai.face_detect
            and self.face_ai.face_detect.session is not None
            and self.face_ai.face_recog
            and self.face_ai.face_recog.session is not None
        )

    def _save_snapshot(self, frame, prefix):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(self.snapshot_dir, f"{prefix}_{stamp}.jpg")
        try:
            cv2.imwrite(path, frame)
        except Exception as e:
            print(f"Could not save access snapshot: {e}")
            return ""
        return path

    def register_person(self, details, frame):
        if not self.ready:
            return {"ok": False, "message": "Face engine is not running."}
        name = str(details.get("full_name", "")).strip()
        if len(name) < 2:
            return {"ok": False, "message": "Please enter a full name."}
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
        return {"ok": True, "person": self.db.get_person(person_id)}

    def _allowed(self, person, door_id):
        doors = str(person.get("doors") or "all").strip().lower()
        if doors in ("", "all", "*"):
            return True
        return door_id.lower() in [d.strip().lower() for d in doors.split(",")]

    def identify(self, frame):
        if not self.ready:
            return {
                "ok": False,
                "decision": "error",
                "message": "Face engine is not running.",
            }
        cropped = self.face_ai.face_detect.get_single_face_cropped(frame)
        if cropped is None:
            return {
                "ok": False,
                "decision": "denied",
                "message": "No single face found. Look straight at the camera.",
                "score": 0.0,
                "door_id": self.door.door_id,
                "door_name": self.door.door_name,
            }
        embedding = self.face_ai.face_recog.get_face_embedding(cropped)
        templates = self.db.templates()
        if embedding is None or not templates:
            reason = "No face template" if embedding is None else "No registered people"
            return {
                "ok": False,
                "decision": "denied",
                "message": reason,
                "score": 0.0,
                "door_id": self.door.door_id,
                "door_name": self.door.door_name,
            }
        matrix = np.vstack([t["embedding"] for t in templates]).astype(np.float32)
        scores = matrix @ embedding.astype(np.float32)
        best_index = int(np.argmax(scores))
        best = templates[best_index]
        score = float(scores[best_index])
        threshold = self.door.threshold
        known = score >= threshold
        person = best if known else None
        decision = "granted"
        reason = "Face matched and door permission granted"
        if not known:
            decision = "denied"
            # Never attach a name to a face that did not clear the threshold.
            reason = "Face not recognised. Try again or contact the administrator."
        elif not person["active"]:
            decision = "denied"
            reason = "This person is inactive"
        elif not self._allowed(person, self.door.door_id):
            decision = "denied"
            reason = f"{person['full_name']} is not allowed at {self.door.door_name}"
        now = time.monotonic()
        if decision == "granted" and (now - self._last_grant) < self.door.cooldown_seconds:
            decision = "denied"
            reason = "Cooldown: please wait before scanning again"

        snapshot = self._save_snapshot(frame, "access")
        event = {
            "ts": _now(),
            "person_id": person["person_id"] if person else None,
            "person_name": person["full_name"] if person else "",
            "door_id": self.door.door_id,
            "door_name": self.door.door_name,
            "score": score,
            "decision": decision,
            "reason": reason,
            "snapshot_path": snapshot,
        }
        door_result = None
        if decision == "granted":
            door_result = self.door.unlock(event)
            if not door_result.get("ok"):
                decision = "error"
                reason = door_result.get("detail", "Door controller failed")
            else:
                self._last_grant = now
        event["decision"] = decision
        event["reason"] = reason
        event_id = self.db.log_event(event)
        return {
            "ok": decision == "granted",
            "decision": decision,
            "message": reason,
            "score": score,
            "threshold": threshold,
            "door_id": self.door.door_id,
            "door_name": self.door.door_name,
            "door_controller": self.door.controller,
            "door_detail": (door_result or {}).get("detail", ""),
            "door_ok": bool(door_result and door_result.get("ok")),
            "person": person,
            "person_id": person["person_id"] if person else None,
            "person_name": person["full_name"] if person else "",
            "role": person["role"] if person else "",
            "department": person["department"] if person else "",
            "external_id": person["external_id"] if person else "",
            "ts": event["ts"],
            "event_id": event_id,
        }

    # -- convenience for the UI -----------------------------------
    def list_people(self):
        return self.db.list_people()

    def delete_person(self, person_id):
        self.db.delete_person(person_id)

    def list_events(self, limit=50):
        return self.db.list_events(limit)

    def export_events(self, path):
        return self.db.export_events(path)
