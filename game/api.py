import threading


class StopExecution(Exception):
    """Raised inside the script thread to unwind it cleanly when stopped."""
    pass


class GameAPI:
    """
    Bridge between the player's script thread and the game's main thread.

    Each *action* (move, harvest) is queued here by the SCRIPT thread and
    executed by the MAIN thread on the next game tick; the script thread
    blocks until it has been applied. That is what lets the player write
    `while True: api.move(1, 0)` and watch it run at a visible pace.

    Player code never sees this object directly - it gets a PlayerAPI,
    which only exposes the public game commands.
    """

    WAIT_SLICE = 0.05  # seconds between stop checks while waiting for a tick

    def __init__(self, world, player):
        self.world = world
        self.player = player
        self._lock = threading.Lock()
        self._pending = None          # (action_fn, done_event, result_box)
        self._stop_requested = False

    # ---- lifecycle (called by the runtime, not the player) ----
    def request_stop(self):
        with self._lock:
            self._stop_requested = True
            self._discard_pending()

    def clear_stop(self):
        with self._lock:
            self._stop_requested = False
            self._discard_pending()

    @property
    def stop_requested(self):
        return self._stop_requested

    def _discard_pending(self):
        if self._pending:
            self._pending[1].set()    # release a waiting script thread
            self._pending = None

    def process_pending(self):
        """Call once per game tick from the MAIN thread. Returns True if an action ran."""
        with self._lock:
            pending, self._pending = self._pending, None
        if not pending:
            return False
        action, done, box = pending
        try:
            action()
        except Exception as e:          # never let player input crash the game loop
            box["error"] = e
        done.set()
        return True

    def _do_action(self, action_fn):
        if self._stop_requested:
            raise StopExecution()
        done, box = threading.Event(), {}
        with self._lock:
            self._pending = (action_fn, done, box)
        while not done.wait(self.WAIT_SLICE):
            if self._stop_requested:
                raise StopExecution()
        if self._stop_requested:
            raise StopExecution()
        if "error" in box:
            raise box["error"]

    # ---- game commands (wrapped by PlayerAPI) ----
    def move(self, dx, dy):
        for name, v in (("dx", dx), ("dy", dy)):
            if isinstance(v, bool) or not isinstance(v, int) or v not in (-1, 0, 1):
                raise ValueError(f"move(): {name} must be -1, 0 or 1 (got {v!r})")
        self._do_action(lambda: self.player.move(dx, dy, self.world))

    def harvest(self):
        self._do_action(lambda: self.world.harvest_at(self.player.x, self.player.y))

    def get_pos(self):
        self._check_stop()
        return self.player.x, self.player.y

    def can_harvest(self):
        self._check_stop()
        return self.world.has_resource(self.player.x, self.player.y)

    def get_world_size(self):
        self._check_stop()
        return self.world.size

    def crops_left(self):
        self._check_stop()
        return len(self.world.resources)

    def _check_stop(self):
        if self._stop_requested:
            raise StopExecution()


class PlayerAPI:
    """
    The `api` object handed to player code. It holds no public reference to
    the world or the player, so scripts can only act through these commands
    (the runtime also rejects any `_name` / `__dunder__` access).
    """

    __slots__ = ("_game",)

    def __init__(self, game_api):
        self._game = game_api

    def move(self, dx, dy):
        """Move one cell: dx and dy are each -1, 0 or 1. Blocks until applied."""
        self._game.move(dx, dy)

    def harvest(self):
        """Harvest the crop on the current cell (does nothing if empty)."""
        self._game.harvest()

    def can_harvest(self):
        """True if there is a crop on the current cell."""
        return self._game.can_harvest()

    def get_pos(self):
        """Current (x, y) position. (0, 0) is the top-left cell."""
        return self._game.get_pos()

    def get_world_size(self):
        """Width/height of the square farm."""
        return self._game.get_world_size()

    def crops_left(self):
        """Number of crops still on the farm."""
        return self._game.crops_left()
