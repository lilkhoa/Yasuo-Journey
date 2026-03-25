"""
test_packet.py – Unit tests for network/packet.py serialisation.
Run: python -m pytest network/test_packet.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import struct
from network import packet as pkt


# ── helpers ──────────────────────────────────────────────────────────────────

def roundtrip(p: dict) -> dict:
    """Encode then decode a packet (strips the 4-byte length prefix)."""
    encoded = pkt.encode(p)
    # encoded = 4-byte length header + JSON body
    body_len = struct.unpack('>I', encoded[:4])[0]
    body = encoded[4: 4 + body_len]
    return pkt.decode(body)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_handshake_roundtrip():
    p = pkt.make_handshake(player_id=1, seed=999999)
    r = roundtrip(p)
    assert r['type']      == pkt.HANDSHAKE
    assert r['player_id'] == 1
    assert r['seed']      == 999999


def test_player_state_roundtrip():
    p = pkt.make_player_state(
        player_id=0, x=123.45, y=678.9, vel_y=-5.5,
        facing_right=True, state='run',
        hp=750.0, stamina=100.0,
        frame_index=3, timestamp=1.2345,
    )
    r = roundtrip(p)
    assert r['type']         == pkt.PLAYER_STATE
    assert r['player_id']    == 0
    assert abs(r['x'] - 123.45) < 0.01
    assert abs(r['y'] - 678.9)  < 0.01
    assert r['facing_right'] is True
    assert r['state']        == 'run'
    assert r['frame_index']  == 3


def test_skill_event_roundtrip():
    p = pkt.make_skill_event(player_id=1, skill='q', direction=-1, x=50.0, y=300.0)
    r = roundtrip(p)
    assert r['type']      == pkt.SKILL_EVENT
    assert r['skill']     == 'q'
    assert r['direction'] == -1
    assert abs(r['x'] - 50.0) < 0.01


def test_hit_event_roundtrip():
    p = pkt.make_hit_event(attacker_id=1, target_type='npc', target_id=4242, damage=75.0)
    r = roundtrip(p)
    assert r['type']        == pkt.HIT_EVENT
    assert r['target_type'] == 'npc'
    assert r['target_id']   == 4242
    assert r['damage']      == 75.0


def test_entity_state_roundtrip():
    entities = [
        {'etype': 'npc',  'eid': 1, 'x': 100.0, 'y': 200.0, 'hp': 50,   'state': 'walk',  'direction': 1},
        {'etype': 'boss', 'eid': 2, 'x': 500.0, 'y': 300.0, 'hp': 3000, 'state': 'idle',  'direction': -1},
    ]
    p = pkt.make_entity_state(entities)
    r = roundtrip(p)
    assert r['type'] == pkt.ENTITY_STATE
    assert len(r['entities']) == 2
    assert r['entities'][0]['etype'] == 'npc'
    assert r['entities'][1]['hp']    == 3000


def test_projectile_state_roundtrip():
    projs = [{'pid': 101, 'x': 200.0, 'y': 150.0, 'vx': 5.0, 'vy': 0.0, 'active': True}]
    p = pkt.make_projectile_state(projs)
    r = roundtrip(p)
    assert r['type'] == pkt.PROJECTILE_STATE
    assert r['projectiles'][0]['pid'] == 101
    assert r['projectiles'][0]['active'] is True


def test_game_event_roundtrip():
    p = pkt.make_game_event('kill', killer_id=0, target_id=7)
    r = roundtrip(p)
    assert r['type']      == pkt.GAME_EVENT
    assert r['event']     == 'kill'
    assert r['killer_id'] == 0
    assert r['target_id'] == 7


def test_encode_length_prefix():
    """Make sure the 4-byte length prefix matches the body length."""
    import json
    p = pkt.make_handshake(1, 42)
    encoded = pkt.encode(p)
    (declared_len,) = struct.unpack('>I', encoded[:4])
    actual_body_len = len(encoded) - 4
    assert declared_len == actual_body_len


def test_large_entity_list_round_trips():
    """Stress test with 100 entities."""
    entities = [
        {'etype': 'npc', 'eid': i, 'x': float(i * 10), 'y': 200.0,
         'hp': 100, 'state': 'walk', 'direction': 1}
        for i in range(100)
    ]
    p = pkt.make_entity_state(entities)
    r = roundtrip(p)
    assert len(r['entities']) == 100
    assert r['entities'][99]['eid'] == 99
