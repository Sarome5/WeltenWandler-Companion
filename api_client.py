import requests
import keyring
import sseclient

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
    def login(self, username: str, password: str) -> bool:
        """Einloggen und JWT-Token speichern. Gibt True bei Erfolg zurück."""
        try:
            r = requests.post(
                f"{self.base_url}/api/companion/login",
                json={"username": username, "password": password},
                timeout=10,
            )
            if r.status_code == 200:
                self.token = r.json().get("token")
                save_token(self.token)
                return True
        except Exception:
            pass
        return False

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
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                self.logout()
        except Exception:
            pass
        return None

    # --------------------------------------------------
    # SSE STREAM
    # --------------------------------------------------
    def stream(self):
        """
        Generator: liefert SSE-Events vom Server.
        Wirft Exception wenn Verbindung abbricht → Aufrufer reconnectet.
        """
        r = requests.get(
            f"{self.base_url}/api/companion/stream",
            headers={**self._headers(), "Accept": "text/event-stream"},
            stream=True,
            timeout=None,
        )
        client = sseclient.SSEClient(r)
        for event in client.events():
            yield event
