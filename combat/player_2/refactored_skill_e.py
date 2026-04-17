import sdl2
import sdl2.ext
import os
import time
from combat.refactored_skill import BaseSkill
from combat.refactored_utils import load_image_sequence
from settings import SKILL_E_2_COOLDOWN, SKILL_E_2_CAST_RANGE
from entities.leaf_ranger_aoe import ArrowRainAoE

# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_arrow_rain_cast_animation(factory, skill_asset_dir, target_size=None):
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    sprites = load_image_sequence(
        factory,
        e_folder,
        prefix="3_atk_",
        count=12,
        target_size=target_size,
        zero_pad=False
    )
    return sprites


def load_arrow_rain_cast_animation_proportional(factory, skill_asset_dir, scale_factor=1.0, crop_box=None):
    """
    Load E cast animation with proportional scaling and optional cropping.
    
    E cast sprites are 288×128 pixels (same as idle and Q cast source images).
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
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    
    sprites = []
    for i in range(1, 13):  # 3_atk_1.png through 3_atk_12.png
        file_path = os.path.join(e_folder, f"3_atk_{i}.png")
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
            print(f"[ERROR] E cast frame {i}: {e}")
    
    if sprites:
        crop_info = f"crop={crop_box}" if crop_box else "no crop"
        print(f"[E CAST] Loaded {len(sprites)} frames: {sprites[0].size if sprites else 'N/A'} (factor={scale_factor}, {crop_info})")
    
    return sprites

# ─────────────────────────────────────────────────────────────────────────────
# MAIN SKILL CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SkillE(BaseSkill):
    def __init__(self, owner):
        super().__init__(owner, name="Arrow Rain", base_cooldown=SKILL_E_2_COOLDOWN)
        
        self.cast_range = SKILL_E_2_CAST_RANGE
        self.is_dashing = False # Flag giữ chỗ cho Animation của LeafRanger (Dùng chung từ BaseChar)

    def execute(self, renderer=None, game_map=None, **kwargs):
        """
        Execute is called mid-animation (frame 6) to spawn the actual AoE.
        """
        direction = 1 if self.owner.facing_right else -1
        
        # Calculate spawn position (center of AoE)
        spawn_x = self.owner.x + (self.cast_range * direction)
        
        spawn_y = self.owner.y + self.owner.height - 30 
        
        if game_map:
            tiles = game_map.get_tile_rects_around(spawn_x, self.owner.y, 200, 300)
            ground_y = spawn_y
            found_ground = False
            
            for tile in tiles:
                if tile.y > self.owner.y and abs(tile.x - spawn_x) < 150:
                    ground_y = tile.y
                    found_ground = True
                    break
            
            if found_ground: spawn_y = ground_y
            
        # Pass damage multiplier
        aoe = ArrowRainAoE(spawn_x, spawn_y, self.owner, renderer, damage_multiplier=self.damage_multiplier)
        return aoe

# ─────────────────────────────────────────────────────────────────────────────
# UPDATE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def update_e_aoe_logic(aoe_obj, enemies, dt, network_ctx=None):
    if not aoe_obj.active: return
    
    # 1. UPDATE ANIMATION AND LIFETIME
    aoe_obj.update(dt)
    
    # 2. COLLISION SCAN 
    for target in enemies:
        if not hasattr(target, 'is_alive'):
            if hasattr(target, 'health') and target.health <= 0: continue
        elif not target.is_alive(): continue
        
        if aoe_obj.check_collision(target):
            aoe_obj.apply_root(target, network_ctx)