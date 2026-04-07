import threading
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image
import os


def _load_icon() -> Image.Image:
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.isfile(icon_path):
        return Image.open(icon_path).resize((64, 64))
    # Fallback: einfaches goldenes Quadrat
    img = Image.new("RGBA", (64, 64), (255, 210, 0, 255))
    return img


class LoginWindow:
    def __init__(self, on_login, current_url="http://localhost:5000"):
        self.on_login    = on_login
        self.current_url = current_url
        self.root        = None

    def show(self):
        if self.root and self.root.winfo_exists():
            self.root.lift()
            return

        self.root = tk.Tk()
        self.root.title("WeltenWandler Companion – Login")
        self.root.geometry("420x280")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        tk.Label(self.root, text="WeltenWandler Companion",
                 bg="#1a1a2e", fg="#ffd200",
                 font=("Arial", 13, "bold")).pack(pady=(18, 8))

        frame = tk.Frame(self.root, bg="#1a1a2e")
        frame.pack(padx=20, fill="x")

        tk.Label(frame, text="Server URL:", bg="#1a1a2e", fg="#aaaaaa").grid(row=0, column=0, sticky="w", pady=4)
        self.url_var = tk.StringVar(value=self.current_url)
        tk.Entry(frame, textvariable=self.url_var, width=26).grid(row=0, column=1, pady=4, padx=(8, 0))

        # Trennlinie
        tk.Frame(frame, bg="#333355", height=1).grid(row=1, columnspan=2, sticky="ew", pady=6)

        tk.Label(frame, text="Benutzername:", bg="#1a1a2e", fg="white").grid(row=2, column=0, sticky="w", pady=4)
        self.user_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.user_var, width=26).grid(row=2, column=1, pady=4, padx=(8, 0))

        tk.Label(frame, text="Passwort:", bg="#1a1a2e", fg="white").grid(row=3, column=0, sticky="w", pady=4)
        self.pass_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.pass_var, show="*", width=26).grid(row=3, column=1, pady=4, padx=(8, 0))

        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var,
                 bg="#1a1a2e", fg="#ff6666").pack(pady=(4, 0))

        tk.Button(self.root, text="Einloggen",
                  bg="#ffd200", fg="#1a1a2e",
                  font=("Arial", 10, "bold"),
                  command=self._do_login,
                  relief="flat", padx=14).pack(pady=8)

        self.root.mainloop()

    def _do_login(self):
        self.status_var.set("Verbinde...")
        self.root.update()
        success, err = self.on_login(
            self.url_var.get().rstrip("/"),
            self.user_var.get(),
            self.pass_var.get()
        )
        if success:
            self.root.destroy()
        else:
            self.status_var.set(err or "Login fehlgeschlagen.")


class SettingsWindow:
    def __init__(self, cfg, on_save):
        self.cfg     = cfg
        self.on_save = on_save

    def show(self):
        root = tk.Tk()
        root.title("Einstellungen")
        root.geometry("440x180")
        root.resizable(False, False)
        root.configure(bg="#1a1a2e")

        tk.Label(root, text="Einstellungen",
                 bg="#1a1a2e", fg="#ffd200",
                 font=("Arial", 12, "bold")).pack(pady=(14, 8))

        frame = tk.Frame(root, bg="#1a1a2e")
        frame.pack(padx=20, fill="x")

        tk.Label(frame, text="Website URL:", bg="#1a1a2e", fg="white").grid(row=0, column=0, sticky="w", pady=6)
        url_var = tk.StringVar(value=self.cfg.get("api_url", ""))
        tk.Entry(frame, textvariable=url_var, width=36).grid(row=0, column=1, pady=6, padx=(8, 0))

        tk.Label(frame, text="Addon-Pfad:", bg="#1a1a2e", fg="white").grid(row=1, column=0, sticky="w", pady=6)
        path_var = tk.StringVar(value=self.cfg.get("addon_path", ""))
        tk.Entry(frame, textvariable=path_var, width=36).grid(row=1, column=1, pady=6, padx=(8, 0))

        def save():
            self.cfg["api_url"]    = url_var.get().strip().rstrip("/")
            self.cfg["addon_path"] = path_var.get().strip()
            self.on_save(self.cfg)
            root.destroy()

        tk.Button(root, text="Speichern",
                  bg="#ffd200", fg="#1a1a2e",
                  font=("Arial", 10, "bold"),
                  command=save, relief="flat", padx=14).pack(pady=10)

        root.mainloop()


class TrayApp:
    def __init__(self, app_controller):
        self.ctrl = app_controller
        self.icon = None
        self._status = "Nicht verbunden"

    def set_status(self, text: str):
        self._status = text
        if self.icon:
            self.icon.title = f"WRT Companion – {text}"

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(f"Status: {self._status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Daten jetzt aktualisieren", lambda: threading.Thread(
                target=self.ctrl.refresh, daemon=True).start()),
            pystray.MenuItem("Einstellungen", lambda: threading.Thread(
                target=self.ctrl.open_settings, daemon=True).start()),
            pystray.MenuItem("Addon updaten", lambda: threading.Thread(
                target=self.ctrl.update_addon, daemon=True).start()),
            pystray.MenuItem("App updaten", lambda: threading.Thread(
                target=self.ctrl.update_self, daemon=True).start()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", self._quit),
        )

    def _quit(self):
        self.ctrl.stop()
        self.icon.stop()

    def run(self):
        self.icon = pystray.Icon(
            name="WRT Companion",
            icon=_load_icon(),
            title=f"WRT Companion – {self._status}",
            menu=self._build_menu(),
        )
        self.icon.run()
