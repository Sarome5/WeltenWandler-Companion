import requests
import keyring
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KEYRING_SERVICE = "WRT-Companion"
KEYRING_TOKEN   = "jwt_token"


def save_token(token: str):
    keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN, token)


def load_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN)


def clear_token():
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_TOKEN)
    except Exception:
        pass


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token    = load_token()

    def _headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------
    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Einloggen und JWT-Token speichern. Gibt (True, "") oder (False, Fehlermeldung) zurück."""
        try:
            r = requests.post(
                f"{self.base_url}/api/companion/login",
                json={"username": username, "password": password},
                timeout=10,
                verify=False,  # Dev-Zertifikate akzeptieren
            )
            if r.status_code == 200:
                self.token = r.json().get("token")
                save_token(self.token)
                return True, ""
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            return False, str(e)

    def is_logged_in(self) -> bool:
        return self.token is not None

    def logout(self):
        self.token = None
        clear_token()

    # --------------------------------------------------
    # RAID
    # --------------------------------------------------
    def get_raid(self) -> dict | None:
        """Aktuellen Raid mit Anmelde- und Prio-Status abrufen."""
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/raid",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    # --------------------------------------------------
    # STATS
    # --------------------------------------------------
    def get_stats(self, patch_id=None, difficulty=None, loot_scope=None) -> dict | None:
        """Statistiken (Loothistorie, Spieler-Stats, Dropchance) abrufen."""
        try:
            params = {}
            if patch_id is not None:
                params["patch_id"] = patch_id
            if difficulty and difficulty != "all":
                params["difficulty"] = difficulty
            if loot_scope and loot_scope != "all":
                params["loot_scope"] = loot_scope
            r = requests.get(
                f"{self.base_url}/api/companion/stats",
                headers=self._headers(),
                params=params,
                timeout=15,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    # --------------------------------------------------
    # ADMIN
    # --------------------------------------------------
    def _admin_get(self, path: str) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/api/companion/admin/{path}",
                             headers=self._headers(), timeout=15, verify=False)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    def _admin_post(self, path: str, json_data=None) -> dict:
        try:
            r = requests.post(f"{self.base_url}/api/companion/admin/{path}",
                              headers=self._headers(), json=json_data, timeout=15, verify=False)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _admin_put(self, path: str, json_data=None) -> dict:
        try:
            r = requests.put(f"{self.base_url}/api/companion/admin/{path}",
                             headers=self._headers(), json=json_data, timeout=15, verify=False)
            if r.status_code == 200:
                return r.json()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _admin_delete(self, path: str) -> dict:
        try:
            r = requests.delete(f"{self.base_url}/api/companion/admin/{path}",
                                headers=self._headers(), timeout=15, verify=False)
            if r.status_code == 200:
                return r.json()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def admin_get_raids(self)            -> dict | None: return self._admin_get("raids")
    def admin_get_raid(self, raid_id)    -> dict | None: return self._admin_get(f"raids/{raid_id}")
    def admin_create_raid(self, data)    -> dict:        return self._admin_post("raids", data)
    def admin_update_raid(self, rid, d)  -> dict:        return self._admin_put(f"raids/{rid}", d)
    def admin_toggle_publish(self, rid)  -> dict:        return self._admin_post(f"raids/{rid}/publish")
    def admin_archive_raid(self, rid)    -> dict:        return self._admin_post(f"raids/{rid}/archive")
    def admin_get_archive(self)          -> dict | None: return self._admin_get("raids/archive")
    def admin_unarchive_raid(self, rid)  -> dict:        return self._admin_post(f"raids/{rid}/unarchive")
    def admin_delete_raid(self, rid)     -> dict:        return self._admin_delete(f"raids/{rid}")
    def admin_get_users(self)            -> dict | None: return self._admin_get("users")
    def admin_set_role(self, uid, role)  -> dict:        return self._admin_post(f"users/{uid}/role", {"role": role})
    def admin_set_prio_cap(self, uid, p) -> dict:        return self._admin_post(f"users/{uid}/prio-cap", {"prio_cap": p})
    def admin_reset_password(self, uid)  -> dict:        return self._admin_post(f"users/{uid}/reset-password")
    def admin_delete_user(self, uid)     -> dict:        return self._admin_delete(f"users/{uid}")
    def admin_get_form_patches(self)     -> list:
        data = self._admin_get("form-patches")
        return (data or {}).get("patches", [])

    def get_patches(self) -> list:
        """Verfügbare Lootlisten (Patches) abrufen."""
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/patches",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json().get("patches", [])
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return []

    # --------------------------------------------------
    # PROFIL & CHARAKTERE
    # --------------------------------------------------
    def get_profile(self) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/api/companion/profile",
                             headers=self._headers(), timeout=10, verify=False)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    def get_characters(self) -> list:
        try:
            r = requests.get(f"{self.base_url}/api/companion/characters",
                             headers=self._headers(), timeout=10, verify=False)
            if r.status_code == 200:
                return r.json().get("characters", [])
        except Exception:
            pass
        return []

    def create_character(self, name: str, wow_class: str, wow_spec: str) -> dict:
        try:
            r = requests.post(f"{self.base_url}/api/companion/characters",
                              headers=self._headers(),
                              json={"name": name, "wowClass": wow_class, "wowSpec": wow_spec},
                              timeout=10, verify=False)
            if r.status_code in (200, 409):
                return r.json()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_character(self, char_id: int, name: str, wow_class: str, wow_spec: str) -> dict:
        try:
            r = requests.put(f"{self.base_url}/api/companion/characters/{char_id}",
                             headers=self._headers(),
                             json={"name": name, "wowClass": wow_class, "wowSpec": wow_spec},
                             timeout=10, verify=False)
            if r.status_code == 200:
                return r.json()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def activate_character(self, char_id: int) -> dict:
        try:
            r = requests.post(f"{self.base_url}/api/companion/characters/{char_id}/activate",
                              headers=self._headers(), timeout=10, verify=False)
            if r.status_code == 200:
                return r.json()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --------------------------------------------------
    # NEWS
    # --------------------------------------------------
    def get_pending_news(self) -> dict | None:
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/news/pending",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json().get("news")
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    def confirm_news(self, news_id: int) -> bool:
        try:
            r = requests.post(
                f"{self.base_url}/api/companion/news/{news_id}/confirm",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            return r.status_code == 200
        except Exception:
            return False

    # --------------------------------------------------
    # SIGNUP / PRIO
    # --------------------------------------------------
    def change_signup(self, raid_id: int, status: str) -> dict:
        try:
            r = requests.post(
                f"{self.base_url}/api/companion/raids/{raid_id}/signup",
                headers=self._headers(),
                json={"status": status},
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 403:
                return {"success": False, "error": "deadline_passed"}
            if r.status_code == 401:
                self.logout()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_raid_loot(self, raid_id: int) -> dict | None:
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/raids/{raid_id}/loot",
                headers=self._headers(),
                timeout=15,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    def get_prio_list(self, raid_id: int) -> dict | None:
        """Vollständige Prioliste aller Spieler für einen Raid (nur officer+)."""
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/raids/{raid_id}/full-prios",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                pass  # Kein Zugriff → ignorieren
        except Exception:
            pass
        return None

    def save_prio(self, raid_id: int, difficulty: str, slots: list) -> dict:
        try:
            r = requests.post(
                f"{self.base_url}/api/companion/raids/{raid_id}/prio",
                headers=self._headers(),
                json={"difficulty": difficulty, "slots": slots},
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --------------------------------------------------
    # POLLING EVENTS
    # --------------------------------------------------
    def get_events(self, since: int = 0) -> dict | None:
        """Fragt ab ob seit <since> ein Raid live geschaltet wurde."""
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/events",
                headers=self._headers(),
                params={"since": since},
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception as e:
            print(f"[Polling] Fehler: {e}")
        return None

    # --------------------------------------------------
    # BLACKLIST
    # --------------------------------------------------
    def get_blacklist(self) -> list:
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/blacklist",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json().get("blacklist", [])
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return []

    def add_blacklist_item(self, item_id: int, note: str = "") -> dict:
        try:
            r = requests.post(
                f"{self.base_url}/api/companion/blacklist",
                headers=self._headers(),
                json={"item_id": item_id, "note": note},
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_blacklist_item(self, bl_id: int) -> dict:
        try:
            r = requests.delete(
                f"{self.base_url}/api/companion/blacklist/{bl_id}",
                headers=self._headers(),
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
