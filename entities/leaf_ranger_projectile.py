"""
Player 2 Projectile System

Two specialized projectile classes for Player 2's W skill (Toxin Enhancement):
1. PoisonProjectile - Deals damage
2. PlantProjectile  - Roots first enemy hit
"""

import os
import ctypes
import sdl2
import sdl2.ext
import time
from settings import (
    W_PROJECTILE_SPEED,
    DAMAGE_W_POISON,
    POISON_TICK_RATE,
    POISON_DURATION,
    DAMAGE_W_PLANT,
    W_PLANT_SNARE_DURATION,
    HEAL_W_DUST,
)

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR   = os.path.dirname(_MODULE_DIR)  # .../A3_Yasuo


class Player2Projectile:
    """
    Base class for Player 2 projectiles.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        velocity_x, velocity_y: Movement velocity
        direction: Movement direction (1 for right, -1 for left)
        active: Whether projectile is still active
        owner: Reference to the entity that fired this projectile (Player2)
        renderer: SDL2 renderer
        frame_textures: List of individual frame textures
        current_frame: Current animation frame
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
        lifetime: Maximum age in frames
        age: Current age in frames
    """
    
    def __init__(self, x, y, direction, owner, renderer, frame_count, texture_dir):
        """
        Initialize Player 2 projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Player2 that fired this projectile
            renderer: PySDL2 renderer
            frame_count: Number of animation frames to load
            texture_dir: Path to texture directory
        """
        self.x = x
        self.y = y
        self.width = 48
        self.height = 48
        self.velocity_x = W_PROJECTILE_SPEED * direction
        self.velocity_y = 0
        self.direction = direction
        self.active = True
        self.owner = owner
        self.renderer = renderer
        
        # Animation
        self.frame_textures = []
        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0
        
        # Lifetime (frames until auto-destroy)
        self.lifetime = 300  # 5 seconds at 60 FPS
        self.age = 0
        
        # Load textures
        self.texture_dir = texture_dir
        self.frame_count = frame_count
        self._load_textures()
    
    def _load_textures(self):
        """Load animation frame textures."""
        for i in range(1, self.frame_count + 1):
            filename = f"arrow_hit_poison_{i}.png"  # Will be overridden in subclasses
            filepath = os.path.join(self.texture_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Projectile frame not found: {filepath}")
    
    def update(self, delta_time=1, world = None, my_map = None, obstacles = None):
        """
        Update projectile position and animation.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if not self.active:
            return
        
        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Update animation
        self._update_animation()
        
        # Update lifetime
        self.age += 1
        if self.age >= self.lifetime:
            self.active = False
    
    def _update_animation(self):
        """Update animation frame."""
        if not self.frame_textures:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_textures)
    
    def render(self, camera_x=0, camera_y=0):
        """Render projectile sprite.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        if not self.active or not self.frame_textures:
            return
        
        # Get current frame texture
        texture = self.frame_textures[self.current_frame]
        
        # Destination rectangle (apply camera offset for screen-space rendering)
        dest_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        
        # Flip sprite based on direction
        flip = sdl2.SDL_FLIP_NONE
        if self.direction < 0:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
        # Render
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            None,  # Use entire texture
            dest_rect,
            0,
            None,
            flip
        )
    
    def get_bounds(self):
        """
        Get bounding box for collision detection.
        
        Returns:
            tuple: (x, y, width, height)
        """
        return (self.x, self.y, self.width, self.height)
    
    def check_collision(self, target):
        """
        Check collision with a target entity.
        
        Args:
            target: Entity with get_bounds() method
            
        Returns:
            bool: True if collision detected
        """
        if not self.active:
            return False
        
        # Get bounding boxes
        px, py, pw, ph = self.get_bounds()
        
        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
        else:
            # Fallback for sprite-based objects
            tx = target.x if hasattr(target, 'x') else target.sprite.x
            ty = target.y if hasattr(target, 'y') else target.sprite.y
            tw = target.width if hasattr(target, 'width') else target.sprite.size[0]
            th = target.height if hasattr(target, 'height') else target.sprite.size[1]
        
        # AABB collision detection
        return (px < tx + tw and
                px + pw > tx and
                py < ty + th and
                py + ph > ty)
    
    def cleanup(self):
        """Clean up resources."""
        for texture in self.frame_textures:
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.frame_textures.clear()

