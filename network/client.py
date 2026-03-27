"""
client.py – Network client for A3_Yasuo 2-player co-op.

Architecture
------------
- Runs two daemon threads: one for sending, one for receiving.
- The game loop calls update_local_player() once per frame with the local
  player's latest state; this is queued and sent asynchronously.
- The game loop reads get_remote_state(), get_entity_state(), etc. to
  obtain the server's latest world snapshot.
- SKILL_EVENT and HIT_EVENT are sent via send_skill_event() / send_hit_event().
"""

import socket
import threading
import queue
import time

from network import packet as pkt


class GameClient:
    """
    Maintains the TCP connection to the server and provides a simple
    flat API for the game loop to push/pull network data.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        # Assigned by server during handshake
        self.player_id: int = 1
        self.seed: int      = 0

        # Latest data received from server
        self._remote_player_state: dict  = {}
        self._entity_state: list         = []
        self._projectile_state: list     = []
        self._pending_game_events: list  = []

        # Lobby state from server
        self.lobby_host_ready = False
        self.lobby_client_ready = False
        self.lobby_game_starting = False

        self._state_lock  = threading.Lock()
        self._events_lock = threading.Lock()

        # Outbound queue (non-blocking from game loop)
        self._send_queue: queue.Queue = queue.Queue(maxsize=128)

        self._sock: socket.socket | None = None
        self._connected = threading.Event()
        self._running   = True
        self._handshake_done = threading.Event()

        self._recv_thread = threading.Thread(
            target=self._recv_loop, daemon=True, name="cli-recv")
        self._send_thread = threading.Thread(
            target=self._send_loop, daemon=True, name="cli-send")

    # ── Connection management ─────────────────────────────────────────────

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Attempt to connect to the server.
        Returns True when handshake is complete, False on timeout/error.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.host, self.port))
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(None)   # Switch to blocking after connect
            self._sock = s
        except OSError as e:
            print(f"[Client] Connection failed: {e}")
            return False

        self._recv_thread.start()
        self._send_thread.start()

        # Wait for handshake to be received
        if not self._handshake_done.wait(timeout=5.0):
            print("[Client] Handshake timeout.")
            return False

        self._connected.set()
        print(f"[Client] Connected. player_id={self.player_id}, seed={self.seed}")
        return True

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    # ── Outbound helpers (game loop → server) ────────────────────────────

    def send_player_state(self, state_pkt: dict):
        """Queue the local player's state for sending to the server."""
        self._enqueue(state_pkt)

    def send_skill_event(self, skill: str, direction: int, x: float, y: float):
        """Send a skill-cast event to the server."""
        ev = pkt.make_skill_event(self.player_id, skill, direction, x, y)
        self._enqueue(ev)

    def send_hit_event(self, target_type: str, target_id: int, damage: float):
        """Notify the server that the local player hit an entity."""
        ev = pkt.make_hit_event(self.player_id, target_type, target_id, damage)
        self._enqueue(ev)

    def send_lobby_ready(self, ready: bool):
        """Send the client's lobby ready state to the server."""
        self._enqueue(pkt.make_lobby_state(False, ready, False))

    def send_game_pause(self):
        self._enqueue(pkt.make_game_pause())

    def send_game_resume(self):
        self._enqueue(pkt.make_game_resume())

    # ── Inbound helpers (game loop ← server) ─────────────────────────────

    def get_remote_player_state(self) -> dict:
        """Return the latest PLAYER_STATE snapshot of the remote player."""
        with self._state_lock:
            return dict(self._remote_player_state)

    def get_entity_state(self) -> list:
        """Return the latest entity snapshot from the server."""
        with self._state_lock:
            return list(self._entity_state)

    def get_projectile_state(self) -> list:
        """Return the latest projectile snapshot from the server."""
        with self._state_lock:
            return list(self._projectile_state)

    def pop_game_events(self) -> list:
        """Drain and return all pending GAME_EVENT packets."""
        with self._events_lock:
            evs = list(self._pending_game_events)
            self._pending_game_events.clear()
        return evs

    # ── Internal threads ──────────────────────────────────────────────────

    def _recv_loop(self):
        """Continuously receive packets from the server."""
        while self._running:
            p = pkt.recv_packet(self._sock)
            if p is None:
                print("[Client] Disconnected from server.")
                self._connected.clear()
                break

            t = p.get("type")
            if t == pkt.HANDSHAKE:
                self.player_id = p.get("player_id", 1)
                self.seed      = p.get("seed", 0)
                self._handshake_done.set()

            elif t == pkt.PLAYER_STATE:
                # Server is relaying the host player's state to us
                with self._state_lock:
                    self._remote_player_state = p

            elif t == pkt.ENTITY_STATE:
                with self._state_lock:
                    self._entity_state = p.get("entities", [])

            elif t == pkt.PROJECTILE_STATE:
                with self._state_lock:
                    self._projectile_state = p.get("projectiles", [])

            elif t == pkt.LOBBY_STATE:
                self.lobby_host_ready = p.get("host_ready", False)
                self.lobby_client_ready = p.get("client_ready", False)
                self.lobby_game_starting = p.get("game_starting", False)

            elif t in (pkt.GAME_EVENT, pkt.GAME_PAUSE, pkt.GAME_RESUME, pkt.GAME_OVER):
                with self._events_lock:
                    self._pending_game_events.append(p)

    def _send_loop(self):
        """Drain the outbound queue and write packets to the socket."""
        while self._running:
            try:
                p = self._send_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if self._sock is None:
                continue
            try:
                self._sock.sendall(pkt.encode(p))
            except OSError:
                break

    def _enqueue(self, p: dict):
        """Non-blocking enqueue; drop oldest on overflow."""
        try:
            self._send_queue.put_nowait(p)
        except queue.Full:
            try:
                self._send_queue.get_nowait()
                self._send_queue.put_nowait(p)
            except queue.Empty:
                pass
