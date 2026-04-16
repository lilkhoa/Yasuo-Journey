import sdl2
import sdl2.ext
import os
import time
from combat.refactored_skill import BaseSkill
from combat.refactored_utils import load_image_sequence

# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_laser_cast_animation(factory, skill_asset_dir):
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
# LASER PROJECTILE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

class LaserObject:
    def __init__(self, world, sprites_list, x, y, direction, damage_multiplier=1.0):
        self.world = world
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        self.x = x
        self.y = y
        self.direction = direction
        
        self.active = True
        self.spawn_time = time.time()
        self.duration = 0.5 
        
        self.max_range = 800
        
        from settings import DAMAGE_SKILL_Q
        self.damage = DAMAGE_SKILL_Q * damage_multiplier
        
        self.hit_list = []
        
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.05
        
    def get_hitbox(self):
        hitbox_height = 40
        y_offset = 20
        
        if self.direction > 0:
            return sdl2.SDL_Rect(int(self.x), int(self.y + y_offset), self.max_range, hitbox_height)
        else:
            return sdl2.SDL_Rect(int(self.x - self.max_range), int(self.y + y_offset), self.max_range, hitbox_height)

    def delete(self):
        self.active = False

# ─────────────────────────────────────────────────────────────────────────────
# MAIN SKILL CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SkillQLaser(BaseSkill):
    def __init__(self, owner):
        super().__init__(owner, name="Laser Beam", base_cooldown=0.1)
        
    def execute(self, world, factory, renderer, skill_sprites=None, **kwargs):
        print("Spawning Laser Projectile!")
        
        direction = 1 if self.owner.facing_right else -1
        
        spawn_x = self.owner.sprite.x + (60 * direction)
        spawn_y = self.owner.sprite.y + 40
        
        sprites_to_use = skill_sprites if skill_sprites else [factory.from_color(sdl2.ext.Color(255, 255, 0), size=(800, 80))]
        
        laser = LaserObject(world, sprites_to_use, spawn_x, spawn_y, direction, damage_multiplier=self.damage_multiplier)
        return laser

# ─────────────────────────────────────────────────────────────────────────────
# UPDATE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def update_q_laser_logic(laser_obj, enemies, dt, network_ctx=None):
    if not laser_obj.active: return
    
    # 1. LIFETIME
    if time.time() - laser_obj.spawn_time > laser_obj.duration:
        laser_obj.delete()
        return
        
    # 2. ANIMATION
    if len(laser_obj.sprites) > 1:
        laser_obj.anim_timer += dt
        if laser_obj.anim_timer >= laser_obj.anim_speed:
            laser_obj.anim_timer = 0
            laser_obj.anim_frame = (laser_obj.anim_frame + 1) % len(laser_obj.sprites)

    # 3. COLLISION
    laser_rect = laser_obj.get_hitbox()
    
    for target in enemies:
        if not hasattr(target, 'is_alive') or not target.is_alive(): continue
            
        target_net_id = getattr(target, 'net_id', id(target))
        if target_net_id in laser_obj.hit_list: continue

        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
            target_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
        else:
            target_rect = sdl2.SDL_Rect(int(target.sprite.x), int(target.sprite.y), 
                                        int(target.sprite.size[0]), int(target.sprite.size[1]))

        if sdl2.SDL_HasIntersection(laser_rect, target_rect):
            damage = laser_obj.damage
            print(f"Q Laser Hit! Damage: {damage}")
            
            if network_ctx:
                is_multi, is_host, game_client = network_ctx
                if is_multi and game_client and game_client.is_connected():
                    etype = 'boss' if target.__class__.__name__ == 'Boss' else 'npc'
                    game_client.send_hit_event(etype, target_net_id, damage)
                else:
                    if hasattr(target, 'take_damage'): target.take_damage(damage)
            else:
                if hasattr(target, 'take_damage'): target.take_damage(damage)
            
            laser_obj.hit_list.append(target_net_id)
            
            if hasattr(target, 'apply_knockup'): target.apply_knockup(-10)
            elif hasattr(target, 'velocity_y'): target.velocity_y = -8