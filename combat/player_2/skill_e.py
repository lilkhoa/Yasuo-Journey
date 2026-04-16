"""
Player 2 Skill E - Arrow Rain (Large-Area Root AoE)

Arrow Rain is a crowd control skill that spawns a large area of effect
that roots all enemies within it for 1.5 seconds.
"""

import sdl2
import sdl2.ext
import os
import time
from combat.skill import Skill
from combat.utils import load_image_sequence
from settings import SKILL_E_2_COOLDOWN, SKILL_E_2_CAST_RANGE
from entities.leaf_ranger_aoe import ArrowRainAoE


# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_arrow_rain_cast_animation(factory, skill_asset_dir):
    """
    Load the casting animation frames for Skill E (Arrow Rain).
    Expected: assets/Skills/skill_e_2/3_atk_1.png through 3_atk_12.png
    """
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    print(f"[load_arrow_rain_cast_animation] Loading from: {e_folder}")
    print(f"[load_arrow_rain_cast_animation] Folder exists: {os.path.exists(e_folder)}")
    
    sprites = load_image_sequence(
        factory,
        e_folder,
        prefix="3_atk_",
        count=12,
        target_size=(150, 150),
        zero_pad=False  # Files are 3_atk_1.png, not 3_atk_001.png
    )
    print(f"[load_arrow_rain_cast_animation] Loaded {len(sprites)} frames")
    return sprites


# ─────────────────────────────────────────────────────────────────────────────
# SKILL E - ARROW RAIN
# ─────────────────────────────────────────────────────────────────────────────

class SkillE(Skill):
    """
    E Skill: Arrow Rain – Large-Area Root AoE
    
    This skill spawns a large circular area that roots all enemies within it.
    Unlike Q (laser) which is hit-scan and W (projectile-based), E creates
    a persistent AoE that affects multiple enemies over time.
    """
    
    def __init__(self, owner):
        """
        Initialize Skill E.
        
        Args:
            owner: Player2 instance (the skill owner)
        """
        super().__init__(owner, cooldown_time=SKILL_E_2_COOLDOWN)
        self.aoe_active = None  # Current ArrowRainAoE instance
        # Polymorphic interface: Player2's E is an AoE drop, not a dash.
        # game.py reads skill_e.is_dashing for all character types, so we
        # expose the attribute here and keep it permanently False.
        self.is_dashing = False
    
    def execute(self, renderer, game_map=None, enemies=None):
        """
        Cast Arrow Rain AoE targeting the nearest enemy in range.
        If no enemy is in range, fires to the maximum cast distance.
        The AoE bottom edge aligns with the terrain surface.
        
        Args:
            renderer: SDL2 renderer for texture loading
            game_map: GameMap instance for terrain height calculation
            enemies: List of live enemy targets for targeting selection
        
        Returns:
            ArrowRainAoE instance
        """
        direction = 1 if self.owner.facing_right else -1
        player_cx = self.owner.sprite.x + 64  # Center of 128px-wide sprite
        
        # Target nearest enemy in facing direction within cast range
        spawn_x = player_cx + SKILL_E_2_CAST_RANGE * direction  # Default: max range
        if enemies:
            candidates = []
            for target in enemies:
                if hasattr(target, 'is_alive') and not target.is_alive():
                    continue
                if hasattr(target, 'health') and target.health <= 0:
                    continue
                if hasattr(target, 'get_bounds'):
                    tx, ty, tw, th = target.get_bounds()
                    ex = tx + tw // 2
                elif hasattr(target, 'x'):
                    ex = target.x + getattr(target, 'width', 32) // 2
                else:
                    continue
                dx = ex - player_cx
                in_facing_dir = (direction > 0 and dx > 0) or (direction < 0 and dx < 0)
                if in_facing_dir and abs(dx) <= SKILL_E_2_CAST_RANGE:
                    candidates.append((abs(dx), ex))
            if candidates:
                candidates.sort()
                spawn_x = candidates[0][1]  # Nearest enemy's center X
        
        # Ground Y: bottom of AoE aligns with terrain surface
        if game_map:
            ground_height = game_map.get_ground_height_at_x(spawn_x)
            if ground_height is not None:
                spawn_y = ground_height - SKILL_E_2_HEIGHT // 2
            else:
                spawn_y = self.owner.sprite.y + 128 - SKILL_E_2_HEIGHT // 2
        else:
            spawn_y = self.owner.sprite.y + 128 - SKILL_E_2_HEIGHT // 2
        
        aoe = ArrowRainAoE(spawn_x, spawn_y, renderer, damage=DAMAGE_SKILL_E_2)
        self.aoe_active = aoe
        return aoe

    def update_dash(self, dt, enemies, boxes=None, game_map=None, network_ctx=None):
        """
        Polymorphic stub: Player2's E skill doesn't use dashing.
        This method is here for interface compatibility with Yasuo's SkillE.
        
        Args:
            dt: Delta time
            enemies: List of enemies
            boxes: Obstacle boxes
            game_map: Game map
            network_ctx: Network context tuple
        """
        pass  # Player2's E uses AoE casting, not dashing


# ─────────────────────────────────────────────────────────────────────────────
# AoE UPDATE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def update_e_aoe_logic(aoe_obj, enemies, dt, network_ctx=None):
    """
    Update Arrow Rain AoE and apply root effects.
    
    Logic Flow:
    1. Update AoE animation and lifetime
    2. Each frame, scan for enemies in AoE zone
    3. Apply root effect to any enemy hit for first time
    4. Auto-destroy when duration expires
    
    Args:
        aoe_obj: ArrowRainAoE instance
        enemies: List of NPC/Boss/Minion targets
        dt: Delta time (seconds)
        network_ctx: Tuple (is_multi, is_host, game_client) for network integration
    """
    if not aoe_obj.active:
        return
    
    # 1. UPDATE ANIMATION AND LIFETIME
    aoe_obj.update(dt)
    
    # 2. COLLISION SCAN - Check all enemies each frame
    for target in enemies:
        # Skip dead or invalid targets
        if not hasattr(target, 'is_alive'):
            if hasattr(target, 'health') and target.health <= 0:
                continue
        elif not target.is_alive():
            continue
        
        # Damage: any enemy inside the arrow column
        if aoe_obj.check_collision(target):
            aoe_obj.apply_damage(target, network_ctx)
        
        # Root: only enemies standing inside the ground impact zone
        rz = aoe_obj.get_root_zone_hitbox()
        rz_rect = sdl2.SDL_Rect(int(rz[0]), int(rz[1]), int(rz[2]), int(rz[3]))
        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
        else:
            tx = target.x if hasattr(target, 'x') else 0
            ty = target.y if hasattr(target, 'y') else 0
            tw = getattr(target, 'width', 32)
            th = getattr(target, 'height', 64)
        t_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
        if sdl2.SDL_HasIntersection(rz_rect, t_rect):
            aoe_obj.apply_root(target, network_ctx)
    
    # 3. AUTO-DESTROY when duration expires
    if aoe_obj.lifetime_timer <= 0:
        aoe_obj.active = False
        aoe_obj.cleanup()
