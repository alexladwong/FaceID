import datetime
import json
import os
import tempfile
import time
import unittest

import numpy as np

from services.access import (
    AccessSvc,
    DoorController,
    KeyboardWedgeCardReader,
    NullCardReader,
    _normalize_card_uid,
)


class FakeDetect:
    session = object()

    def get_single_face_cropped(self, frame):
        return frame


class FakeRecog:
    session = object()

    def get_face_embedding(self, image):
        label = int(image[0, 0, 0])
        if label == 0:
            return np.array([1.0, 0.0], dtype=np.float32)
        if label == 1:
            return np.array([0.0, 1.0], dtype=np.float32)
        return np.array([-1.0, 0.0], dtype=np.float32)


class FakeFaceAi:
    face_detect = FakeDetect()
    face_recog = FakeRecog()


def frame(label=0):
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image[0, 0, 0] = label
    return image


BASE_CONFIG = {
    "door_id": "main-gate",
    "door_name": "Main Gate",
    "controller": "simulated",
    "webhook_url": "",
    "secret": "",
    "threshold": 0.65,
    "cooldown_seconds": 0,
    "allowed_methods": ["face", "pin", "card", "admin"],
    "require_two_factor": False,
    "pin_max_attempts": 5,
    "pin_lockout_seconds": 300,
    "card_reader": "keyboard_wedge",
    "liveness_provider": "none",
    "fail_mode": "fail_secure",
    "admin_roles": ["admin", "security"],
    "admin_second_approver": False,
    "open_start": "00:00",
    "open_end": "23:59",
    "open_days": "0,1,2,3,4,5,6",
}


class AccessSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="faceai_access_test_")
        self.config = dict(BASE_CONFIG)
        self.config_path = os.path.join(self.tmp.name, "doors.json")
        self._write_config()
        self.svc = AccessSvc(
            os.path.join(self.tmp.name, "access.db"),
            FakeFaceAi(),
            self.config_path,
            os.path.join(self.tmp.name, "snaps"),
        )
        self.admin = self._bootstrap_admin()

    def tearDown(self):
        self.svc.db.conn.close()
        self.tmp.cleanup()

    def _write_config(self, **updates):
        data = dict(self.config)
        data.update(updates)
        with open(self.config_path, "w") as f:
            json.dump(data, f)

    def _new_svc(self, config=None, card_reader=None):
        if config:
            self.config.update(config)
            self._write_config()
        return AccessSvc(
            os.path.join(self.tmp.name, "access2.db"),
            FakeFaceAi(),
            self.config_path,
            os.path.join(self.tmp.name, "snaps2"),
            card_reader=card_reader,
        )

    def _bootstrap_admin(self):
        result = self.svc.register_person(
            {
                "full_name": "Admin User",
                "external_id": "ADM-1",
                "role": "Admin",
                "doors": "all",
            },
            frame(0),
        )
        self.assertTrue(result["ok"], result)
        person_id = result["person"]["id"]
        pin = self.svc.set_pin(person_id, "1234")
        self.assertTrue(pin["ok"], pin)
        return result["person"]

    def _add_staff(self, name="Staff One", external_id="STF-1", doors="all", frame_label=1, pin="2468", schedule_days="0,1,2,3,4,5,6"):
        result = self.svc.register_person(
            {
                "full_name": name,
                "external_id": external_id,
                "role": "Staff",
                "department": "Works",
                "doors": doors,
                "schedule_days": schedule_days,
            },
            frame(frame_label),
            actor_ref="ADM-1",
            actor_pin="1234",
        )
        self.assertTrue(result["ok"], result)
        person_id = result["person"]["id"]
        pin_result = self.svc.set_pin(person_id, pin, actor_ref="ADM-1", actor_pin="1234")
        self.assertTrue(pin_result["ok"], pin_result)
        return result["person"]

    # -- face ------------------------------------------------------
    def test_face_grant_and_unknown_denial(self):
        staff = self._add_staff()
        granted = self.svc.authenticate_face(frame(1))
        self.assertEqual(granted["decision"], "granted", granted)
        self.assertEqual(granted["person_name"], staff["full_name"])
        self.assertEqual(granted["method"], "face")

        unknown = self.svc.authenticate_face(frame(2))
        self.assertEqual(unknown["decision"], "denied")
        self.assertIsNone(unknown["person_id"])
        self.assertNotIn("Staff One", unknown["message"])

    def test_face_blocked_for_webhook_without_liveness(self):
        svc = self._new_svc(
            {
                "controller": "webhook",
                "webhook_url": "http://127.0.0.1:1/unlock",
                "liveness_provider": "none",
            }
        )
        result = svc.authenticate_face(frame(0))
        self.assertEqual(result["decision"], "error")
        self.assertFalse(result["door_ok"])
        self.assertIn("Liveness", result["message"])

    # -- PIN -------------------------------------------------------
    def test_pin_is_hashed_and_not_logged(self):
        person = self.svc.db.get_person(self.admin["id"])
        self.assertNotEqual(person["pin_hash"], "1234")
        self.assertTrue(person["pin_salt"])
        result = self.svc.authenticate_pin("ADM-1", "1234")
        self.assertEqual(result["decision"], "granted")
        events = self.svc.list_events(20)
        self.assertFalse(any("1234" in (e.get("reason", "") + e.get("credential_ref", "")) for e in events))

    def test_pin_denial_lockout_and_recovery(self):
        self._write_config(pin_max_attempts=2, pin_lockout_seconds=1)
        self.svc.door.reload()
        staff = self._add_staff(pin="2468")
        first = self.svc.authenticate_pin("STF-1", "0000")
        second = self.svc.authenticate_pin("STF-1", "0000")
        locked = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(first["decision"], "denied")
        self.assertEqual(second["decision"], "denied")
        self.assertEqual(locked["decision"], "denied")
        self.assertIn("locked", locked["message"].lower())
        time.sleep(1.1)
        recovered = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(recovered["decision"], "granted", recovered)

    def test_pin_revocation_and_management_authorization(self):
        staff = self._add_staff()
        no_admin = self.svc.set_pin(staff["id"], "9999")
        self.assertFalse(no_admin["ok"])
        revoked = self.svc.revoke_pin(staff["id"], actor_ref="ADM-1", actor_pin="1234")
        self.assertTrue(revoked["ok"])
        denied = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(denied["decision"], "denied")
        self.assertIn("revoked", denied["message"].lower())

    def test_unknown_pin_does_not_disclose_person(self):
        result = self.svc.authenticate_pin("NOPE", "1234")
        self.assertEqual(result["decision"], "denied")
        self.assertIsNone(result["person_id"])
        self.assertNotIn("Admin", result["message"])

    # -- cards -----------------------------------------------------
    def test_card_valid_expired_lost_revoked_and_unavailable(self):
        staff = self._add_staff()
        assigned = self.svc.assign_card(
            staff["id"], "AA:BB:CC:DD", actor_ref="ADM-1", actor_pin="1234"
        )
        self.assertTrue(assigned["ok"], assigned)
        card = self.svc.db.list_cards(staff["id"])[0]
        valid = self.svc.authenticate_card("AABBCCDD")
        self.assertEqual(valid["decision"], "granted", valid)
        self.assertNotIn("AABBCCDD", valid["credential_ref"])

        expired = self.svc.assign_card(
            staff["id"], "11223344",
            valid_until=(datetime.date.today() - datetime.timedelta(days=1)).isoformat(),
            actor_ref="ADM-1", actor_pin="1234",
        )
        self.assertTrue(expired["ok"], expired)
        self.assertEqual(self.svc.authenticate_card("11223344")["decision"], "denied")

        lost = self.svc.revoke_card(card["id"], actor_ref="ADM-1", actor_pin="1234", lost=True)
        self.assertTrue(lost["ok"])
        self.assertIn("lost", self.svc.authenticate_card("AABBCCDD")["message"].lower())

        no_reader = AccessSvc(
            os.path.join(self.tmp.name, "noreader.db"),
            FakeFaceAi(),
            self.config_path,
            os.path.join(self.tmp.name, "snaps3"),
            card_reader=NullCardReader(),
        )
        self.assertEqual(no_reader.authenticate_card("AABBCCDD")["decision"], "unavailable")

    def test_card_invalid_and_revoked(self):
        self.assertEqual(
            self.svc.authenticate_card("!!!")["decision"], "denied"
        )
        self.assertEqual(
            self.svc.authenticate_card("FFFFFFFF")["decision"], "denied"
        )

    # -- policy ----------------------------------------------------
    def test_door_permissions_and_schedules(self):
        staff = self._add_staff(doors="other-gate")
        denied = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(denied["decision"], "denied")
        self.assertIn("not allowed", denied["message"].lower())

        staff2 = self._add_staff(
            "Schedule Staff", "STF-2", doors="all", frame_label=1, pin="1111",
            schedule_days=",".join(str(d) for d in range(7) if d != datetime.date.today().weekday()),
        )
        denied2 = self.svc.authenticate_pin("STF-2", "1111")
        self.assertEqual(denied2["decision"], "denied")
        self.assertIn("access days", denied2["message"].lower())

        self.svc.update_person(
            staff["id"], {"doors": "all"}, actor_ref="ADM-1", actor_pin="1234"
        )
        self.svc.door.config["open_days"] = str(
            (datetime.date.today().weekday() + 1) % 7
        )
        denied3 = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(denied3["decision"], "denied")
        self.assertIn("closed", denied3["message"].lower())

    def test_two_factor_face_requires_pin(self):
        staff = self._add_staff()
        self._write_config(require_two_factor=True)
        self.svc.door.reload()
        challenge = self.svc.authenticate_face(frame(1))
        self.assertEqual(challenge["decision"], "second_factor_required", challenge)
        self.assertTrue(challenge.get("challenge_token"))
        self.assertEqual(challenge["person_id"], staff["id"])
        granted = self.svc.complete_challenge(challenge["challenge_token"], "2468")
        self.assertEqual(granted["decision"], "granted", granted)

    def test_two_factor_pin_alone_is_denied(self):
        self._write_config(require_two_factor=True)
        self.svc.door.reload()
        result = self.svc.authenticate_pin("ADM-1", "1234")
        self.assertEqual(result["decision"], "denied")
        self.assertIn("two", result["message"].lower())

    def test_two_factor_card_requires_pin(self):
        staff = self._add_staff()
        self.svc.assign_card(staff["id"], "99887766", actor_ref="ADM-1", actor_pin="1234")
        self._write_config(require_two_factor=True)
        self.svc.door.reload()
        challenge = self.svc.authenticate_card("99887766")
        self.assertEqual(challenge["decision"], "second_factor_required", challenge)
        granted = self.svc.complete_challenge(challenge["challenge_token"], "2468")
        self.assertEqual(granted["decision"], "granted", granted)

    # -- admin assistance -----------------------------------------
    def test_admin_assistance_requires_reason_and_records_approval(self):
        staff = self._add_staff()
        no_reason = self.svc.authorize_admin_access("ADM-1", "1234", staff["id"], "x")
        self.assertEqual(no_reason["decision"], "denied")
        denied = self.svc.authorize_admin_access("ADM-1", "wrong", staff["id"], "Delivery assistance")
        self.assertEqual(denied["decision"], "denied")
        granted = self.svc.authorize_admin_access(
            "ADM-1", "1234", staff["id"], "Delivery assistance at loading bay"
        )
        self.assertEqual(granted["decision"], "granted", granted)
        self.assertEqual(granted["method"], "admin")
        self.assertEqual(granted["person_id"], staff["id"])
        events = self.svc.list_events(5)
        self.assertTrue(any(e.get("admin_name") == "Admin User" for e in events))

    def test_admin_cannot_self_authorize_or_override_suspension(self):
        staff = self._add_staff()
        self_approve = self.svc.authorize_admin_access(
            "ADM-1", "1234", self.admin["id"], "Self access"
        )
        self.assertEqual(self_approve["decision"], "denied")
        suspended = self.svc.set_active(staff["id"], False, actor_ref="ADM-1", actor_pin="1234")
        self.assertTrue(suspended["ok"])
        denied = self.svc.authorize_admin_access(
            "ADM-1", "1234", staff["id"], "Suspended assistance"
        )
        self.assertEqual(denied["decision"], "denied")

    def test_second_admin_approver_required(self):
        staff = self._add_staff()
        second = self.svc.register_person(
            {
                "full_name": "Second Admin",
                "external_id": "ADM-2",
                "role": "Security",
                "doors": "all",
            },
            frame(0),
            actor_ref="ADM-1",
            actor_pin="1234",
        )
        self.assertTrue(second["ok"], second)
        self.assertTrue(
            self.svc.set_pin(second["person"]["id"], "5678", actor_ref="ADM-1", actor_pin="1234")["ok"]
        )
        self._write_config(admin_second_approver=True)
        self.svc.door.reload()
        no_approver = self.svc.authorize_admin_access(
            "ADM-1", "1234", staff["id"], "Exceptional access"
        )
        self.assertEqual(no_approver["decision"], "denied")
        approved = self.svc.authorize_admin_access(
            "ADM-1", "1234", staff["id"], "Exceptional access",
            approver_ref="ADM-2", approver_pin="5678",
        )
        self.assertEqual(approved["decision"], "granted", approved)

    # -- controller / audit ---------------------------------------
    def test_controller_failure_never_grants(self):
        staff = self._add_staff()
        self._write_config(
            controller="webhook",
            webhook_url="http://127.0.0.1:1/unlock",
        )
        self.svc.door.reload()
        result = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(result["decision"], "error")
        self.assertFalse(result["door_ok"])
        self.assertFalse(result["ok"])

    def test_duplicate_unlock_key_is_suppressed(self):
        config = os.path.join(self.tmp.name, "dup.json")
        with open(config, "w") as f:
            json.dump(BASE_CONFIG, f)
        door = DoorController(config)
        event = {"event_key": "fixed-key", "door_id": "main-gate"}
        first = door.unlock(event)
        second = door.unlock(event)
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertTrue(second.get("duplicate"))

    def test_cooldown_blocks_immediate_repeat(self):
        self._write_config(cooldown_seconds=30)
        self.svc.door.reload()
        staff = self._add_staff()
        first = self.svc.authenticate_pin("STF-1", "2468")
        second = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(first["decision"], "granted")
        self.assertEqual(second["decision"], "denied")
        self.assertIn("cooldown", second["message"].lower())

    def test_export_has_no_pin_or_full_card(self):
        staff = self._add_staff()
        self.svc.assign_card(staff["id"], "A1B2C3D4", actor_ref="ADM-1", actor_pin="1234")
        self.svc.authenticate_pin("STF-1", "2468")
        self.svc.authenticate_card("A1B2C3D4")
        path = os.path.join(self.tmp.name, "audit.csv")
        self.svc.export_events(path)
        with open(path) as f:
            content = f.read()
        self.assertNotIn("2468", content)
        self.assertNotIn("A1B2C3D4", content)
        self.assertIn("pin", content)
        self.assertIn("card", content)

    def test_revoked_card_is_rejected(self):
        staff = self._add_staff()
        self.svc.assign_card(staff["id"], "DEADBEEF", actor_ref="ADM-1", actor_pin="1234")
        card = self.svc.db.list_cards(staff["id"])[0]
        revoked = self.svc.revoke_card(card["id"], actor_ref="ADM-1", actor_pin="1234")
        self.assertTrue(revoked["ok"])
        denied = self.svc.authenticate_card("DEADBEEF")
        self.assertEqual(denied["decision"], "denied")
        self.assertIn("revoked", denied["message"].lower())

    def test_face_engine_unavailable_is_a_failure(self):
        svc = AccessSvc(
            os.path.join(self.tmp.name, "noface.db"),
            None,
            self.config_path,
            os.path.join(self.tmp.name, "snaps_noface"),
        )
        result = svc.authenticate_face(frame(0))
        self.assertEqual(result["decision"], "error")
        self.assertFalse(result["ok"])
        self.assertIn("engine", result["message"].lower())

    def test_last_administrator_cannot_be_removed(self):
        denied_revoke = self.svc.revoke_pin(
            self.admin["id"], actor_ref="ADM-1", actor_pin="1234"
        )
        self.assertFalse(denied_revoke["ok"])
        denied_suspend = self.svc.set_active(
            self.admin["id"], False, actor_ref="ADM-1", actor_pin="1234"
        )
        self.assertFalse(denied_suspend["ok"])
        denied_delete = self.svc.delete_person(
            self.admin["id"], actor_ref="ADM-1", actor_pin="1234"
        )
        self.assertFalse(denied_delete["ok"])
        denied_role = self.svc.update_person(
            self.admin["id"], {"role": "Staff"}, actor_ref="ADM-1", actor_pin="1234"
        )
        self.assertFalse(denied_role["ok"])

    def test_credential_management_requires_admin(self):
        staff = self._add_staff()
        denied = self.svc.revoke_pin(staff["id"])
        self.assertFalse(denied["ok"])
        denied_card = self.svc.assign_card(staff["id"], "12345678")
        self.assertFalse(denied_card["ok"])

    def test_face_enrollment_is_admin_authorized(self):
        staff = self._add_staff()
        before = self.svc.db.face_count(staff["id"])
        denied = self.svc.enroll_face(staff["id"], frame(1))
        self.assertFalse(denied["ok"])
        result = self.svc.enroll_face(
            staff["id"], frame(1), actor_ref="ADM-1", actor_pin="1234"
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.svc.db.face_count(staff["id"]), before + 1)

    def test_webhook_requires_a_secret_and_never_opens(self):
        staff = self._add_staff()
        self._write_config(
            controller="webhook",
            webhook_url="http://127.0.0.1:1/unlock",
            secret="",
        )
        self.svc.door.reload()
        self.assertFalse(self.svc.controller_status()["ok"])
        result = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(result["decision"], "error")
        self.assertFalse(result["door_ok"])

    def test_remote_http_controller_is_refused(self):
        staff = self._add_staff()
        self._write_config(
            controller="webhook",
            webhook_url="http://example.com/unlock",
            secret="test-secret",
        )
        self.svc.door.reload()
        status = self.svc.controller_status()
        self.assertFalse(status["ok"])
        result = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(result["decision"], "error")
        self.assertIn("HTTPS", result["message"])

    def test_method_disablement_applies_to_every_caller(self):
        self._add_staff()
        self._write_config(allowed_methods=["pin"])
        self.svc.door.reload()
        face = self.svc.authenticate_face(frame(1))
        self.assertEqual(face["decision"], "error")
        pin = self.svc.authenticate_pin("STF-1", "2468")
        self.assertEqual(pin["decision"], "granted")

    def test_audit_events_for_credential_changes(self):
        staff = self._add_staff()
        actions = {row["action"] for row in self.svc.list_audit(50)}
        self.assertIn("person_enrolled", actions)
        self.assertIn("pin_set", actions)
        self.assertIn("admin_auth", actions)


if __name__ == "__main__":
    unittest.main()
