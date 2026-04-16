import sdl2
import sdl2.ext
import time
import os
from combat.refactored_skill import BaseSkill
from combat.refactored_utils import load_image_sequence

def load_wall_assets(factory, skill_asset_dir):
    w_folder = os.path.join(skill_asset_dir, "w")
    sprites = load_image_sequence(
        factory, 
        w_folder, 
        prefix="fire_column_medium_", 
        count=14, 
        target_size=(80, 160), 
        zero_pad=False 
    )
    return sprites

class WallObject:
    def __init__(self, world, sprites_list, x, y, duration, damage_multiplier=1.0, owner=None):
        self.entity = sdl2.ext.Entity(world)
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        self.entity.sprite = self.sprites[0]
        self.entity.sprite.position = x, y
        
        self.owner = owner # Lưu lại chủ nhân để không chặn đạn phe ta
        self.created_at = time.time()
        self.duration = duration
        self.active = True
        
        from settings import DAMAGE_SKILL_W
        self.damage = DAMAGE_SKILL_W * damage_multiplier
        self.damage_interval = 0.5
        self.hit_timers = {}
        
        self.anim_state = 'spawn' 
        self.indices_spawn = [0, 1, 2]
        self.indices_loop  = [3, 4, 5, 6, 7, 8]
        self.indices_end   = [9, 10, 11, 12, 13]
        
        self.local_frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.08 

    @property
    def sprite(self):
        try:
            return self.entity.sprite
        except KeyError:
            return None
    
    def get_hitbox(self):
        sprite = self.sprite
        if not sprite: return sdl2.SDL_Rect(0,0,0,0)
        return sdl2.SDL_Rect(
            int(sprite.x + 20), 
            int(sprite.y + 20), 
            int(sprite.size[0] - 40), 
            int(sprite.size[1] - 20)
        )

    def delete(self): 
        try:
            self.entity.delete()
        except:
            pass

# --- REFACTORED CLASS ---
class SkillW(BaseSkill):
    """Bản chất là WindWallSkill"""
    def __init__(self, owner):
        super().__init__(owner, name="Wind Wall", base_cooldown=0.1)

    def execute(self, world, factory, renderer, skill_sprites=None, **kwargs):
        sprites_to_use = skill_sprites if skill_sprites else [factory.from_color(sdl2.ext.Color(200, 50, 0), size=(20, 100))]
        
        direction = 1 if self.owner.facing_right else -1
        spawn_x = self.owner.sprite.x + (70 * direction)
        spawn_y = self.owner.sprite.y - 15
        
        # Truyền thêm tham số owner=self.owner vào
        wall = WallObject(world, sprites_to_use, spawn_x, spawn_y, duration=4.0, damage_multiplier=self.damage_multiplier, owner=self.owner)
        return wall

