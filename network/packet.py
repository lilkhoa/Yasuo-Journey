"""
packet.py – Packet definitions and serialisation helpers for A3_Yasuo multiplayer.

All packets are plain Python dicts serialised as UTF-8 JSON, length-prefixed
with a 4-byte big-endian integer so they can be framed correctly over a TCP stream.

Packet types (field "type"):
  HANDSHAKE        – initial handshake exchanged immediately after connection
  PLAYER_STATE     – per-frame player position / animation state
  SKILL_EVENT      – player used a skill (q / w / e / attack)
  HIT_EVENT        – player hit an entity (sent to server for authoritative damage)
  ENTITY_STATE     – server → client: snapshot of all NPC / Boss states
  PROJECTILE_STATE – server → client: snapshot of all projectile states
  GAME_EVENT       – server → client: high-level game events (kill, victory, etc.)
"""

import json
import struct
import socket

def encode_ip(ip: str) -> str:
    """Encode an IPv4 address to a short alphanumeric Room ID (Base36)."""
    try:
        packed = socket.inet_aton(ip)
        num = struct.unpack("!I", packed)[0]
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        res = ""
        while num > 0:
            num, rem = divmod(num, 36)
            res = chars[rem] + res
        return res if res else "0"
    except Exception:
        return "ERROR"

def decode_ip(room_id: str) -> str:
    """Decode a Room ID back to an IPv4 address. Returns original string if invalid."""
    try:
        room_id = room_id.upper()
        if "." in room_id: return room_id
        num = 0
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for char in room_id:
            num = num * 36 + chars.index(char)
        packed = struct.pack("!I", num)
        return socket.inet_ntoa(packed)
    except Exception:
        return room_id

# ── Packet type constants ────────────────────────────────────────────────────
HANDSHAKE        = "HANDSHAKE"
PLAYER_STATE     = "PLAYER_STATE"
SKILL_EVENT      = "SKILL_EVENT"
HIT_EVENT        = "HIT_EVENT"
ENTITY_STATE     = "ENTITY_STATE"
PROJECTILE_STATE = "PROJECTILE_STATE"
GAME_EVENT       = "GAME_EVENT"
LOBBY_STATE      = "LOBBY_STATE"
GAME_PAUSE       = "GAME_PAUSE"
GAME_RESUME      = "GAME_RESUME"
PICKUP_REQUEST   = "PICKUP_REQUEST"
ITEM_DROPPED     = "ITEM_DROPPED"
CHARACTER_SELECT = "CHARACTER_SELECT"
BARREL_DESTROY   = "BARREL_DESTROY"
CHEST_OPEN       = "CHEST_OPEN"

# ── Serialisation helpers ────────────────────────────────────────────────────

def encode(packet: dict) -> bytes:
    """Serialise a packet dict to wire bytes (4-byte length prefix + JSON body)."""
    body = json.dumps(packet, separators=(',', ':')).encode('utf-8')
    return struct.pack('>I', len(body)) + body


def decode(data: bytes) -> dict:
    """Deserialise raw JSON bytes (WITHOUT the length prefix) to a packet dict."""
    return json.loads(data.decode('utf-8'))


def recv_packet(sock) -> dict | None:
    """
    Block-read exactly one packet from *sock*.
    Returns the decoded dict, or None if the connection was closed.
    """
    # 1. Read 4-byte length header
    header = _recv_exactly(sock, 4)
    if header is None:
        return None
    (length,) = struct.unpack('>I', header)

    # 2. Read body
    body = _recv_exactly(sock, length)
    if body is None:
        return None

    return decode(body)


def _recv_exactly(sock, n: int) -> bytes | None:
    """Read exactly *n* bytes from *sock*, handling partial reads."""
    buf = b''
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except OSError:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


# ── Packet constructors ──────────────────────────────────────────────────────

def make_handshake(player_id: int, seed: int, character_type: str = "yasuo") -> dict:
    return {"type": HANDSHAKE, "player_id": player_id, "seed": seed, "character_type": character_type}


