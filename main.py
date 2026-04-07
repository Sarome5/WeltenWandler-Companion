"""
WeltenWandler Companion App
Verbindet die WeltenWandler Website mit dem WoW Addon.
"""
import threading
import time

import config
import lua_writer
import updater
from api_client  import APIClient
from sse_listener import PollingListener
from tray        import TrayApp, LoginWindow, SettingsWindow


class AppController:
    def __init__(self):
        self.cfg    = config.load()
        self.api    = APIClient(self.cfg["api_url"])
        self.tray   = TrayApp(self)
        self.sse    = PollingListener(self.api, on_raid_live=self.refresh)
        self._stop  = False

    # --------------------------------------------------
    # START
    # --------------------------------------------------
    def run(self):
        # Falls noch kein Token → Login anzeigen
        if not self.api.is_logged_in():
            self._show_login()

        if self.api.is_logged_in():
            self.tray.set_status("Verbunden")
            # Sofort einmal aktualisieren
            threading.Thread(target=self.refresh, daemon=True).start()
            # SSE-Listener starten
            self.sse.start()
        else:
            self.tray.set_status("Nicht eingeloggt")

        # Tray blockiert bis Beenden gedrückt wird
        self.tray.run()

    def stop(self):
        self._stop = True
        self.sse.stop()

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------
    def _show_login(self):
        def do_login(url, username, password):
            # URL speichern falls geändert
            if url != self.cfg.get("api_url"):
                self.cfg["api_url"] = url
                self.api.base_url   = url
                config.save(self.cfg)

            success, err = self.api.login(username, password)
            if success:
                self.tray.set_status("Verbunden")
            else:
                print(f"[Login] Fehler: {err}")
            return success, err

        win = LoginWindow(on_login=do_login, current_url=self.cfg.get("api_url", "http://localhost:5000"))
        win.show()

    # --------------------------------------------------
    # EINSTELLUNGEN
    # --------------------------------------------------
    def open_settings(self):
        def on_save(new_cfg):
            self.cfg = new_cfg
            config.save(new_cfg)
            # API-URL neu setzen
            self.api.base_url = new_cfg["api_url"]

        win = SettingsWindow(cfg=self.cfg, on_save=on_save)
        win.show()

    # --------------------------------------------------
    # DATEN AKTUALISIEREN
    # --------------------------------------------------
    def refresh(self):
        if not self.api.is_logged_in():
            self.tray.set_status("Nicht eingeloggt")
            return

        addon_path = self.cfg.get("addon_path", "")
        if not addon_path:
            self.tray.set_status("Addon-Pfad nicht gesetzt")
            return

        self.tray.set_status("Aktualisiere...")

        # Raid-Daten
        raid_data = self.api.get_raid()
        if raid_data:
            ok = lua_writer.write_raid(raid_data, addon_path)
            print(f"[App] raid_data.lua {'geschrieben' if ok else 'FEHLER'}")

        # Stats-Daten
        stats_data = self.api.get_stats()
        if stats_data:
            ok = lua_writer.write_stats(stats_data, addon_path)
            print(f"[App] stats_data.lua {'geschrieben' if ok else 'FEHLER'}")

        if raid_data or stats_data:
            self.tray.set_status("Aktuell")
        else:
            self.tray.set_status("Fehler beim Abrufen")

    # --------------------------------------------------
    # UPDATES
    # --------------------------------------------------
    def update_addon(self):
        addon_path = self.cfg.get("addon_path", "")
        if not addon_path:
            return
        self.tray.set_status("Addon wird aktualisiert...")
        ok = updater.update_addon(addon_path)
        self.tray.set_status("Addon aktualisiert – /reload ingame" if ok else "Addon-Update fehlgeschlagen")

    def update_self(self):
        self.tray.set_status("App wird aktualisiert...")
        updater.update_self()  # startet neu wenn erfolgreich


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    AppController().run()
