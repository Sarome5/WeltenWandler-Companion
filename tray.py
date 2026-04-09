import threading
import pystray
from PIL import Image
import os


def _load_icon() -> Image.Image:
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.isfile(icon_path):
        return Image.open(icon_path).resize((64, 64))
    img = Image.new("RGBA", (64, 64), (255, 210, 0, 255))
    return img


class TrayApp:
    def __init__(self, app_controller):
        self.ctrl    = app_controller
        self.icon    = None
        self._status = "Nicht verbunden"

    def set_status(self, text: str):
        self._status = text
        if self.icon:
            self.icon.title = f"WRT Companion – {text}"

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(f"Status: {self._status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Öffnen", lambda: self.ctrl.gui.show_main(), default=True),
            pystray.MenuItem("Daten jetzt aktualisieren", lambda: threading.Thread(
                target=self.ctrl.refresh, daemon=True).start()),
            pystray.MenuItem("Einstellungen", lambda: self.ctrl.gui.show_settings()),
            pystray.MenuItem("Addon updaten", lambda: threading.Thread(
                target=self.ctrl.update_addon, daemon=True).start()),
            pystray.MenuItem("App updaten", lambda: threading.Thread(
                target=self.ctrl.update_self, daemon=True).start()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", self._quit),
        )

    def _quit(self):
        self.ctrl.gui.quit()   # stoppt SSE + zerstört Sentinel → webview.start() kehrt zurück
        self.icon.stop()

    def run(self):
        self.icon = pystray.Icon(
            name="WRT Companion",
            icon=_load_icon(),
            title=f"WRT Companion – {self._status}",
            menu=self._build_menu(),
        )
        self.icon.run()
