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
from combat.refactored_skill_q import load_tornado_assets, TornadoObject
from combat.refactored_skill_w import load_wall_assets, WallObject

PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')
PLAYER2_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player_2')

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
        self._factory = factory
        self._world = world
        self._character_type = 'yasuo'  # Default

        # ── Load default animations (Yasuo) ───────────────────────────────
        self.anims_right: dict = {}
        self.anims_left: dict = {}
        self._load_yasuo_sprites(factory)

        # ── SDLExt entity for sprite binding ──────────────────────────────
        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = self.anims_right['idle'][0]
        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = self.anims_right['idle'][0]
        self.entity.sprite.position = (200, 350)   # Default off-screen-ish

        self.active_vfx = []

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
        self._render_w: int     = 128     # Render dimensions (adapts to character)
        self._render_h: int     = 128

    def _load_yasuo_sprites(self, factory):
        """Load Yasuo (Player 1) sprites."""
        self.anims_right = {}
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

        if not self.anims_right['idle']:
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(0, 100, 255), (40, 60))]

        self.anims_left = {}
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        self._render_w = 128
        self._render_h = 128
        
        # Load skill VFX frames
        skill_dir = os.path.join(root_dir, 'assets', 'Skills')
        self.skill_frames = {
            'q': load_tornado_assets(factory, skill_dir),
            'w': load_wall_assets(factory, skill_dir)
        }

    def _load_leaf_ranger_sprites(self, factory):
        """Load Leaf Ranger (Player 2) sprites with scaling and cropping."""
        import sys as _sys
        scale = 1.5
        universal_crop = (117, 45, 77, 83)

        def load_scaled_sequence(folder, prefix, count, crop_box=None):
            frames = []
            for i in range(1, count + 1):
                file_path = os.path.join(PLAYER2_ASSET_DIR, folder, f"{prefix}{i}.png")
                if not os.path.exists(file_path):
                    continue
                try:
                    surf_ptr = sdl2.ext.load_image(file_path)
                    if crop_box:
                        cx, cy, cw, ch = crop_box
                        src_rect = sdl2.SDL_Rect(cx, cy, cw, ch)
                    else:
                        orig_w = surf_ptr.w if hasattr(surf_ptr, 'w') else surf_ptr.contents.w
                        orig_h = surf_ptr.h if hasattr(surf_ptr, 'h') else surf_ptr.contents.h
                        src_rect = sdl2.SDL_Rect(0, 0, orig_w, orig_h)

                    new_w = int(src_rect.w * scale)
                    new_h = int(src_rect.h * scale)

                    rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
                    if _sys.byteorder == 'big':
                        rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff

                    scaled_surf = sdl2.SDL_CreateRGBSurface(0, new_w, new_h, 32, rmask, gmask, bmask, amask)
                    sdl2.SDL_SetSurfaceBlendMode(surf_ptr, sdl2.SDL_BLENDMODE_NONE)
                    dst_rect = sdl2.SDL_Rect(0, 0, new_w, new_h)
                    sdl2.SDL_BlitScaled(surf_ptr, src_rect, scaled_surf, dst_rect)
                    sprite = factory.from_surface(scaled_surf)
                    frames.append(sprite)
                    sdl2.SDL_FreeSurface(surf_ptr)
                except Exception as e:
                    print(f"[RemotePlayer] Scale error {file_path}: {e}")
            return frames

        self.anims_right = {}
        self.anims_right['idle']          = load_scaled_sequence('idle', 'idle_', 12, universal_crop)
        self.anims_right['run']           = load_scaled_sequence('run', 'run_', 10, universal_crop)
        self.anims_right['walk']          = list(self.anims_right['run'])  # Walk uses run frames
        self.anims_right['attack_normal'] = load_scaled_sequence('normal_attack', '2_atk_', 10, universal_crop)
        self.anims_right['block']         = load_scaled_sequence('defend', 'defend_', 19, universal_crop)
        self.anims_right['jump_up']       = load_scaled_sequence('jump_up', 'jump_up_', 3, universal_crop)
        self.anims_right['fall']          = load_scaled_sequence('jump_down', 'jump_down_', 3, universal_crop)
        self.anims_right['dead']          = load_scaled_sequence('death', 'death_', 19, universal_crop)
        self.anims_right['hurt']          = load_scaled_sequence('take_hit', 'take_hit_', 6, universal_crop)
        _skill_asset_dir = os.path.join(root_dir, 'assets', 'Skills')
        from combat.player_2.refactored_skill_q import load_laser_cast_animation_proportional
        from combat.player_2.refactored_skill_e import load_arrow_rain_cast_animation_proportional
        cast_crop = (90, 45, 120, 83)
        self.anims_right['q'] = load_laser_cast_animation_proportional(factory, _skill_asset_dir, scale_factor=scale, crop_box=cast_crop)
        self.anims_right['w'] = []  # W is instant buff, no anim
        self.anims_right['e'] = load_arrow_rain_cast_animation_proportional(factory, _skill_asset_dir, scale_factor=scale, crop_box=cast_crop)

        if not self.anims_right['idle']:
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(0, 200, 100), (40, 60))]

        self.anims_left = {}
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        # Set render size based on actual sprite dimensions
        if self.anims_right['idle']:
            self._render_w = self.anims_right['idle'][0].size[0]
            self._render_h = self.anims_right['idle'][0].size[1]
        print(f"[RemotePlayer] Leaf Ranger loaded: {self._render_w}x{self._render_h}")
        
        # Load skill VFX frames (graceful fallback if assets missing)
        _proj_asset_dir = os.path.join(root_dir, 'assets', 'Projectile')
        self.skill_frames = {'q': [], 'e': []}
        try:
            from combat.player_2.refactored_skill_q import load_laser_projectile_frames
            frames = load_laser_projectile_frames(factory, _proj_asset_dir)
            if frames:
                self.skill_frames['q'] = frames
        except Exception as e:
            print(f"[RemotePlayer] Could not load Leaf Ranger Q frames: {e}")
        try:
            from combat.player_2.refactored_skill_e import load_arrow_rain_cast_animation_proportional
            frames = load_arrow_rain_cast_animation_proportional(factory, _skill_asset_dir, scale_factor=scale)
            if frames:
                self.skill_frames['e'] = frames
        except Exception as e:
            print(f"[RemotePlayer] Could not load Leaf Ranger E frames: {e}")

    def set_character_type(self, char_type: str):
        """
        Switch the remote player's display character.
        Call once when the remote player's character choice is known.
        """
        if char_type == self._character_type:
            return  # Already loaded
        self._character_type = char_type
        print(f"[RemotePlayer] Switching to character: {char_type}")
        if char_type == 'leaf_ranger':
            self._load_leaf_ranger_sprites(self._factory)
        else:
            self._load_yasuo_sprites(self._factory)
        # Reset entity sprite
        if self.anims_right.get('idle'):
            old_pos = self.entity.sprite.position if self.entity.sprite else (200, 350)
            self.entity.sprite = self.anims_right['idle'][0]
            self.entity.sprite.position = old_pos

    # ── Network update ────────────────────────────────────────────────────

    def apply_network_state(self, net_state: dict):
        """
        Called every frame with the latest raw packet from the network layer.
        Pushes the snapshot into the interpolation buffer.
        """
        if not net_state:
            return
            
        ts = net_state.get('ts', 0)
        if hasattr(self, '_last_applied_ts') and ts <= self._last_applied_ts:
            return
        self._last_applied_ts = ts
        
        # Sync clocks: calculate the offset between local monotonic and sender's monotonic
        if not hasattr(self, '_clock_offset'):
            self._clock_offset = time.monotonic() - ts
            
        local_ts = ts + self._clock_offset
        
        self.visible = True
        self._interpolator.add_snapshot(
            ts=local_ts,
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

    def update(self, dt: float, my_map=None, obstacles=None, enemies=None):
        """
        Advance animation based on the interpolated network state.
        Call once per frame from the main game loop.
        """
        self.update_vfx(dt, my_map, obstacles, enemies)
        
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
            'jump':        'jump',      # Yasuo jump state
            'jump_up':     'jump_up',  # Leaf Ranger jump up
            'fall':        'fall',     # Leaf Ranger fall
        }
        key = state_to_anim.get(self.state, 'idle')
        result = anims.get(key)
        
        # Fallback chain for jump states:
        # - jump_up/fall not in anims (Yasuo) → try 'jump' → 'idle'
        # - jump not in anims (Leaf Ranger) → try 'jump_up' or 'fall' → 'idle'
        if not result:
            if key in ('jump_up', 'fall'):
                result = anims.get('jump')
            elif key == 'jump':
                result = anims.get('jump_up') or anims.get('fall')
        if not result:
            result = anims.get('idle', [])
        return result

    # ── Render & VFX ────────────────────────────────────────────────────────────

    def spawn_skill_vfx(self, skill_key: str, direction: int, x: float, y: float, game_map=None, camera=None):
        """Spawn purely visual effect objects for the remote player's skill casts."""
        frames = getattr(self, 'skill_frames', {}).get(skill_key)
        
        # Attack projectiles and ArrowRainProjectile load their own textures so they don't need frames
        if not frames and skill_key not in ['attack_normal', 'attack_w_poison', 'attack_w_plant', 'e']:
            return
        
        if self._character_type == 'yasuo':
            if skill_key == 'q':
                obj = TornadoObject(self._world, frames, x, y, direction, max_dist=700, max_hits=0, damage_multiplier=0)
                obj.is_visual_only = True
                self.active_vfx.append({'obj': obj, 'type': 'tornado', 'char': 'yasuo'})
            elif skill_key == 'w':
                obj = WallObject(self._world, frames, x, y, duration=4.0, damage_multiplier=0)
                obj.is_visual_only = True
                self.active_vfx.append({'obj': obj, 'type': 'wall', 'char': 'yasuo'})
        elif self._character_type == 'leaf_ranger':
            if skill_key == 'q':
                from combat.player_2.refactored_skill_q import LaserObject
                obj = LaserObject(self._world, frames, x, y, direction, laser_range=700, damage_multiplier=0)
                obj.is_visual_only = True
                self.active_vfx.append({'obj': obj, 'type': 'laser', 'char': 'leaf_ranger'})
            elif skill_key == 'e':
                from combat.player_2.refactored_skill_e import ArrowRainProjectile
                
                # In multiplayer, SKILL_EVENT for 'e' passes target_x as the `x` argument!
                target_x = x
                if camera and game_map:
                    obj = ArrowRainProjectile(
                        target_x=target_x,
                        owner=self,
                        renderer=self.renderer_ptr,
                        game_map=game_map,
                        camera=camera,
                        damage_multiplier=0  # Visual only, no damage
                    )
                    # Tell it not to root or do physics damage if we want,
                    # but since enemies list passed in update() is [], it naturally won't deal damage.
                    self.active_vfx.append({'obj': obj, 'type': 'arrow_rain_projectile', 'char': 'leaf_ranger'})
            elif skill_key in ('attack_normal', 'attack_w_poison', 'attack_w_plant'):
                from entities.leaf_ranger_projectile import NormalArrowProjectile, PoisonProjectile, PlantProjectile
                if skill_key == 'attack_normal':
                    obj = NormalArrowProjectile(x, y, direction, self, self.renderer_ptr)
                elif skill_key == 'attack_w_poison':
                    obj = PoisonProjectile(x, y, direction, self, self.renderer_ptr)
                else:
                    obj = PlantProjectile(x, y, direction, self, self.renderer_ptr)
                obj.is_visual_only = True
                self.active_vfx.append({'obj': obj, 'type': 'leaf_ranger_attack', 'char': 'leaf_ranger'})

    def update_vfx(self, dt: float, my_map=None, obstacles=None, enemies=None):
        """Update active skill VFX and check collisions."""
        from combat.refactored_skill_q import update_q_logic
        from combat.refactored_skill_w import update_w_logic
        
        for item in self.active_vfx[:]:
            obj = item['obj']
            if item['char'] == 'yasuo':
                if item['type'] == 'tornado':
                    update_q_logic(obj, [], dt, network_ctx=None)
                elif item['type'] == 'wall':
                    update_w_logic(obj, enemies=None, projectiles=None, dt=dt, network_ctx=None)
            elif item['char'] == 'leaf_ranger':
                if item['type'] == 'laser':
                    from combat.player_2.refactored_skill_q import update_q_laser_logic
                    update_q_laser_logic(obj, [], dt, network_ctx=None)
                elif item['type'] == 'arrow_rain_projectile':
                    aoe = obj.update(dt, [])
                    if aoe:
                        item['obj'] = aoe
                        item['type'] = 'arrow_rain_aoe'
                elif item['type'] == 'arrow_rain_aoe':
                    obj.update(dt)
                elif item['type'] == 'leaf_ranger_attack':
                    
                    # 1. Cho mũi tên ảo tương tác với Bản đồ (cắm vào tường/rương)
                    obj.update(dt, world=None, my_map=my_map, interactables=obstacles)
                    
                    # 2. Tự hủy mũi tên ảo nếu chạm Quái Vật
                    if enemies and obj.active:
                        for e in enemies:
                            if hasattr(e, 'is_alive') and not e.is_alive(): continue
                            if hasattr(obj, 'check_collision') and obj.check_collision(e):
                                if hasattr(obj, 'on_hit'): obj.on_hit()
                                else: obj.active = False
                                break
                                
                    # 3. Tự hủy mũi tên ảo nếu chạm Thùng Gỗ
                    # (Vì NormalArrowProjectile mặc định bỏ qua thùng gỗ để nhường cho vòng lặp chính phá)
                    if obstacles and obj.active:
                        import sdl2
                        for obs in obstacles:
                            if obs.__class__.__name__ == 'Barrel' and not obs.is_broken:
                                p_rect = sdl2.SDL_Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                                bx, by, bw, bh = obs.get_bounds()
                                b_rect = sdl2.SDL_Rect(int(bx), int(by), int(bw), int(bh))
                                
                                if sdl2.SDL_HasIntersection(p_rect, b_rect):
                                    if hasattr(obj, 'on_hit'): obj.on_hit()
                                    else: obj.active = False
                                    break
                                    
            # Remove inactive VFX
            if not getattr(obj, 'active', True):
                self.active_vfx.remove(item)

    def render(self, sdl_renderer, camera_x: float, camera_y: float):
        """Render the remote player and VFX with a blue tint."""
        # Render VFX
        for item in self.active_vfx:
            obj = item['obj']
            
            # Use obj.render() directly for custom projectiles/effects
            if item['type'] in ['leaf_ranger_attack', 'arrow_rain_projectile', 'arrow_rain_aoe']:
                if hasattr(obj, 'render'):
                    if item['type'] == 'arrow_rain_projectile':
                        # ArrowRainProjectile takes (renderer, camera)
                        # The object already has self.camera which was correctly passed at spawn!
                        obj.render(sdl_renderer, obj.camera)
                    elif item['type'] == 'arrow_rain_aoe':
                        # ArrowRainAoE takes (camera_x, camera_y)
                        obj.render(camera_x, camera_y)
                    else:
                        obj.render(camera_x, camera_y)
                continue

            # Handle VFX with list of sprites (Laser)
            if item['type'] == 'laser':
                if hasattr(obj, 'sprites') and obj.sprites:
                    sprite = obj.sprites[int(obj.anim_frame) % len(obj.sprites)]
                    if sprite and hasattr(sprite, 'surface') and sprite.surface:
                        tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, sprite.surface)
                        if tex:
                            sdl2.SDL_SetTextureColorMod(tex, REMOTE_TINT[0], REMOTE_TINT[1], REMOTE_TINT[2])
                            sdl2.SDL_SetTextureAlphaMod(tex, 180)
                            
                            if item['type'] == 'laser':
                                # Render beam using LeafRanger tiling style
                                sw, sh = sprite.surface.w, sprite.surface.h
                                num_tiles = max(1, int(obj.current_range / sw) + 1)
                                for i in range(num_tiles):
                                    tile_offset = i * sw
                                    if tile_offset >= obj.current_range: break
                                    remaining_range = obj.current_range - tile_offset
                                    tile_w = min(sw, int(remaining_range))
                                    
                                    if obj.direction > 0:
                                        rx = int(obj.x + tile_offset - camera_x)
                                    else:
                                        rx = int(obj.x - tile_offset - tile_w - camera_x)
                                    
                                    src_rect = sdl2.SDL_Rect(0, 0, tile_w, sh) if tile_w < sw else None
                                    dst_rect = sdl2.SDL_Rect(rx, int(obj.y - camera_y), tile_w, sh)
                                    sdl2.SDL_RenderCopy(sdl_renderer, tex, src_rect, dst_rect)
                                
                            sdl2.SDL_DestroyTexture(tex)
                continue

            # Handle VFX with single sprite (Yasuo Tornado/Wall)
            sprite = getattr(obj, 'sprite', None) or getattr(obj, 'current_sprite', None)
            if sprite and hasattr(sprite, 'surface') and sprite.surface:
                tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, sprite.surface)
                if tex:
                    sx = getattr(sprite, 'x', getattr(obj, 'current_x', 0))
                    sy = getattr(sprite, 'y', getattr(obj, 'current_y', 0))
                    dst = sdl2.SDL_Rect(int(sx - camera_x), int(sy - camera_y), sprite.surface.w, sprite.surface.h)
                    
                    sdl2.SDL_SetTextureColorMod(tex, REMOTE_TINT[0], REMOTE_TINT[1], REMOTE_TINT[2])
                    sdl2.SDL_SetTextureAlphaMod(tex, 180)
                    sdl2.SDL_RenderCopy(sdl_renderer, tex, None, dst)
                    sdl2.SDL_DestroyTexture(tex)

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

        # Use actual sprite size instead of hardcoded 128
        w = self.entity.sprite.size[0] if self.entity.sprite else self._render_w
        h = self.entity.sprite.size[1] if self.entity.sprite else self._render_h

        dst = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            w, h,
        )
        sdl2.SDL_RenderCopy(sdl_renderer, tex, None, dst)
        sdl2.SDL_DestroyTexture(tex)

        # Draw HP bar above remote player's head
        self._render_hp_bar(sdl_renderer, camera_x, camera_y)

    def _render_hp_bar(self, sdl_renderer, camera_x: float, camera_y: float):
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y) - 14

        bar_w, bar_h = 80, 8
        render_w = self.entity.sprite.size[0] if self.entity.sprite else self._render_w
        bar_x = screen_x + (render_w - bar_w) // 2
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
        render_w = self.entity.sprite.size[0] if self.entity.sprite else self._render_w
        render_h = self.entity.sprite.size[1] if self.entity.sprite else self._render_h
        if self._character_type == 'leaf_ranger':
            scale = 1.5
            hitbox_w = int(35 * scale)
            hitbox_h = int(60 * scale)
        else:
            hitbox_w, hitbox_h = 40, 80
        offset_x = (render_w - hitbox_w) // 2
        offset_y = (render_h - hitbox_h)
        return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y),
                             hitbox_w, hitbox_h)

    def get_bounds(self):
        r = self.get_hitbox()
        return (r.x, r.y, r.w, r.h)

    def is_alive(self) -> bool:
        return self.hp > 0
