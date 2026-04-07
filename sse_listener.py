import threading
import time


class PollingListener:
    """
    Fragt alle POLL_INTERVAL Sekunden den /api/companion/events Endpunkt ab.
    Bei raid_live=true wird on_raid_live() aufgerufen und die Daten aktualisiert.
    """

    POLL_INTERVAL = 120  # Sekunden zwischen Abfragen

    def __init__(self, api_client, on_raid_live):
        self.api          = api_client
        self.on_raid_live = on_raid_live
        self._thread      = None
        self._running     = False
        self._last_check  = 0

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            if self.api.is_logged_in():
                self._poll()
            time.sleep(self.POLL_INTERVAL)

    def _poll(self):
        result = self.api.get_events(since=self._last_check)
        if result:
            self._last_check = result.get("updated_at", int(time.time()))
            if result.get("raid_live"):
                print("[Polling] Neuer Raid live → Daten werden aktualisiert")
                self.on_raid_live()
