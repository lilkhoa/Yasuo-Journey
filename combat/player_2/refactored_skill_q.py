"""
refactored_skill_q.py – Q Skill (Laser Beam) for LeafRanger character

This skill fires a horizontal laser beam that instantly hits all enemies in its path.
Unlike Yasuo's tornado (projectile-based), this is a hitscan weapon with visual effects.

Network sync:
- SKILL_EVENT sent when cast (for animation sync)
- HIT_EVENT sent for each enemy hit (server authoritative damage)
"""

import sdl2
import sdl2.ext
import os
import time
from combat.refactored_skill import BaseSkill
from combat.refactored_utils import load_image_sequence
from settings import DAMAGE_SKILL_Q_2

# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_laser_cast_animation(factory, skill_asset_dir, target_size=None):
    """
    Load the casting animation frames for Skill Q (Laser beam).
    Expected: assets/Skills/skill_q_2/sp_atk_1.png through sp_atk_17.png
    
    Args:
        factory: Sprite factory for creating sprites
        skill_asset_dir: Path to Skills folder
        target_size: (width, height) tuple to scale sprites. 
                    For LeafRanger with scale_factor=1.5, this should be (225, 225)
                    to match the idle character size (77×83 crop × 1.5 ≈ 115×124)
    """
    q_folder = os.path.join(skill_asset_dir, "skill_q_2")
    sprites = load_image_sequence(
        factory,
        q_folder,
        prefix="sp_atk_",
        count=17,
        target_size=target_size,
        zero_pad=False
    )
    return sprites


def load_laser_cast_animation_proportional(factory, skill_asset_dir, scale_factor=1.0, crop_box=None):
    """
    Load Q cast animation with proportional scaling and optional cropping.
    
    Q cast sprites are 288×128 pixels (same as idle source images).
    They need the SAME crop box as idle to keep character position consistent.
    
    Args:
        factory: Sprite factory
        skill_asset_dir: Path to Skills folder
        scale_factor: Scaling multiplier (e.g., 1.5 for LeafRanger)
        crop_box: (x, y, w, h) tuple for cropping, e.g., (117, 45, 77, 83)
    """
    import sdl2
    import sdl2.ext
    import sys
    q_folder = os.path.join(skill_asset_dir, "skill_q_2")
    
    sprites = []
    for i in range(1, 18):  # sp_atk_1.png through sp_atk_17.png
        file_path = os.path.join(q_folder, f"sp_atk_{i}.png")
        if not os.path.exists(file_path):
            continue
        
        try:
            surf_ptr = sdl2.ext.load_image(file_path)
            
            # Apply crop box if provided (SAME as idle sprites)
            if crop_box:
                cx, cy, cw, ch = crop_box
                src_rect = sdl2.SDL_Rect(cx, cy, cw, ch)
            else:
                orig_w = surf_ptr.w if hasattr(surf_ptr, 'w') else surf_ptr.contents.w
                orig_h = surf_ptr.h if hasattr(surf_ptr, 'h') else surf_ptr.contents.h
                src_rect = sdl2.SDL_Rect(0, 0, orig_w, orig_h)
            
            # Scale the cropped region
            new_w = int(src_rect.w * scale_factor)
            new_h = int(src_rect.h * scale_factor)
            
            rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
            if sys.byteorder == 'big':
                rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff
            
            scaled_surf = sdl2.SDL_CreateRGBSurface(0, new_w, new_h, 32, rmask, gmask, bmask, amask)
            sdl2.SDL_SetSurfaceBlendMode(surf_ptr, sdl2.SDL_BLENDMODE_NONE)
            
            dst_rect = sdl2.SDL_Rect(0, 0, new_w, new_h)
            sdl2.SDL_BlitScaled(surf_ptr, src_rect, scaled_surf, dst_rect)
            
            sprite = factory.from_surface(scaled_surf)
            sprites.append(sprite)
            sdl2.SDL_FreeSurface(surf_ptr)
        except Exception as e:
            print(f"[ERROR] Q cast frame {i}: {e}")
    
    if sprites:
        crop_info = f"crop={crop_box}" if crop_box else "no crop"
        print(f"[Q CAST] Loaded {len(sprites)} frames: {sprites[0].size if sprites else 'N/A'} (factor={scale_factor}, {crop_info})")
    
    return sprites


