"""
server.py – Authoritative game server for A3_Yasuo 2-player co-op.

Architecture
------------
- Runs in a background daemon thread (does NOT block the SDL game loop).
- Accepts exactly ONE client connection (host player = player_id 0,
  guest player = player_id 1).
- Receives PLAYER_STATE / SKILL_EVENT / HIT_EVENT packets from the client.
- The main game loop calls push_world_state() every tick to give the server
  the current NPC/Boss/Projectile snapshot, which gets broadcast to the client.
- Entity AI runs ONLY on the server (host machine).

Thread safety
-------------
All shared state is protected via threading.Lock or thread-safe queue.Queue.
"""

import socket
import threading
import time
import queue
import random

from network import packet as pkt


class GameServer:
    """
    Manages the listening socket, one connected client, and all
    data exchange between the host game and the remote client.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        # Random seed shared with client so entity spawns are identical
        self.seed = random.randint(0, 2**31 - 1)

        # player_id 0 = host (local), player_id 1 = guest (remote client)
        self._local_player_id  = 0
        self._remote_player_id = 1

        # Latest state received FROM the client about the remote player
        self._remote_state: dict = {}          # protected by _state_lock
        self._state_lock = threading.Lock()

        # Lobby state
        self.host_ready = False
        self.client_ready = False
        self.game_starting = False

        # Character type tracking
        self._host_character_type = "yasuo"      # Set by game loop before start
        self._remote_character_type = "yasuo"     # Received from client
        self._char_lock = threading.Lock()

        # latest skill/hit events queued by the client (consumed by game loop)
        self._event_queue: queue.Queue = queue.Queue(maxsize=128)

        # Outbound queue: world-state snapshots to push to client
        self._send_queue: queue.Queue = queue.Queue(maxsize=64)

        self._client_sock: socket.socket | None = None
        self._connected = threading.Event()
        self._running   = True

        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="srv-listen")
        self._send_thread = threading.Thread(
            target=self._send_loop, daemon=True, name="srv-send")

    # ── Public API (called from main game thread) ─────────────────────────

    def start(self):
        """Start listening for the client connection."""
        self._listen_thread.start()
        print(f"[Server] Listening on {self.host}:{self.port} "
              f"(seed={self.seed})")

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def set_host_character_type(self, char_type: str):
        """Set the host player's character type (called before game start)."""
        with self._char_lock:
            self._host_character_type = char_type

    def get_remote_character_type(self) -> str:
        """Return the remote (client) player's character type."""
        with self._char_lock:
            return self._remote_character_type

    def get_remote_state(self) -> dict:
        """Return a copy of the latest PLAYER_STATE from the remote client."""
        with self._state_lock:
            return dict(self._remote_state)

    def pop_events(self) -> list:
        """Drain and return all pending SKILL_EVENT / HIT_EVENT from client."""
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def push_local_player_state(self, state_pkt: dict):
        """Send the host player's latest state to the client."""
        self._enqueue(state_pkt)

    def push_world_state(self, entity_pkt: dict, projectile_pkt: dict):
        """Push a world snapshot (entities + projectiles) to the client."""
        self._enqueue(entity_pkt)
        self._enqueue(projectile_pkt)

    def push_game_event(self, event_pkt: dict):
        """Broadcast a game-level event (kill, victory, pause, etc.) to the client."""
        self._enqueue(event_pkt)

    def push_lobby_state(self):
        """Push the current lobby state to the client."""
        self._enqueue(pkt.make_lobby_state(self.host_ready, self.client_ready, self.game_starting))

    def stop(self):
        self._running = False
        if self._client_sock:
            try:
                self._client_sock.close()
            except OSError:
                pass

    # ── Internal threads ──────────────────────────────────────────────────

    def _listen_loop(self):
        """Accept one client, perform handshake, then spawn recv thread."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(1)
        srv.settimeout(1.0)

        while self._running:
            try:
                conn, addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            print(f"[Server] Client connected: {addr}")
            self._client_sock = conn
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Send handshake (player_id=1 for the client, seed for spawn sync)
            with self._char_lock:
                host_char = self._host_character_type
            hs = pkt.make_handshake(player_id=self._remote_player_id,
                                    seed=self.seed,
                                    character_type=host_char)
            try:
                conn.sendall(pkt.encode(hs))
            except OSError as e:
                print(f"[Server] Handshake send error: {e}")
                continue

            self._connected.set()
            self._send_thread.start()

            # Receive loop (blocking in this thread)
            self._recv_loop(conn)

            # Client disconnected
            self._connected.clear()
            with self._state_lock:
                self._remote_state = {}
            print("[Server] Client disconnected.")
            break   # Only support one client session per run

        srv.close()

    def _recv_loop(self, conn: socket.socket):
        """Continuously receive packets from the connected client."""
        while self._running:
            p = pkt.recv_packet(conn)
            if p is None:
                break   # Connection closed

            t = p.get("type")
            if t == pkt.PLAYER_STATE:
                with self._state_lock:
                    self._remote_state = p
            elif t == pkt.LOBBY_STATE:
                self.client_ready = p.get("client_ready", False)
            elif t == pkt.CHARACTER_SELECT:
                with self._char_lock:
                    self._remote_character_type = p.get("character_type", "yasuo")
                print(f"[Server] Client selected character: {self._remote_character_type}")
                # Also push to event_queue so host game loop is notified immediately
                try:
                    self._event_queue.put_nowait(p)
                except queue.Full:
                    pass
            elif t in (pkt.SKILL_EVENT, pkt.HIT_EVENT, pkt.GAME_PAUSE, pkt.GAME_RESUME, pkt.GAME_EVENT, pkt.PICKUP_REQUEST, pkt.ITEM_DROPPED, pkt.BARREL_DESTROY, pkt.CHEST_OPEN):
                try:
                    self._event_queue.put_nowait(p)
                except queue.Full:
                    pass   # Drop packet if overwhelmed

    def _send_loop(self):
        """Drain the outbound queue and send packets to the client."""
        while self._running:
            try:
                p = self._send_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            conn = self._client_sock
            if conn is None:
                continue
            try:
                conn.sendall(pkt.encode(p))
            except OSError:
                break   # Client disconnected

    def _enqueue(self, p: dict):
        """Push a packet onto the outbound queue (drop oldest if full)."""
        if not self._connected.is_set():
            return
        try:
            self._send_queue.put_nowait(p)
        except queue.Full:
            try:
                self._send_queue.get_nowait()   # drop oldest
                self._send_queue.put_nowait(p)
            except queue.Empty:
                pass
