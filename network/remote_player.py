"""
remote_player.py – Render-only representation of the remote player.

RemotePlayer does NOT have AI or input logic. It:
- Shares the same animation sprites as the local Player
- Is positioned/animated by data received from the network
- Uses RemotePlayerInterpolator to smoothly move between received snapshots
- Is rendered with a blue color tint to distinguish from the local player

Usage (in game.py):
    remote_player = RemotePlayer(world, software_factory, renderer_ptr)

    # Each frame:
    snap = network.get_remote_state()
    remote_player.apply_network_state(snap)
    remote_player.update(dt)
    remote_player.render(sdl_renderer, camera_x, camera_y)
"""

import os
import sys
import time
import sdl2
import sdl2.ext

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from combat.utils import load_grid_sprite_sheet, flip_sprites_horizontal
from network.interpolation import RemotePlayerInterpolator

PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')

# Blue tint for remote player (R, G, B)
REMOTE_TINT = (100, 150, 255)
# Name label color
LABEL_COLOR = (100, 200, 255)


class RemotePlayer:
    """
    A render-only ghost of the other player, driven by network snapshots.
    """

    def __init__(self, world, factory, renderer_ptr=None):
        self.renderer_ptr = renderer_ptr
        self._interpolator = RemotePlayerInterpolator(delay=0.10)

        # ── Load animations (same assets as local Player) ─────────────────
        self.anims_right: dict = {}
        self.anims_right['idle']          = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Idle.png"),     cols=6,  rows=1)
        self.anims_right['run']           = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Run.png"),      cols=8,  rows=1)
        self.anims_right['walk']          = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Walk.png"),     cols=8,  rows=1)
        self.anims_right['attack_normal'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_1.png"),cols=6,  rows=1)
        self.anims_right['block']         = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"),   cols=2,  rows=1)
        self.anims_right['q']             = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_2.png"),cols=4,  rows=1)
        self.anims_right['w']             = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"),   cols=2,  rows=1)
        self.anims_right['e']             = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_3.png"),cols=3,  rows=1)
        self.anims_right['jump']          = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Jump.png"),     cols=12, rows=1)
        self.anims_right['dead']          = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Dead.png"),     cols=3,  rows=1)
        self.anims_right['hurt']          = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Hurt.png"),     cols=2,  rows=1)

        # Fallback
        if not self.anims_right['idle']:
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(0, 100, 255), (40, 60))]

        self.anims_left: dict = {}
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        # ── SDLExt entity for sprite binding ──────────────────────────────
        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = self.anims_right['idle'][0]
        self.entity.sprite.position = (200, 350)   # Default off-screen-ish

        # ── State ─────────────────────────────────────────────────────────
        self.x: float           = 200.0
        self.y: float           = 350.0
        self.facing_right: bool = True
        self.state: str         = 'idle'
        self.prev_state: str    = 'idle'
        self.frame_index: int   = 0
        self.anim_timer: float  = 0.0
        self.anim_speed: float  = 0.10

        self.hp: float          = 750.0
        self.max_hp: float      = 750.0
        self.stamina: float     = 150.0

        self.visible: bool      = False   # Hidden until first packet received

    # ── Network update ────────────────────────────────────────────────────

    def apply_network_state(self, net_state: dict):
        """
        Called every frame with the latest raw packet from the network layer.
        Pushes the snapshot into the interpolation buffer.
        """
        if not net_state:
            return
        self.visible = True
        self._interpolator.add_snapshot(
            ts=net_state.get('ts', time.monotonic()),
            x=net_state.get('x', self.x),
            y=net_state.get('y', self.y),
            state=net_state.get('state', 'idle'),
            facing_right=net_state.get('facing_right', True),
            frame_index=net_state.get('frame_index', 0),
            hp=net_state.get('hp', self.hp),
            stamina=net_state.get('stamina', self.stamina),
        )
        # Keep hp/stamina for HUD without waiting for interpolation
        self.hp      = net_state.get('hp', self.hp)
        self.stamina = net_state.get('stamina', self.stamina)

    # ── Per-frame update ──────────────────────────────────────────────────

    def update(self, dt: float):
        """
        Advance animation based on the interpolated network state.
        Call once per frame from the main game loop.
        """
        if not self.visible:
            return

        snap = self._interpolator.get_interpolated(time.monotonic())

        self.x            = snap['x']
        self.y            = snap['y']
        self.facing_right = snap['facing_right']
        self.frame_index  = snap['frame_index']
        new_state         = snap['state']

        # Reset frame counter on state change
        if new_state != self.prev_state:
            self.anim_timer  = 0.0
            self.prev_state  = new_state
        self.state = new_state

        # Advance local anim timer so the sprite doesn't freeze if
        # packets stop arriving briefly
        self.anim_timer += dt

        # Pick sprite
        anims = self.anims_right if self.facing_right else self.anims_left
        frames = self._pick_frames(anims)
        if not frames:
            return

        # Use server-authoritative frame index if reasonable; else animate locally
        idx = self.frame_index % len(frames)

        old_pos = self.entity.sprite.position
        self.entity.sprite = frames[idx]
        self.entity.sprite.position = old_pos
        self.entity.sprite.x = int(self.x)
        self.entity.sprite.y = int(self.y)

    def _pick_frames(self, anims: dict) -> list:
        state_to_anim = {
            'dead':        'dead',
            'hurt':        'hurt',
            'casting_q':   'q',
            'casting_w':   'w',
            'dashing_e':   'e',
            'attacking':   'attack_normal',
            'run':         'run',
            'walk':        'walk',
        }
        key = state_to_anim.get(self.state, 'idle')
        return anims.get(key, anims.get('idle', []))

    # ── Render ────────────────────────────────────────────────────────────

    def render(self, sdl_renderer, camera_x: float, camera_y: float):
        """Render the remote player with a blue tint."""
        if not self.visible:
            return
        if not self.entity.sprite.surface:
            return

        surf = self.entity.sprite.surface
        tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, surf)
        if not tex:
            return

        r, g, b = REMOTE_TINT
        sdl2.SDL_SetTextureColorMod(tex, r, g, b)
        sdl2.SDL_SetTextureAlphaMod(tex, 210)

        dst = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            128, 128,
        )
        sdl2.SDL_RenderCopy(sdl_renderer, tex, None, dst)
        sdl2.SDL_DestroyTexture(tex)

        # Draw HP bar above remote player's head
        self._render_hp_bar(sdl_renderer, camera_x, camera_y)

    def _render_hp_bar(self, sdl_renderer, camera_x: float, camera_y: float):
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y) - 14

        bar_w, bar_h = 80, 8
        bar_x = screen_x + (128 - bar_w) // 2
        ratio = max(0.0, min(1.0, self.hp / max(1.0, self.max_hp)))

        # Background (dark red)
        bg = sdl2.SDL_Rect(bar_x, screen_y, bar_w, bar_h)
        sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(sdl_renderer, 80, 20, 20, 200)
        sdl2.SDL_RenderFillRect(sdl_renderer, bg)

        # Foreground (cyan-blue for remote player)
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            fg = sdl2.SDL_Rect(bar_x, screen_y, fill_w, bar_h)
            sdl2.SDL_SetRenderDrawColor(sdl_renderer, 50, 150, 255, 220)
            sdl2.SDL_RenderFillRect(sdl_renderer, fg)

        # Border
        sdl2.SDL_SetRenderDrawColor(sdl_renderer, 200, 220, 255, 255)
        sdl2.SDL_RenderDrawRect(sdl_renderer, bg)
        sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_NONE)

    # ── Hitbox helpers (server-side targeting) ────────────────────────────

    def get_hitbox(self) -> sdl2.SDL_Rect:
        hitbox_w, hitbox_h = 40, 80
        offset_x = (128 - hitbox_w) // 2
        offset_y = (128 - hitbox_h)
        return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y),
                             hitbox_w, hitbox_h)

    def get_bounds(self):
        r = self.get_hitbox()
        return (r.x, r.y, r.w, r.h)

    def is_alive(self) -> bool:
        return self.hp > 0
