import os
import sys
import zipfile
import requests

ADDON_REPO_OWNER = "Sarome5"
ADDON_REPO_NAME  = "WeltenWandler-Raid-Tool"
SELF_REPO        = "Sarome5/WeltenWandler-Companion"
GH_API           = "https://api.github.com/repos/{}/releases/latest"

CURRENT_VERSION = "1.0.5"


def _version_newer(remote: str, local: str) -> bool:
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return False


# --------------------------------------------------
# ADDON UPDATE (Branch-basiert)
# --------------------------------------------------

def _toc_version_remote(branch: str) -> str | None:
    """Liest ## Version aus der .toc-Datei des gewählten Branches auf GitHub."""
    url = (
        f"https://raw.githubusercontent.com/{ADDON_REPO_OWNER}/"
        f"{ADDON_REPO_NAME}/{branch}/WeltenWandler_Raid_Tool.toc"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            for line in r.text.splitlines():
                if line.startswith("## Version:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def _toc_version_local(addon_path: str) -> str:
    """Liest ## Version aus der lokalen .toc-Datei."""
    toc = os.path.join(addon_path, "WeltenWandler_Raid_Tool.toc")
    try:
        with open(toc, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("## Version:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "0.0.0"


def check_addon_update(addon_path: str, current_version: str = "", branch: str = "master") -> tuple[bool, str]:
    """Gibt (update_verfügbar, remote_version) zurück."""
    local_ver  = _toc_version_local(addon_path) or current_version or "0.0.0"
    remote_ver = _toc_version_remote(branch)
    if remote_ver and _version_newer(remote_ver, local_ver):
        return True, remote_ver
    return False, remote_ver or local_ver


def update_addon(addon_path: str, branch: str = "master") -> bool:
    """Lädt den gewählten Branch als ZIP herunter und entpackt ihn ins Addon-Verzeichnis."""
    zip_url = (
        f"https://github.com/{ADDON_REPO_OWNER}/{ADDON_REPO_NAME}"
        f"/archive/refs/heads/{branch}.zip"
    )
    tmp_zip = os.path.join(os.path.dirname(addon_path), "_wrt_update.zip")
    try:
        r = requests.get(zip_url, timeout=30)
        r.raise_for_status()
        with open(tmp_zip, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(tmp_zip, "r") as z:
            names = z.namelist()
            # ZIP-Wurzel automatisch erkennen (erstes Top-Level-Verzeichnis)
            zip_root = next((m for m in names if m.endswith("/") and m.count("/") == 1), None)
            if not zip_root:
                raise ValueError(f"ZIP-Struktur unbekannt: {names[:5]}")

            for member in names:
                if not member.startswith(zip_root):
                    continue
                relative = member[len(zip_root):]
                if not relative:
                    continue
                # data/*.lua nicht überschreiben (companion-generierte Dateien)
                if relative.startswith("data/"):
                    continue
                target = os.path.join(addon_path, relative.replace("/", os.sep))
                if member.endswith("/"):
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())

        os.remove(tmp_zip)
        return True
    except Exception as e:
        print(f"[Updater] Addon-Update fehlgeschlagen: {e}", flush=True)
        try:
            os.remove(tmp_zip)
        except Exception:
            pass
        return False


# --------------------------------------------------
# SELF UPDATE
# --------------------------------------------------
def _get_latest_self() -> tuple[str, str] | tuple[None, None]:
    """Gibt (version, installer_url) des neuesten Releases zurück."""
    try:
        r = requests.get(GH_API.format(SELF_REPO), timeout=10)
        if r.status_code != 200:
            return None, None
        data        = r.json()
        tag         = data.get("tag_name", "").lstrip("v")
        assets      = data.get("assets", [])
        # Installer-Asset: erste .exe im Release
        installer   = next((a["browser_download_url"] for a in assets if a["name"].endswith(".exe")), None)
        return tag, installer
    except Exception:
        return None, None


def check_self_update() -> tuple[bool, str]:
    tag, _ = _get_latest_self()
    if tag and _version_newer(tag, CURRENT_VERSION):
        return True, tag
    return False, CURRENT_VERSION


def update_self(on_status=None) -> bool:
    """
    Lädt den neuen Installer herunter und führt ihn silent aus.
    Der Installer beendet die laufende App automatisch und startet sie danach neu.
    Funktioniert nur im kompilierten (PyInstaller) Modus.
    on_status: optionaler Callback (str) für Statusmeldungen an die GUI.
    """
    def _status(msg: str):
        print(f"[Updater] {msg}", flush=True)
        if on_status:
            try:
                on_status(msg)
            except Exception:
                pass

    tag, installer_url = _get_latest_self()
    if not installer_url:
        _status("Kein Update gefunden.")
        return False

    try:
        import tempfile
        import subprocess

        _status(f"Download läuft… (v{tag})")
        r = requests.get(installer_url, timeout=120)
        r.raise_for_status()

        tmp_dir        = tempfile.mkdtemp()
        installer_path = os.path.join(tmp_dir, f"WeltenWandler-Companion-Setup-v{tag}.exe")
        with open(installer_path, "wb") as f:
            f.write(r.content)

        _status("Wird installiert…")
        # /SILENT: kein Wizard, aber Fortschrittsanzeige
        # /CLOSEAPPLICATIONS: schließt laufende Instanzen automatisch
        subprocess.Popen(
            [installer_path, "/SILENT", "/CLOSEAPPLICATIONS"],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        # App beenden – der Installer übernimmt den Rest
        os._exit(0)
    except Exception as e:
        _status(f"Update fehlgeschlagen.")
        print(f"[Updater] Self-Update fehlgeschlagen: {e}")
        return False
