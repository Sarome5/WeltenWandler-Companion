"""
WeltenWandler Companion App
Verbindet die WeltenWandler Website mit dem WoW Addon.
"""
import threading
from datetime import datetime, timezone

import config
import lua_writer
import updater
from api_client   import APIClient
from gui          import GuiManager
from sse_listener import PollingListener
from tray         import TrayApp


DIFFICULTY_MAP = {
    "normal":  "Normal",
    "heroic":  "Heroisch",
    "mythic":  "Mythisch",
}

SIGNUP_MAP = {
    "active":    "angemeldet",
    "late":      "spaeter",
    "tentative": "vorlaeufig",
    "bench":     "bench",
    "absent":    "abgelehnt",
}


def _iso_to_timestamp(iso_str: str) -> int | None:
    """ISO-Datumsstring → Unix-Timestamp."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return None


def _normalize_prioitem(item: dict) -> dict:
    diff_raw = item.get("difficulty") or ""
    return {
        "itemID":     item.get("itemID"),
        "itemName":   item.get("itemName"),
        "priority":   item.get("priority"),
        "difficulty": DIFFICULTY_MAP.get(diff_raw, diff_raw) if diff_raw else None,
    }


def _normalize_single(raid: dict) -> dict:
    return {
        "raidID":         raid.get("raidID"),
        "raidName":       raid.get("raidName"),
        "difficulty":     DIFFICULTY_MAP.get(raid.get("difficulty", ""), raid.get("difficulty")),
        "scheduledAt":    _iso_to_timestamp(raid.get("scheduledAt")),
        "signupStatus":   SIGNUP_MAP.get(raid.get("signupStatus", ""), raid.get("signupStatus")),
        "prioFilled":     raid.get("prioFilled", False),
        "prioItems":      [_normalize_prioitem(p) for p in (raid.get("prioItems") or [])],
        "superPrio":      raid.get("superPrio", False),
        "deadlinePassed": raid.get("deadlinePassed", False),
        "characterName":  raid.get("characterName"),
        "wowClass":       raid.get("wowClass"),
        "wowSpec":        raid.get("wowSpec"),
    }


def _normalize_raid(raw: dict) -> dict:
    """API-Antwort in das Format für lua_writer normalisieren."""
    if "raids" in raw:
        return {
            "version": 1,
            "raids":   [_normalize_single(r) for r in raw["raids"]],
        }
    raid = raw.get("raid", raw)
    return {
        "version": 1,
        "raids":   [_normalize_single(raid)],
    }


class AppController:
    def __init__(self):
        self.cfg  = config.load()
        self.api  = APIClient(self.cfg["api_url"])
        self.tray = TrayApp(self)
        self.sse  = PollingListener(self.api, on_raid_live=self.refresh)
        self.gui  = GuiManager(self)
        self._stop = False

        # Letzte Raid-/Stats-Daten im Speicher
        self.last_raid_data:   dict | None = None
        self.last_update_raid: str         = "–"
        self.last_update_stats: str        = "–"

    # --------------------------------------------------
    # START / STOP
    # --------------------------------------------------
    def run(self):
        self.gui.launch()

    def stop(self):
        self._stop = True
        self.sse.stop()

    def quit(self):
        """Vollständig beenden (GUI + SSE + Tray)."""
        self.stop()
        if self.tray.icon:
            try:
                self.tray.icon.stop()
            except Exception:
                pass

    # --------------------------------------------------
    # DATEN AKTUALISIEREN
    # --------------------------------------------------
    def refresh(self):
        if not self.api.is_logged_in():
            self.tray.set_status("Nicht eingeloggt")
            self.gui.set_status("status.not_logged_in", state="error")
            return

        addon_path = config.get_addon_full(self.cfg)
        if not addon_path:
            self.tray.set_status("Addon-Pfad nicht gesetzt")
            self.gui.set_status("status.addon_path_missing", "status.addon_path_hint", state="error")
            return

        self.tray.set_status("Aktualisiere...")
        self.gui.set_status("status.updating", self.cfg.get("api_url", ""), state="loading")

        # Raid-Daten
        raid_raw = self.api.get_raid()
        raid_ok  = False
        if raid_raw:
            raid_data = _normalize_raid(raid_raw)
            raid_ok   = lua_writer.write_raid(raid_data, addon_path)
            if raid_ok:
                self.last_raid_data   = raid_data
                self.last_update_raid = datetime.now().strftime("%H:%M:%S")

        # Stats-Daten — kein Patch-Filter (Backend unterstützt noch kein Multi-Patch)
        stats_data = self.api.get_stats()
        stats_ok   = False
        if stats_data:
            stats_ok = lua_writer.write_stats(stats_data, addon_path)
            if stats_ok:
                self.last_update_stats = datetime.now().strftime("%H:%M:%S")

        now = datetime.now().strftime("%H:%M:%S")
        if raid_ok or stats_ok:
            self.tray.set_status("Aktuell")
            self.gui.set_status("status.up_to_date", self.cfg.get("api_url", ""), state="ok",
                                last_update=f"Zuletzt: {now}")
        else:
            self.tray.set_status("Fehler beim Abrufen")
            self.gui.set_status("status.error", "", state="error",
                                last_update=f"Versuch: {now}")

    # --------------------------------------------------
    # UPDATES
    # --------------------------------------------------
    def update_addon(self):
        addon_path = config.get_addon_full(self.cfg)
        if not addon_path:
            return
        self.tray.set_status("Addon wird aktualisiert...")
        ok = updater.update_addon(addon_path)
        self.tray.set_status("Addon aktualisiert – /reload ingame" if ok else "Addon-Update fehlgeschlagen")

    def update_self(self):
        self.tray.set_status("App wird aktualisiert...")
        updater.update_self()


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    AppController().run()
