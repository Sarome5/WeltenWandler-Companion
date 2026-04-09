import json
import os
import sys
import winreg

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
_APP_NAME   = "WRT Companion"

ADDON_SUBPATH = r"Interface\AddOns\WeltenWandler_Raid_Tool"

DEFAULTS = {
    "api_url":            "http://localhost:5000",
    "addon_path_base":    "",
    "run_on_startup":     False,
    "close_to_tray":      True,
    "addon_autoupdate":   False,
    "language":           "de",
    "version":            "0.1.0",
    "excluded_patch_ids": [],
}


def get_addon_full(cfg: dict) -> str:
    """Gibt den vollständigen Addon-Pfad zurück (base + ADDON_SUBPATH)."""
    base = cfg.get("addon_path_base", "").strip()
    return os.path.join(base, ADDON_SUBPATH) if base else ""


def _detect_wow_base() -> str:
    """WoW _retail_-Pfad aus der Windows Registry lesen."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Blizzard Entertainment\World of Warcraft",
        )
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        base = os.path.join(path, "_retail_")
        if os.path.isdir(os.path.join(base, ADDON_SUBPATH)):
            return base
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

    cfg["api_url"] = cfg.get("api_url", "").strip()

    # Migration: altes addon_path (vollständig) → neues addon_path_base
    old_path = cfg.pop("addon_path", "")
    if not cfg.get("addon_path_base") and old_path:
        norm = old_path.strip().replace("/", os.sep).rstrip(os.sep)
        sub  = ADDON_SUBPATH.rstrip(os.sep)
        if norm.endswith(sub):
            cfg["addon_path_base"] = norm[: -len(sub)].rstrip(os.sep)
        else:
            cfg["addon_path_base"] = norm

    # Auto-Erkennung falls leer
    if not cfg.get("addon_path_base"):
        cfg["addon_path_base"] = _detect_wow_base()

    # Migration: alte Felder entfernen
    cfg.pop("selected_patch_id", None)
    cfg.pop("selected_patch_ids", None)

    # Sicherstellen dass excluded_patch_ids immer eine Liste ist
    if not isinstance(cfg.get("excluded_patch_ids"), list):
        cfg["excluded_patch_ids"] = []

    return cfg


def save(cfg: dict):
    # addon_path nicht mehr speichern
    to_save = {k: v for k, v in cfg.items() if k != "addon_path"}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2, ensure_ascii=False)


# --------------------------------------------------
# Run on Startup (Windows Registry)
# --------------------------------------------------

def set_run_on_startup(enabled: bool):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        if enabled:
            exe    = sys.executable
            script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}" "{script}"')
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def get_run_on_startup() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False
