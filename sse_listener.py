import threading
import time


class PollingListener:
    """
    Fragt regelmäßig den /api/companion/events Endpunkt ab.
    Normales Intervall: 120s. Wenn ein Raid in <60 Minuten startet: 30s.
    Bei raid_live=true wird on_raid_live() aufgerufen.
    """

    POLL_INTERVAL_NORMAL = 120  # Sekunden im Normalbetrieb
    POLL_INTERVAL_SOON   = 30   # Sekunden wenn Raid in < 60 Minuten

    def __init__(self, api_client, on_raid_live, get_next_raid_time=None, on_poll=None):
        self.api                = api_client
        self.on_raid_live       = on_raid_live
        self.get_next_raid_time = get_next_raid_time  # callable: () → int|None
        self.on_poll            = on_poll              # callable: () → None, läuft bei jedem Zyklus
        self._thread            = None
        self._running           = False
        self._last_check        = 0

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _current_interval(self) -> int:
        """Kürzeres Intervall wenn ein Raid bald startet (±60/30 Minuten)."""
        if self.get_next_raid_time:
            t = self.get_next_raid_time()
            if t is not None:
                delta = t - time.time()
                if -1800 <= delta <= 3600:   # 30min nach Start bis 60min vorher
                    return self.POLL_INTERVAL_SOON
        return self.POLL_INTERVAL_NORMAL

    def _run(self):
        while self._running:
            if self.api.is_logged_in():
                self._poll()
            time.sleep(self._current_interval())

    def _poll(self):
        if self.on_poll:
            self.on_poll()
        result = self.api.get_events(since=self._last_check)
        if result:
            self._last_check = result.get("updated_at", int(time.time()))
            if result.get("raid_live"):
                interval = self._current_interval()
                label = "30s (Raid bald)" if interval == self.POLL_INTERVAL_SOON else "120s"
                print(f"[Polling] Neuer Raid live → Daten werden aktualisiert (Intervall: {label})")
                self.on_raid_live()
