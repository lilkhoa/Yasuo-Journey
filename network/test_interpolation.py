"""
test_interpolation.py – Unit tests for network/interpolation.py
Run: python -m pytest network/test_interpolation.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from network.interpolation import RemotePlayerInterpolator


# ── helpers ───────────────────────────────────────────────────────────────────

def snap(ts, x, y, state='idle', facing_right=True, fi=0, hp=750.0, st=150.0):
    return dict(ts=ts, x=x, y=y, state=state, facing_right=facing_right,
                frame_index=fi, hp=hp, stamina=st)


def make_interp(delay=0.0):
    """Zero-delay interpolator so we can test without timing offsets."""
    return RemotePlayerInterpolator(delay=delay)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_empty_returns_default():
    interp = make_interp()
    r = interp.get_interpolated(now=1.0)
    assert r['x'] == 0.0
    assert r['y'] == 0.0
    assert r['state'] == 'idle'


def test_single_snapshot_returned_as_is():
    interp = make_interp()
    interp.add_snapshot(ts=1.0, x=100.0, y=200.0, state='run',
                        facing_right=True, frame_index=2, hp=750.0, stamina=100.0)
    r = interp.get_interpolated(now=1.0)  # delay=0 → render_time=1.0
    assert abs(r['x'] - 100.0) < 0.001
    assert abs(r['y'] - 200.0) < 0.001


def test_interpolates_midpoint():
    interp = make_interp(delay=0.0)
    interp.add_snapshot(ts=0.0, x=0.0,   y=0.0,   state='walk', facing_right=True, frame_index=0, hp=750.0, stamina=150.0)
    interp.add_snapshot(ts=1.0, x=100.0, y=50.0,  state='walk', facing_right=True, frame_index=1, hp=700.0, stamina=140.0)

    r = interp.get_interpolated(now=0.5)   # exactly midpoint
    assert abs(r['x']  - 50.0)  < 0.5
    assert abs(r['y']  - 25.0)  < 0.5
    assert abs(r['hp'] - 725.0) < 1.0


def test_clamp_to_oldest_before_all_snapshots():
    interp = make_interp(delay=0.0)
    interp.add_snapshot(ts=5.0, x=200.0, y=100.0, state='idle',
                        facing_right=True, frame_index=0, hp=750.0, stamina=150.0)
    # render_time = 3.0 < oldest ts = 5.0 → clamp to oldest
    r = interp.get_interpolated(now=3.0)
    assert abs(r['x'] - 200.0) < 0.001


def test_clamp_to_newest_after_all_snapshots():
    interp = make_interp(delay=0.0)
    interp.add_snapshot(ts=1.0, x=50.0,  y=10.0, state='idle',
                        facing_right=True, frame_index=0, hp=750.0, stamina=150.0)
    interp.add_snapshot(ts=2.0, x=100.0, y=20.0, state='run',
                        facing_right=True, frame_index=1, hp=700.0, stamina=130.0)
    # render_time = 9.0 > newest ts = 2.0 → clamp to newest
    r = interp.get_interpolated(now=9.0)
    assert abs(r['x'] - 100.0) < 0.001
    assert r['state'] == 'run'


def test_facing_direction_switches_at_midpoint():
    interp = make_interp(delay=0.0)
    interp.add_snapshot(ts=0.0, x=0.0, y=0.0, state='walk',
                        facing_right=True,  frame_index=0, hp=750.0, stamina=150.0)
    interp.add_snapshot(ts=1.0, x=0.0, y=0.0, state='walk',
                        facing_right=False, frame_index=0, hp=750.0, stamina=150.0)

    r_before = interp.get_interpolated(now=0.4)   # t<0.5 → use before snapshot
    r_after  = interp.get_interpolated(now=0.6)   # t>0.5 → use after snapshot

    assert r_before['facing_right'] is True
    assert r_after['facing_right']  is False


def test_delay_shifts_render_window():
    interp = RemotePlayerInterpolator(delay=0.5)   # 500 ms delay
    interp.add_snapshot(ts=0.0, x=0.0,   y=0.0,  state='idle',
                        facing_right=True, frame_index=0, hp=750.0, stamina=150.0)
    interp.add_snapshot(ts=1.0, x=100.0, y=50.0, state='walk',
                        facing_right=True, frame_index=1, hp=700.0, stamina=140.0)

    # now=1.0 → render_time = 1.0 - 0.5 = 0.5  → midpoint
    r = interp.get_interpolated(now=1.0)
    assert abs(r['x'] - 50.0) < 0.5


def test_reset_clears_buffer():
    interp = make_interp()
    interp.add_snapshot(ts=0.0, x=99.0, y=99.0, state='run',
                        facing_right=True, frame_index=0, hp=750.0, stamina=150.0)
    interp.reset()
    r = interp.get_interpolated(now=0.0)
    assert r['x'] == 0.0   # default after reset


def test_buffer_does_not_exceed_max():
    from network.interpolation import MAX_BUFFER
    interp = make_interp()
    for i in range(MAX_BUFFER + 20):
        interp.add_snapshot(ts=float(i), x=float(i), y=0.0, state='idle',
                            facing_right=True, frame_index=0, hp=750.0, stamina=150.0)
    assert len(interp._buf) == MAX_BUFFER