def load_laser_projectile_frames(factory, projectile_asset_dir, target_size=(800, 80)):
    """
    Load the laser beam visual effect frames.
    Expected: assets/Projectile/Player_2/q/beam_extension_effect_1.png through 5.png
    
    Note: Laser is purely visual - damage is applied instantly via hitscan
    """
    laser_folder = os.path.join(projectile_asset_dir, "Player_2", "q")
    sprites = load_image_sequence(
        factory,
        laser_folder,
        prefix="beam_extension_effect_",
        count=5,
        target_size=target_size,
        zero_pad=False
    )
    return sprites


# ─────────────────────────────────────────────────────────────────────────────
# LASER OBJECT (Visual effect + hitbox tracking)
# ─────────────────────────────────────────────────────────────────────────────

class LaserObject:
    """
    Represents a laser beam visual effect.
    - Displays animated laser beam
    - Manages hitbox for collision detection
    - Tracks hit list to prevent repeated damage on same target
    - Has fixed lifetime (not distance-based)
    """

    def __init__(self, world, sprites_list, x, y, direction, laser_range=700, damage_multiplier=1.0):
        """
        Args:
            world: SDL world/entity container (not used, kept for compatibility)
            sprites_list: List of sprite frames for the laser animation
            x, y: Origin position (character's weapon/hand)
            direction: 1 for right, -1 for left
            laser_range: Maximum range of the laser (pixels)
            damage_multiplier: Damage scaling multiplier from skill level/stats
        """
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        
        self.x = x
        self.y = y
        self.direction = direction
        self.max_range = laser_range
        self.current_range = laser_range  # For rendering - hitscan laser is at full range immediately
        
        # Damage settings
        self.damage = DAMAGE_SKILL_Q_2 * damage_multiplier
        
        # Animation state
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.1  # Frame duration in seconds
        self.anim_duration = 0.6  # Total laser visual duration
        self.spawn_time = time.time()
        
        # Active state
        self.active = True
        
        # Collision tracking - store net_id of targets already hit
        # (prevents multi-hit on same target)
        self.hit_list = []
        
        print(f"[LASER OBJECT] Created: pos=({x:.1f},{y:.1f}), dir={direction}, "
              f"range={laser_range}, sprites={len(self.sprites)}, sprite_size={self.sprites[0].size if self.sprites else 'N/A'}")

    def get_hitbox(self):
        """
        Returns SDL_Rect representing the laser's damage area.
        Laser is a long horizontal rectangle extending from spawn point.
        """
        hitbox_height = 40
        # Centre the hitbox vertically on the spawn Y
        hitbox_y = int(self.y - hitbox_height // 2)

        if self.direction > 0:  # Firing right
            return sdl2.SDL_Rect(int(self.x), hitbox_y, self.max_range, hitbox_height)
        else:                   # Firing left
            return sdl2.SDL_Rect(int(self.x - self.max_range), hitbox_y,
                                 self.max_range, hitbox_height)

    def delete(self):
        self.active = False


# ─────────────────────────────────────────────────────────────────────────────
# SKILL CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SkillQLaser(BaseSkill):
    """Q Skill: Fire a laser beam (LeafRanger)."""

    def __init__(self, owner):
        super().__init__(owner, name="Laser Beam", base_cooldown=0.1)

    def execute(self, world, factory, renderer, skill_sprites=None, **kwargs):
        """
        Spawn a LaserObject at the character's weapon/hand position.

        Args:
            skill_sprites: Pre-loaded laser animation frames; falls back to a
                           plain yellow rectangle if not provided.
        Returns:
            LaserObject
        """
        sprites_to_use = skill_sprites or [
            factory.from_color(sdl2.ext.Color(255, 255, 0), size=(800, 80))
        ]

        direction = 1 if self.owner.facing_right else -1

        # Spawn offsets scaled proportionally with sprite size to maintain bow alignment.
        # Base offsets (62, 61) calibrated for 128×128 Yasuo sprites.
        # LeafRanger: idle ~115×124 (cropped 77×83 × 1.5), Q/E cast 432×192 (288×128 × 1.5)
        # This ensures laser always originates from character's bow/hand position
        sprite_w = self.owner.sprite.size[0] if self.owner.sprite else 128
        sprite_h = self.owner.sprite.size[1] if self.owner.sprite else 128
        
        # Scale offsets: idle (115px) → ~56px, cast (432px) → ~209px
        offset_x = int(62 * sprite_w / 128)
        offset_y = int(61 * sprite_h / 128)
        
        start_x = self.owner.sprite.x + (offset_x * direction)
        start_y = self.owner.sprite.y + offset_y

        laser_range = kwargs.get('laser_range', 700)

        laser = LaserObject(
            world,
            sprites_to_use,
            start_x,
            start_y,
            direction,
            laser_range=laser_range,
            damage_multiplier=self.damage_multiplier,
        )
        return laser


# ─────────────────────────────────────────────────────────────────────────────
# LASER UPDATE LOGIC (called per-frame by LeafRanger.update_skills)
# ─────────────────────────────────────────────────────────────────────────────

def update_q_laser_logic(laser_obj, enemies, dt, network_ctx=None):
    """
    Update and manage the laser beam each frame.
    
    Logic Flow:
    1. Update animation frame
    2. Check lifetime - deactivate when duration expires
    3. Perform hit-scan collision detection (first frame only)
    4. Send network damage events
    5. Clean memory when done
    
    Args:
        laser_obj: LaserObject instance
        enemies: List of NPC/Boss/Minion targets
        dt: Delta time (seconds)
        network_ctx: (is_multiplayer, is_host, game_client) tuple for network sync
    """
    if not laser_obj.active:
        return

    # 1. Animation
    if len(laser_obj.sprites) > 1:
        laser_obj.anim_timer += dt
        if laser_obj.anim_timer >= laser_obj.anim_speed:
            laser_obj.anim_timer = 0
            laser_obj.anim_frame = (laser_obj.anim_frame + 1) % len(laser_obj.sprites)

    # 2. Lifetime check
    elapsed = time.time() - laser_obj.spawn_time
    if elapsed >= laser_obj.anim_duration:
        laser_obj.active = False
        return

    # 3. Hit-scan collision (only on first frame to prevent multi-hit)
    # Laser damage is instant, not per-frame like tornado
    if elapsed < dt:  # First frame only
        laser_hitbox = laser_obj.get_hitbox()

        for target in enemies:
            if not hasattr(target, 'is_alive') or not target.is_alive():
                continue

            # Get target hitbox
            if hasattr(target, 'get_bounds'):
                tx, ty, tw, th = target.get_bounds()
                target_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
            else:
                target_rect = sdl2.SDL_Rect(
                    int(target.sprite.x), int(target.sprite.y),
                    int(target.sprite.size[0]), int(target.sprite.size[1])
                )

            # Check collision
            if sdl2.SDL_HasIntersection(laser_hitbox, target_rect):
                target_id = getattr(target, 'net_id', id(target))

                # Only hit each target once
                if target_id not in laser_obj.hit_list:
                    laser_obj.hit_list.append(target_id)
                    damage = int(laser_obj.damage)

                    # Network synchronization
                    if network_ctx:
                        is_multi, is_host, game_client = network_ctx
                        if is_multi and game_client and game_client.is_connected():
                            # Send HIT_EVENT to server for authoritative damage
                            etype = 'boss' if target.__class__.__name__ == 'Boss' else 'npc'
                            game_client.send_hit_event(etype, target_id, damage)
                        else:
                            # Offline or host applies damage directly
                            if hasattr(target, 'take_damage'):
                                target.take_damage(damage)
                    else:
                        # No network context - offline single player
                        if hasattr(target, 'take_damage'):
                            target.take_damage(damage)