def make_player_state(player_id: int, x: float, y: float, vel_y: float,
                      facing_right: bool, state: str, hp: float,
                      stamina: float, frame_index: int, timestamp: float) -> dict:
    return {
        "type":         PLAYER_STATE,
        "player_id":    player_id,
        "x":            round(x, 2),
        "y":            round(y, 2),
        "vel_y":        round(vel_y, 3),
        "facing_right": facing_right,
        "state":        state,
        "hp":           round(hp, 1),
        "stamina":      round(stamina, 1),
        "frame_index":  frame_index,
        "ts":           round(timestamp, 4),
    }


def make_skill_event(player_id: int, skill: str, direction: int,
                     x: float, y: float) -> dict:
    """
    skill: 'q' | 'w' | 'e' | 'attack'
    direction: +1 (right) or -1 (left)
    """
    return {
        "type":      SKILL_EVENT,
        "player_id": player_id,
        "skill":     skill,
        "direction": direction,
        "x":         round(x, 2),
        "y":         round(y, 2),
    }


def make_hit_event(attacker_id: int, target_type: str, target_id: int,
                   damage: float) -> dict:
    """
    target_type: 'npc' | 'boss' | 'player'
    target_id:   unique entity id (id() of the object on the server)
    """
    return {
        "type":        HIT_EVENT,
        "attacker_id": attacker_id,
        "target_type": target_type,
        "target_id":   target_id,
        "damage":      damage,
    }


def make_entity_state(entities: list) -> dict:
    """
    entities: list of dicts each with keys:
        etype, eid, x, y, hp, state, direction
    """
    return {"type": ENTITY_STATE, "entities": entities}


def make_projectile_state(projectiles: list) -> dict:
    """
    projectiles: list of dicts each with keys:
        pid, x, y, vx, vy, active
    """
    return {"type": PROJECTILE_STATE, "projectiles": projectiles}


def make_game_event(event: str, **kwargs) -> dict:
    """
    event: 'kill' | 'boss_encounter' | 'victory' | 'game_over'
    kwargs: arbitrary extra fields (e.g. killer_id, target_id)
    """
    pkt = {"type": GAME_EVENT, "event": event}
    pkt.update(kwargs)
    return pkt


def make_lobby_state(host_ready: bool, client_ready: bool, game_starting: bool) -> dict:
    return {
        "type": LOBBY_STATE,
        "host_ready": host_ready,
        "client_ready": client_ready,
        "game_starting": game_starting
    }


def make_game_pause() -> dict:
    return {"type": GAME_PAUSE}


def make_game_resume() -> dict:
    return {"type": GAME_RESUME}


def make_pickup_request(player_id: int, item_net_id: int, player_net_id: int) -> dict:
    """
    Send a request to pick up an item.
    The server will validate and either approve or deny.
    
    Args:
        player_id: Requesting player's ID
        item_net_id: Unique item ID
        player_net_id: Player's unique ID (for server verification)
    """
    return {
        "type": PICKUP_REQUEST,
        "player_id": player_id,
        "item_net_id": item_net_id,
        "player_net_id": player_net_id,
    }


def make_character_select(player_id: int, character_type: str) -> dict:
    """
    Notify the other player which character was selected.
    character_type: 'yasuo' | 'leaf_ranger'
    """
    return {
        "type": CHARACTER_SELECT,
        "player_id": player_id,
        "character_type": character_type,
    }


# Cập nhật hàm make_item_dropped
def make_item_dropped(item_type: int, x: float, y: float, item_net_id: int, vx: float = 0.0, vy: float = 0.0) -> dict:
    """
    Notify clients that an item was dropped at a location.
    """
    return {
        "type": ITEM_DROPPED,
        "item_type": item_type,
        "x": round(x, 2),
        "y": round(y, 2),
        "vx": round(vx, 3), # [THÊM MỚI] Gửi kèm vận tốc x
        "vy": round(vy, 3), # [THÊM MỚI] Gửi kèm vận tốc y
        "item_net_id": item_net_id,
    }


def make_barrel_destroy(barrel_net_id: int) -> dict:
    """Create a packet indicating a barrel has been destroyed."""
    return {
        "type": BARREL_DESTROY,
        "barrel_net_id": barrel_net_id
    }

def make_chest_open(chest_net_id: int) -> dict:
    """Create a packet indicating a chest has been opened."""
    return {
        "type": CHEST_OPEN,
        "chest_net_id": chest_net_id
    }
