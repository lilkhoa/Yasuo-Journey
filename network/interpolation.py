"""
interpolation.py – Linear interpolation for remote player state.

The RemotePlayerInterpolator keeps a rolling buffer of received network
snapshots and serves a position/state that is INTERP_DELAY seconds behind
the latest snapshot.  This hides network jitter: the rendered position
always has two snapshots to interpolate between, so the character moves
smoothly on the other player's screen even if packets arrive irregularly.

Usage:
    interp = RemotePlayerInterpolator(delay=0.10)

    # Call whenever a PLAYER_STATE packet arrives:
    interp.add_snapshot(ts=pkt['ts'], x=pkt['x'], y=pkt['y'],
                        state=pkt['state'], facing_right=pkt['facing_right'],
                        frame_index=pkt['frame_index'],
                        hp=pkt['hp'], stamina=pkt['stamina'])

    # Call each render frame with current local clock time:
    result = interp.get_interpolated(now=time.monotonic())
    # result is a dict with x, y, state, facing_right, frame_index, hp, stamina
"""

import time
from collections import deque

MAX_BUFFER = 16   # Keep at most this many snapshots


class RemotePlayerInterpolator:
    """
    Stores a time-stamped ring-buffer of remote player snapshots and returns
    a linearly-interpolated snapshot for a render time in the past.
    """

    def __init__(self, delay: float = 0.10):
        """
        delay: how many seconds behind real-time we render the remote player.
               Larger = smoother but more lag; 0.10s is a good default.
        """
        self.delay = delay
        self._buf: deque = deque(maxlen=MAX_BUFFER)

    def add_snapshot(self, ts: float, x: float, y: float, state: str,
                     facing_right: bool, frame_index: int,
                     hp: float, stamina: float) -> None:
        """Push a new received snapshot into the buffer."""
        snap = {
            'ts':           ts,
            'x':            x,
            'y':            y,
            'state':        state,
            'facing_right': facing_right,
            'frame_index':  frame_index,
            'hp':           hp,
            'stamina':      stamina,
        }
        self._buf.append(snap)

    def get_interpolated(self, now: float) -> dict:
        """
        Return an interpolated snapshot for render time = now - delay.

        Falls back gracefully:
        - No data at all → returns a zeroed default dict.
        - Only one snapshot → returns that snapshot as-is (no interpolation).
        - Render time is before all snapshots → clamp to oldest.
        - Render time is after all snapshots → clamp to newest (extrapolation
          avoided deliberately; the character will appear to stop, which is
          visually safer than extrapolating into walls).
        """
        if not self._buf:
            return _default_state()

        render_time = now - self.delay

        snaps = list(self._buf)

        # Clamp to oldest
        if render_time <= snaps[0]['ts']:
            return dict(snaps[0])

        # Clamp to newest (no extrapolation)
        if render_time >= snaps[-1]['ts']:
            return dict(snaps[-1])

        # Find the two surrounding snapshots
        before = snaps[0]
        after  = snaps[1]
        for i in range(1, len(snaps)):
            if snaps[i]['ts'] >= render_time:
                before = snaps[i - 1]
                after  = snaps[i]
                break

        # Compute interpolation factor t ∈ [0, 1]
        dt = after['ts'] - before['ts']
        if dt <= 0:
            return dict(after)
        t = (render_time - before['ts']) / dt
        t = max(0.0, min(1.0, t))

        # Linearly interpolate numeric fields
        return {
            'ts':           render_time,
            'x':            _lerp(before['x'], after['x'], t),
            'y':            _lerp(before['y'], after['y'], t),
            # Discrete fields: use after-snapshot when > 50% through the gap
            'state':        after['state'] if t >= 0.5 else before['state'],
            'facing_right': after['facing_right'] if t >= 0.5 else before['facing_right'],
            'frame_index':  after['frame_index']  if t >= 0.5 else before['frame_index'],
            'hp':           _lerp(before['hp'],      after['hp'],      t),
            'stamina':      _lerp(before['stamina'], after['stamina'], t),
        }

    def reset(self) -> None:
        self._buf.clear()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _default_state() -> dict:
    return {
        'ts':           0.0,
        'x':            0.0,
        'y':            0.0,
        'state':        'idle',
        'facing_right': True,
        'frame_index':  0,
        'hp':           0.0,
        'stamina':      0.0,
    }
