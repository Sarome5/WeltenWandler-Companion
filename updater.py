import os
import sys
import zipfile
import shutil
import requests

ADDON_REPO  = "Sarome5/WeltenWandler-Raid-Tool"
SELF_REPO   = "Sarome5/WeltenWandler-Companion"
GH_API      = "https://api.github.com/repos/{}/releases/latest"

CURRENT_VERSION = "0.1.0"


def _get_latest(repo: str) -> tuple[str, str] | tuple[None, None]:
    """Gibt (tag_version, download_url) des neuesten Releases zurück."""
    try:
        r = requests.get(GH_API.format(repo), timeout=10)
        if r.status_code != 200:
            return None, None
        data     = r.json()
        tag      = data.get("tag_name", "").lstrip("v")
        assets   = data.get("assets", [])
        zip_url  = next((a["browser_download_url"] for a in assets if a["name"].endswith(".zip")), None)
        return tag, zip_url
    except Exception:
        return None, None


def _version_newer(remote: str, local: str) -> bool:
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return False


# --------------------------------------------------
# ADDON UPDATE
# --------------------------------------------------
def check_addon_update(addon_path: str, current_version: str) -> tuple[bool, str]:
    """Gibt (update_verfügbar, neue_version) zurück."""
    tag, _ = _get_latest(ADDON_REPO)
    if tag and _version_newer(tag, current_version):
        return True, tag
    return False, current_version


def update_addon(addon_path: str) -> bool:
    """Lädt neuestes Addon-Release herunter und entpackt es."""
    tag, zip_url = _get_latest(ADDON_REPO)
    if not zip_url:
        return False

    tmp_zip = os.path.join(os.path.dirname(addon_path), "_wrt_update.zip")
    try:
        r = requests.get(zip_url, timeout=30)
        with open(tmp_zip, "wb") as f:
            f.write(r.content)

        parent = os.path.dirname(addon_path)
        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(parent)

        os.remove(tmp_zip)
        return True
    except Exception as e:
        print(f"[Updater] Addon-Update fehlgeschlagen: {e}")
        return False


# --------------------------------------------------
# SELF UPDATE
# --------------------------------------------------
def check_self_update() -> tuple[bool, str]:
    """Gibt (update_verfügbar, neue_version) zurück."""
    tag, _ = _get_latest(SELF_REPO)
    if tag and _version_newer(tag, CURRENT_VERSION):
        return True, tag
    return False, CURRENT_VERSION


def update_self() -> bool:
    """
    Lädt neue .exe herunter, ersetzt die aktuelle und startet neu.
    Funktioniert nur im kompilierten (PyInstaller) Modus.
    """
    tag, zip_url = _get_latest(SELF_REPO)
    if not zip_url:
        return False

    try:
        r = requests.get(zip_url, timeout=30)
        tmp_zip = os.path.join(os.path.dirname(sys.executable), "_companion_update.zip")
        with open(tmp_zip, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(os.path.dirname(sys.executable))

        os.remove(tmp_zip)

        # Neustart
        os.execv(sys.executable, sys.argv)
        return True
    except Exception as e:
        print(f"[Updater] Self-Update fehlgeschlagen: {e}")
        return False
