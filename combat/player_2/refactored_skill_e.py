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

def load_arrow_rain_cast_animation(factory, skill_asset_dir):
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    sprites = load_image_sequence(
        factory,
        e_folder,
        prefix="3_atk_",
        count=12,
        target_size=(150, 150),
        zero_pad=False 
    )
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
        print(f"[{self.name}] Spawning AoE Object!")
        
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
            
        print(f"[{self.name}] Spawn coords: ({spawn_x}, {spawn_y})")
        
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