def update_w_logic(wall_obj, enemies=None, projectiles=None, dt=0.016, network_ctx=None):
    if not wall_obj.active: return
    
    # 1. Animation
    wall_obj.anim_timer += dt
    if wall_obj.anim_timer >= wall_obj.anim_speed:
        wall_obj.anim_timer = 0
        wall_obj.local_frame_index += 1
        
        if wall_obj.anim_state == 'spawn':
            if wall_obj.local_frame_index >= len(wall_obj.indices_spawn):
                wall_obj.anim_state = 'loop'
                wall_obj.local_frame_index = 0
        elif wall_obj.anim_state == 'loop':
            wall_obj.local_frame_index = wall_obj.local_frame_index % len(wall_obj.indices_loop)
            if time.time() - wall_obj.created_at > wall_obj.duration:
                wall_obj.anim_state = 'end'
                wall_obj.local_frame_index = 0
        elif wall_obj.anim_state == 'end':
            if wall_obj.local_frame_index >= len(wall_obj.indices_end):
                wall_obj.active = False
                return

        current_indices = []
        if wall_obj.anim_state == 'spawn': current_indices = wall_obj.indices_spawn
        elif wall_obj.anim_state == 'loop': current_indices = wall_obj.indices_loop
        elif wall_obj.anim_state == 'end': current_indices = wall_obj.indices_end
            
        if current_indices:
            safe_index = min(wall_obj.local_frame_index, len(current_indices) - 1)
            real_sprite_index = current_indices[safe_index]
            sprite = wall_obj.sprite
            if sprite:
                old_x, old_y = sprite.position
                wall_obj.entity.sprite = wall_obj.sprites[real_sprite_index]
                wall_obj.entity.sprite.position = old_x, old_y

    # 2. Xử lý va chạm (Tháo bỏ if state == 'loop' để tường đỡ đạn ngay từ frame đầu tiên)
    wall_rect = wall_obj.get_hitbox()
    current_time = time.time()

    # --- LOGIC CHẶN ĐẠN ---
    if projectiles:
        for p in projectiles[:]:
            if not getattr(p, 'active', True): continue
            
            # Check thông minh: Bỏ qua đạn của phe ta
            if hasattr(p, 'owner'):
                if p.owner == wall_obj.owner: continue
                owner_class = getattr(p.owner, '__class__', None)
                if owner_class and owner_class.__name__ in ['Yasuo', 'LeafRanger']:
                    continue
            
            if p.__class__.__name__ == 'BossKamehamehaProjectile': continue

            # [QUAN TRỌNG] Lấy Hitbox đạn (Ưu tiên sprite.x vì p.x có thể bị lỗi "tọa độ ma")
            if hasattr(p, 'get_hitbox'):
                p_rect = p.get_hitbox()
            elif hasattr(p, 'get_bounds'):
                bounds = p.get_bounds()
                p_rect = sdl2.SDL_Rect(int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]))
            elif hasattr(p, 'sprite') and p.sprite:
                p_rect = sdl2.SDL_Rect(int(p.sprite.x), int(p.sprite.y), int(p.sprite.size[0]), int(p.sprite.size[1]))
            else:
                p_rect = sdl2.SDL_Rect(int(getattr(p, 'x', 0)), int(getattr(p, 'y', 0)), int(getattr(p, 'width', 20)), int(getattr(p, 'height', 20)))
            
            if sdl2.SDL_HasIntersection(wall_rect, p_rect):
                p.active = False 
                
                # Dịch chuyển đạn ra khỏi map hoàn toàn để game.py bị mù
                if hasattr(p, 'x'): p.x = -9999
                if hasattr(p, 'y'): p.y = -9999
                if hasattr(p, 'sprite') and p.sprite:
                    p.sprite.x = -9999
                    p.sprite.y = -9999
                
                # Nổ đạn và loại bỏ khỏi hệ thống
                if hasattr(p, 'on_hit'): p.on_hit()
                if p in projectiles: projectiles.remove(p)

    # --- LOGIC GÂY DAMAGE LÊN QUÁI ---
    if enemies:
        for enemy in enemies:
            if hasattr(enemy, 'get_bounds'):
                ex, ey, ew, eh = enemy.get_bounds()
                enemy_rect = sdl2.SDL_Rect(int(ex), int(ey), int(ew), int(eh))
            else:
                if hasattr(enemy, 'sprite') and enemy.sprite:
                    enemy_rect = sdl2.SDL_Rect(int(enemy.sprite.x), int(enemy.sprite.y), int(enemy.sprite.size[0]), int(enemy.sprite.size[1]))
                else: continue

            if sdl2.SDL_HasIntersection(wall_rect, enemy_rect):
                target_net_id = getattr(enemy, 'net_id', id(enemy))
                last_hit = wall_obj.hit_timers.get(target_net_id, 0)
                
                if current_time - last_hit >= wall_obj.damage_interval:
                    if network_ctx:
                        is_multi, is_host, game_client = network_ctx
                        if is_multi and game_client and game_client.is_connected():
                            etype = 'boss' if enemy.__class__.__name__ == 'Boss' else 'npc'
                            game_client.send_hit_event(etype, target_net_id, wall_obj.damage)
                        else:
                            if hasattr(enemy, 'take_damage'): enemy.take_damage(wall_obj.damage)
                    else:
                        if hasattr(enemy, 'take_damage'): enemy.take_damage(wall_obj.damage)
                    wall_obj.hit_timers[target_net_id] = current_time