class NormalArrowProjectile(Player2Projectile):
    """
    Normal attack arrow for Player 2.
    Travels straight and deals base physical damage.
    """
    def __init__(self, x, y, direction, owner, renderer):
        import os
        import sdl2
        import sdl2.ext
        
        texture_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'Player_2', 'projectiles_and_effects', 'arrow')
        
        super().__init__(x, y, direction, owner, renderer, 1, texture_dir)
        
        self.velocity_x = 800 * direction
        self.velocity_y = 0
        
        self.damage = getattr(owner, 'attack_damage', 10) 
        
        self.start_x = x
        self.max_range = 300

        self.is_stuck = False
        self.stuck_timer = 0
        self.STUCK_DURATION = 1.0

        # Tiến hành cắt và phóng to mũi tên
        self._load_exact_arrow(texture_dir)

    def _load_textures(self):
        """No-op: NormalArrowProjectile uses _load_exact_arrow instead."""
        pass

    def _load_exact_arrow(self, texture_dir):
        """Cắt chính xác mũi tên từ sprite sheet và phóng to"""
        import sdl2
        import sdl2.ext
        import os
        import sys
        
        for tex in self.frame_textures:
            if tex: sdl2.SDL_DestroyTexture(tex)
        self.frame_textures.clear()
        
        filepath = os.path.join(texture_dir, 'arrow_.png')
        if os.path.exists(filepath):
            surf_ptr = sdl2.ext.load_image(filepath)

            # 1. Khung cắt (Crop box) dựa trên số đo của bạn
            cx, cy, cw, ch = 111, 61, 33, 4
            src_rect = sdl2.SDL_Rect(cx, cy, cw, ch)

            # 2. Phóng to mũi tên (Scale up 2.5 lần để dễ nhìn trên màn hình)
            scale = 1.5
            new_w = int(cw * scale)
            new_h = int(ch * scale)

            rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
            if sys.byteorder == 'big':
                rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff
                
            scaled_surf = sdl2.SDL_CreateRGBSurface(0, new_w, new_h, 32, rmask, gmask, bmask, amask)
            sdl2.SDL_SetSurfaceBlendMode(surf_ptr, sdl2.SDL_BLENDMODE_NONE)
            
            dst_rect = sdl2.SDL_Rect(0, 0, new_w, new_h)
            sdl2.SDL_BlitScaled(surf_ptr, src_rect, scaled_surf, dst_rect)

            # 3. Lật ảnh nếu đang quay mặt sang trái
            if self.direction < 0:
                dup_surface_ptr = sdl2.SDL_DuplicateSurface(scaled_surf)
                dup_surface = dup_surface_ptr.contents
                dst_px = sdl2.ext.pixels3d(dup_surface)
                dst_px[:] = dst_px[:, ::-1, :] # Flip horizontal
                sdl2.SDL_FreeSurface(scaled_surf)
                scaled_surf = dup_surface_ptr
                
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, scaled_surf)
            self.frame_textures.append(texture)
            
            # 4. CẬP NHẬT HITBOX chuẩn xác với kích thước mũi tên mới
            self.width = new_w
            self.height = new_h
                
            sdl2.SDL_FreeSurface(surf_ptr)
            sdl2.SDL_FreeSurface(scaled_surf)

    def check_collision(self, target):
        owner_class = getattr(self.owner, '__class__', None)
        target_class = getattr(target, '__class__', None)
        # Bay xuyên qua phe ta (Yasuo, LeafRanger)
        if target_class and target_class.__name__ in ['Yasuo', 'LeafRanger']:
            return False
            
        return super().check_collision(target)
    
    def update(self, dt, world=None, my_map=None, interactables=None):
        if not self.active:
            return

        if self.is_stuck:
            self.stuck_timer += dt
            if self.stuck_timer >= self.STUCK_DURATION:
                self.active = False
            return

        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        
        # Biến mất ngay lập tức khi ra khỏi tầm (Max Range)
        distance_traveled = abs(self.x - self.start_x)
        if distance_traveled >= self.max_range:
            self.active = False
            return

        # Check cắm vào tường
        if my_map:
            tiles = my_map.get_tile_rects_around(self.x, self.y, self.width, self.height)
            for tile in tiles:
                if self.check_world_collision(tile):
                    self._stick_to_surface()
                    return

        # Check cắm vào vật cản (Thùng, rương)
        if interactables:
            for obj in interactables:
                # [MỚI CHÈN VÀO]: Bỏ qua thùng gỗ (Barrel) để không bị ghim lại, nhường cho game.py xử lý nổ
                if obj.__class__.__name__ == 'Barrel':
                    continue

                if self.check_world_collision(obj):
                    self._stick_to_surface()
                    return

    def check_world_collision(self, obstacle):
        obj_x = getattr(obstacle, 'x', obstacle[0] if isinstance(obstacle, (list, tuple)) else 0)
        obj_y = getattr(obstacle, 'y', obstacle[1] if isinstance(obstacle, (list, tuple)) else 0)
        obj_w = getattr(obstacle, 'w', obstacle[2] if isinstance(obstacle, (list, tuple)) else 32)
        obj_h = getattr(obstacle, 'h', obstacle[3] if isinstance(obstacle, (list, tuple)) else 32)

        return (self.x < obj_x + obj_w and
                self.x + self.width > obj_x and
                self.y < obj_y + obj_h and
                self.y + self.height > obj_y)

    def _stick_to_surface(self):
        self.is_stuck = True
        self.velocity_x = 0
        self.velocity_y = 0
        self.stuck_timer = 0

    def on_hit(self):
        self.active = False

