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
from entities.player_2_aoe import ArrowRainAoE


# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_arrow_rain_cast_animation(factory, skill_asset_dir):
    """
    Load the casting animation frames for Skill E (Arrow Rain).
    Expected: assets/Skills/skill_e_2/3_atk_1.png through 3_atk_12.png
    """
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    sprites = load_image_sequence(
        factory,
        e_folder,
        prefix="3_atk_",
        count=12,
        target_size=(150, 150),
        zero_pad=True
    )
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
    
    def execute(self, renderer, world=None):
        """
        Cast Arrow Rain AoE at a position in front of the player.
        
        Args:
            renderer: SDL2 renderer for texture loading
            world: SDL2 entity world (not used for AoE)
        
        Returns:
            ArrowRainAoE instance, or None if skill couldn't be cast
        """
        print("Casting E: Arrow Rain!")
        
        # Calculate spawn position (in front of player)
        direction = 1 if self.owner.facing_right else -1
        spawn_x = self.owner.sprite.x + (SKILL_E_2_CAST_RANGE * direction)
        spawn_y = self.owner.sprite.y + 80  # Slightly below center
        
        # Create AoE object
        aoe = ArrowRainAoE(spawn_x, spawn_y, renderer)
        self.aoe_active = aoe
        
        print(f"Arrow Rain spawned at ({spawn_x}, {spawn_y})")
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
        
        # Check if enemy is within AoE
        if aoe_obj.check_collision(target):
            # Apply root if not already hit
            aoe_obj.apply_root(target, network_ctx)
    
    # 3. AUTO-DESTROY when duration expires
    if aoe_obj.lifetime_timer <= 0:
        aoe_obj.active = False
        aoe_obj.cleanup()
        print("Arrow Rain AoE expired and destroyed")
