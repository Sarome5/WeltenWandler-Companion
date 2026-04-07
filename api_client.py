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
    def get_stats(self) -> dict | None:
        """Statistiken (Loothistorie, Spieler-Stats, Dropchance) abrufen."""
        try:
            r = requests.get(
                f"{self.base_url}/api/companion/stats",
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