_W_HIT_ANIM_SPEED = 0.25  # animation frames advanced per update tick


class PoisonProjectile(NormalArrowProjectile):
    """
    W-enhanced normal attack: Poison shot.

    Flight phase  -> identical to NormalArrowProjectile (same cropped arrow
                     sprite, 800 px/s velocity, max-range / wall collision).
    Hit phase     -> plays the poison hit animation at the impact point and
                     then deactivates.  Poison effect is applied via
                     apply_effect(enemy), called by the game loop before on_hit().
    """

    def __init__(self, x, y, direction, owner, renderer, damage_multiplier=1.0):
        super().__init__(x, y, direction, owner, renderer)
        self.damage = DAMAGE_W_POISON * damage_multiplier

        # Hit-animation state
        self.is_hit          = False
        self.hit_frame       = 0
        self.hit_frame_ctr   = 0.0
        self.hit_textures    = []
        self.hit_w           = 0
        self.hit_h           = 0
        self.hit_impact_x    = 0   # world-space X centre saved at impact
        self.hit_impact_y    = 0   # world-space Y centre saved at impact
        # Per-subclass Y correction (pixels).  Positive = shift animation DOWN.
        # Accounts for the visual content not being centred within its crop rect.
        # Poison: content ~9 px below frame centre  → correction = 0 (close enough)
        # Plant:  content ~20 px above frame centre → correction = +20
        self._hit_y_correction = 0
        # Poison content bbox (114,26)→(178,88) in the 256×128 source.
        # Add 10 px padding and display at 1.5× crop size → 126×123.
        self._load_hit_textures("poison", "arrow_hit_poison_", 8,
                                src_x=104, src_y=16, src_w=84, src_h=82,
                                display_w=126, display_h=123)

    # ------------------------------------------------------------------
    def _load_hit_textures(self, subfolder, prefix, count,
                           src_x=0, src_y=0, src_w=256, src_h=128,
                           display_w=128, display_h=64):
        """Load W hit-animation frames, cropping to the visible content area.

        Args:
            subfolder / prefix / count : asset location as before.
            src_x, src_y, src_w, src_h : crop rect inside the 256×128 source
                                          image (use Pillow getbbox + padding).
            display_w, display_h        : final on-screen size (stored as
                                          self.hit_w / self.hit_h for render).
        """
        import sys
        self.hit_w = display_w
        self.hit_h = display_h

        folder = os.path.join(_ROOT_DIR, "assets", "Projectile",
                              "Player_2", "w", subfolder)
        rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
        if sys.byteorder == 'big':
            rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff

        for i in range(1, count + 1):
            fpath = os.path.join(folder, f"{prefix}{i}.png")
            if os.path.exists(fpath):
                try:
                    src_surf = sdl2.ext.load_image(fpath)
                    # Step 1: crop to the content area of this frame
                    crop = sdl2.SDL_CreateRGBSurface(0, src_w, src_h, 32,
                                                     rmask, gmask, bmask, amask)
                    crop_src  = sdl2.SDL_Rect(src_x, src_y, src_w, src_h)
                    crop_dst  = sdl2.SDL_Rect(0, 0, src_w, src_h)
                    sdl2.SDL_SetSurfaceBlendMode(src_surf, sdl2.SDL_BLENDMODE_NONE)
                    sdl2.SDL_BlitSurface(src_surf, crop_src, crop, crop_dst)
                    # Step 2: scale cropped region to display size
                    tmp = sdl2.SDL_CreateRGBSurface(0, display_w, display_h, 32,
                                                    rmask, gmask, bmask, amask)
                    sdl2.SDL_BlitScaled(crop, crop_dst, tmp,
                                        sdl2.SDL_Rect(0, 0, display_w, display_h))
                    tex = sdl2.SDL_CreateTextureFromSurface(self.renderer, tmp)
                    if tex:
                        self.hit_textures.append(tex)
                    else:
                        print(f"[W-Hit] SDL_CreateTextureFromSurface failed: {fpath}")
                    sdl2.SDL_FreeSurface(src_surf)
                    sdl2.SDL_FreeSurface(crop)
                    sdl2.SDL_FreeSurface(tmp)
                except Exception as e:
                    print(f"[W-Hit] load error {fpath}: {e}")
            else:
                print(f"[W-Hit] missing frame: {fpath}")
        print(f"[W-Hit] Loaded {len(self.hit_textures)}/{count} frames from "
              f"'{subfolder}' ({display_w}x{display_h} px)")

    # ------------------------------------------------------------------
    def apply_effect(self, enemy):
        """
        Apply poison effect to the enemy that was hit.
        Called by the game loop just before on_hit().
        """
        if hasattr(enemy, 'apply_poison'):
            enemy.apply_poison(POISON_DURATION, POISON_TICK_RATE)
        elif hasattr(enemy, 'poisoned_timer'):
            enemy.poisoned_timer   = max(getattr(enemy, 'poisoned_timer', 0),
                                         POISON_DURATION)
            enemy.poison_tick_rate = POISON_TICK_RATE
            enemy.poison_damage    = getattr(enemy, 'poison_damage',
                                             int(DAMAGE_W_POISON * 0.2))

    # ------------------------------------------------------------------
    def on_hit(self):
        """Switch to hit-animation mode; do NOT instantly deactivate."""
        if self.is_hit:          # ignore duplicate calls
            return
        self.is_hit        = True
        self.hit_frame     = 0
        self.hit_frame_ctr = 0.0
        self.velocity_x    = 0
        self.velocity_y    = 0
        # Freeze the impact position at the arrow's visual centre so the hit
        # animation stays perfectly aligned with the flight line.
        self.hit_impact_x  = self.x + self.width  // 2
        self.hit_impact_y  = self.y + self.height // 2 + self._hit_y_correction
        # active stays True so the manager keeps updating/rendering until
        # the animation finishes (update() sets active=False at the end)

    # ------------------------------------------------------------------
    def update(self, dt, world=None, my_map=None, interactables=None):
        if not self.active:
            return

        if self.is_hit:
            if not self.hit_textures:
                self.active = False
                return
            self.hit_frame_ctr += _W_HIT_ANIM_SPEED
            if self.hit_frame_ctr >= 1.0:
                self.hit_frame_ctr = 0.0
                self.hit_frame    += 1
                if self.hit_frame >= len(self.hit_textures):
                    self.active = False
            return

        # Flying phase – delegate fully to NormalArrowProjectile
        super().update(dt, world, my_map, interactables)

    # ------------------------------------------------------------------
    def render(self, camera_x=0, camera_y=0):
        if not self.active:
            return

        if self.is_hit and self.hit_textures:
            frame = min(self.hit_frame, len(self.hit_textures) - 1)
            tex   = self.hit_textures[frame]
            flip  = (sdl2.SDL_FLIP_HORIZONTAL
                     if self.direction < 0 else sdl2.SDL_FLIP_NONE)
            # Centre the animation on the exact point where the arrow struck.
            dst = sdl2.SDL_Rect(
                int(self.hit_impact_x - camera_x - self.hit_w // 2),
                int(self.hit_impact_y - camera_y - self.hit_h // 2),
                self.hit_w, self.hit_h
            )
            sdl2.SDL_RenderCopyEx(self.renderer, tex, None, dst, 0, None, flip)
            return

        # Flying phase – inherit NormalArrowProjectile -> Player2Projectile render
        super().render(camera_x, camera_y)

    # ------------------------------------------------------------------
    def cleanup(self):
        for tex in self.hit_textures:
            if tex:
                sdl2.SDL_DestroyTexture(tex)
        self.hit_textures.clear()
        super().cleanup()


class PlantProjectile(PoisonProjectile):
    """
    W-enhanced normal attack: Plant/root shot.

    Identical flight to PoisonProjectile, but plays the root (entangle) hit
    animation and applies a snare instead of poison on impact.
    """

    def __init__(self, x, y, direction, owner, renderer):
        super().__init__(x, y, direction, owner, renderer, damage_multiplier=1.0)
        self.damage        = DAMAGE_W_PLANT
        self.root_duration = W_PLANT_SNARE_DURATION

        # Replace poison hit textures with root textures
        for tex in self.hit_textures:
            if tex:
                sdl2.SDL_DestroyTexture(tex)
        self.hit_textures.clear()
        # Root content bbox (114,56)→(193,97) in the 256×128 source.
        # Add 10 px padding and display at 1.5× crop size → 148×92.
        self._load_hit_textures("root", "arrow_hit_entangle_", 8,
                                src_x=104, src_y=46, src_w=99, src_h=61,
                                display_w=148, display_h=92)
        # The entangle animation's visual content sits ~20 px above the
        # mathematical centre of the frame (content starts at ~26/92 from top
        # rather than at 50%).  Shift the anchor down so it aligns with the
        # arrow's actual flight line.
        self._hit_y_correction = 20

    def apply_effect(self, enemy):
        """Apply root/snare effect to the enemy that was hit."""
        print(f"[PlantProjectile] Root applied for {self.root_duration}s "
              f"on {enemy.__class__.__name__}")
        if hasattr(enemy, 'snared_timer'):
            enemy.snared_timer = self.root_duration
        elif hasattr(enemy, 'apply_snare'):
            enemy.apply_snare(self.root_duration)

