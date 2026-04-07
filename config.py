import json
import os
import winreg

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULTS = {
    "api_url":    "http://localhost:5000",
    "addon_path": "",
    "version":    "0.1.0",
}

ADDON_SUBPATH = r"Interface\AddOns\WeltenWandler_Raid_Tool"


def _detect_wow_path():
    """WoW-Installationspfad aus der Windows Registry lesen."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Blizzard Entertainment\World of Warcraft"
        )
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        full = os.path.join(path, "_retail_", ADDON_SUBPATH)
        if os.path.isdir(full):
            return full
    except Exception:
        pass
    return ""


def load() -> dict:
    cfg = dict(DEFAULTS)
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    # Whitespace aus Pfaden entfernen
    cfg["addon_path"] = cfg.get("addon_path", "").strip()
    cfg["api_url"]    = cfg.get("api_url", "").strip()

    # Addon-Pfad auto-erkennen falls nicht gesetzt
    if not cfg["addon_path"]:
        cfg["addon_path"] = _detect_wow_path()

    return cfg


def save(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
