import sdl2
import sdl2.ext
import os
import time
from combat.skill import Skill
from combat.utils import load_image_sequence

# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_laser_cast_animation(factory, skill_asset_dir):
    """
    Load the casting animation frames for Skill Q (Laser beam).
    Expected: assets/Skills/skill_q_2/sp_atk_1.png through sp_atk_17.png
    """
    q_folder = os.path.join(skill_asset_dir, "skill_q_2")
    sprites = load_image_sequence(
        factory,
        q_folder,
        prefix="sp_atk_",
        count=17,
        target_size=(150, 150),
        zero_pad=False
    )
    return sprites


def load_laser_projectile_frames(factory, projectile_asset_dir):
    """
    Load the laser beam visual frames.
    Expected: assets/Projectile/Player_2/q/beam_extension_effect_1.png through beam_extension_effect_5.png
    """
    laser_folder = os.path.join(projectile_asset_dir, "Player_2", "q")
    sprites = load_image_sequence(
        factory,
        laser_folder,
        prefix="beam_extension_effect_",
        count=5,
        target_size=(800, 80),
        zero_pad=False
    )
    return sprites


# ─────────────────────────────────────────────────────────────────────────────
# LASER OBJECT
# ─────────────────────────────────────────────────────────────────────────────

class LaserObject:
    """
    Represents a laser beam projectile.
    - Displays laser animation
    - Manages hitbox for collision detection
    - Tracks hit list to prevent repeated damage on same target
    """

    def __init__(self, world, sprites_list, x, y, direction, laser_range, damage_multiplier=1.0):
        """
        Args:
            world: SDL world/entity container
            sprites_list: List of sprite frames for the laser animation
            x, y: Origin position (character's weapon/hand)
            direction: 1 for right, -1 for left
            laser_range: Maximum range of the laser (pixels)
            damage_multiplier: Damage scaling multiplier
        """
        self.entity = sdl2.ext.Entity(world)
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        self.entity.sprite = self.sprites[0] if self.sprites else None
        
        if self.entity.sprite:
            self.entity.sprite.position = x, y
        
        self.x = x
        self.y = y
        self.direction = direction
        self.max_range = laser_range
        
        # Damage settings
        from settings import DAMAGE_SKILL_Q_2
        self.damage = DAMAGE_SKILL_Q_2 * damage_multiplier
        
        # Animation
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.1  # Frame duration in seconds (slower cycling)
        self.anim_duration = 0.6  # Total laser duration (visible longer)
        self.total_timer = 0
        
        # Active state
        self.active = True
        
        # Collision tracking - store net_id of targets already hit
        self.hit_list = []

    @property
    def sprite(self):
        return self.entity.sprite

    def get_hitbox(self):
        """
        Return a long rectangular hitbox for the laser beam.
        - Width: extends along the direction
        - Height: laser thickness
        """
        if not self.sprite:
            return sdl2.SDL_Rect(0, 0, 0, 0)
        
        laser_width = self.max_range
        laser_height = 40  # Laser thickness
        
        # Calculate hitbox position
        if self.direction > 0:  # Facing right
            hitbox_x = int(self.x)
        else:  # Facing left - extend hitbox to the left
            hitbox_x = int(self.x - laser_width)
        
        hitbox_y = int(self.y + self.sprite.size[1] // 2 - laser_height // 2)
        
        return sdl2.SDL_Rect(hitbox_x, hitbox_y, laser_width, laser_height)

    def delete(self):
        self.entity.delete()


# ─────────────────────────────────────────────────────────────────────────────
# SKILL Q - LASER
# ─────────────────────────────────────────────────────────────────────────────

class SkillQLaser(Skill):
    """
    Q Skill: Fire a laser beam.
    
    This is a hit-scan ability (instant damage along a straight line).
    Unlike projectiles that move frame-by-frame, the laser doesn't require
    continuous network synchronization for its position.
    """

    def __init__(self, owner):
        super().__init__(owner, cooldown_time=0.1)

    def execute(self, world, factory, renderer, skill_sprites=None):
        """
        Cast the laser beam.
        
        Args:
            world: SDL entity container
            factory: Sprite factory
            renderer: Renderer (for texture creation)
            skill_sprites: Pre-loaded laser animation frames
        
        Returns:
            LaserObject instance, or None if skill failed
        """
        print("Casting Q: Laser Beam!")
        
        sprites_to_use = skill_sprites if skill_sprites else [
            factory.from_color(sdl2.ext.Color(255, 255, 0), size=(800, 80))
        ]
        
        direction = 1 if self.owner.facing_right else -1
        
        # Origin: slightly offset from character's center
        start_x = self.owner.sprite.x + (62 * direction)
        # Position it around the middle/bow area rather than above the head
        start_y = self.owner.sprite.y + 61
        
        laser = LaserObject(
            world,
            sprites_to_use,
            start_x,
            start_y,
            direction,
            laser_range=700,
            damage_multiplier=self.damage_multiplier
        )
        
        return laser


# ─────────────────────────────────────────────────────────────────────────────
# LASER UPDATE LOGIC
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
        network_ctx: Tuple (is_multi, is_host, game_client) for network integration
    """
    if not laser_obj.active:
        return

    # 1. UPDATE ANIMATION
    if len(laser_obj.sprites) > 1:
        laser_obj.anim_timer += dt
        
        if laser_obj.anim_timer >= laser_obj.anim_speed:
            laser_obj.anim_timer = 0
            laser_obj.anim_frame = (laser_obj.anim_frame + 1) % len(laser_obj.sprites)
            
            # Update sprite display (write via entity.sprite — .sprite is read-only property)
            if laser_obj.entity.sprite:
                old_x, old_y = laser_obj.entity.sprite.position
                laser_obj.entity.sprite = laser_obj.sprites[laser_obj.anim_frame]
                laser_obj.entity.sprite.position = old_x, old_y

    # 2. UPDATE LIFETIME
    laser_obj.total_timer += dt
    if laser_obj.total_timer >= laser_obj.anim_duration:
        laser_obj.active = False
        laser_obj.delete()
        return

    # 3. HIT-SCAN COLLISION DETECTION (First frame only - instant all-targets check)
    if laser_obj.total_timer < dt * 1.5:  # During first frame(s) of existence
        laser_rect = laser_obj.get_hitbox()
        
        for target in enemies:
            # Skip dead or invalid targets
            if not hasattr(target, 'is_alive') or not target.is_alive():
                continue
            
            # Get target's net_id to track if already hit
            target_net_id = getattr(target, 'net_id', id(target))
            
            # Skip if already hit by this laser
            if target_net_id in laser_obj.hit_list:
                continue
            
            # Get target hitbox
            if hasattr(target, 'get_bounds'):
                tx, ty, tw, th = target.get_bounds()
                target_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
            else:
                # Fallback for simple sprite-based objects
                target_rect = sdl2.SDL_Rect(
                    int(target.sprite.x),
                    int(target.sprite.y),
                    int(target.sprite.size[0]),
                    int(target.sprite.size[1])
                )
            
            # Check collision
            if sdl2.SDL_HasIntersection(laser_rect, target_rect):
                damage = laser_obj.damage
                
                print(f"Q Laser Hit! Damage: {damage}")
                
                # 4. APPLY DAMAGE - Network-aware
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    
                    if is_multi and game_client and game_client.is_connected():
                        # Online: Send hit event to server
                        etype = 'boss' if target.__class__.__name__ == 'Boss' else 'npc'
                        game_client.send_hit_event(etype, target_net_id, damage)
                    else:
                        # Offline: Apply damage locally
                        if hasattr(target, 'take_damage'):
                            target.take_damage(damage)
                else:
                    # No network context: Apply damage locally
                    if hasattr(target, 'take_damage'):
                        target.take_damage(damage)
                
                # Mark target as hit by this laser (prevents repeated hits)
                laser_obj.hit_list.append(target_net_id)
                
                # Optional: Apply knockback effect
                if hasattr(target, 'apply_knockup'):
                    target.apply_knockup(-10)
                elif hasattr(target, 'velocity_y'):
                    target.velocity_y = -8
