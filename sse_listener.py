import threading
import time


class SSEListener:
    """
    Hält eine dauerhafte SSE-Verbindung zur Website.
    Bei 'raid_live'-Event wird on_raid_live() aufgerufen.
    Reconnectet automatisch bei Verbindungsabbruch.
    """

    def __init__(self, api_client, on_raid_live):
        self.api        = api_client
        self.on_raid_live = on_raid_live
        self._thread    = None
        self._running   = False

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        RECONNECT_DELAY = 30  # Sekunden bis zum nächsten Versuch

        while self._running:
            if not self.api.is_logged_in():
                time.sleep(10)
                continue

            try:
                print("[SSE] Verbinde mit Server-Stream...")
                for event in self.api.stream():
                    if not self._running:
                        return

                    if event.event == "raid_live":
                        print("[SSE] raid_live Event empfangen → Daten werden aktualisiert")
                        self.on_raid_live()

                    elif event.event == "ping":
                        pass  # Keepalive, ignorieren

            except Exception as e:
                if self._running:
                    print(f"[SSE] Verbindung verloren ({e}) – reconnect in {RECONNECT_DELAY}s")
                    time.sleep(RECONNECT_DELAY)
