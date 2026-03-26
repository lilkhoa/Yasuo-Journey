import sdl2
import sdl2.ext
import time
import os
from combat.skill import Skill
from combat.utils import load_image_sequence

# --- LOGIC LOAD TÀI NGUYÊN ---
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
    def __init__(self, world, sprites_list, x, y, duration, damage_multiplier=1.0):
        self.entity = sdl2.ext.Entity(world)
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        self.entity.sprite = self.sprites[0]
        self.entity.sprite.position = x, y
        
        self.created_at = time.time()
        self.duration = duration
        self.active = True
        
        # Stats
        from settings import DAMAGE_SKILL_W
        self.damage = DAMAGE_SKILL_W * damage_multiplier
        self.damage_interval = 0.5
        self.hit_timers = {}
        
        # Animation State
        self.anim_state = 'spawn' 
        self.indices_spawn = [0, 1, 2]
        self.indices_loop  = [3, 4, 5, 6, 7, 8]
        self.indices_end   = [9, 10, 11, 12, 13]
        
        self.local_frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.08 

    @property
    def sprite(self):
        return self.entity.sprite
    
    def get_hitbox(self):
        # Hitbox nhỏ hơn hình ảnh một chút
        return sdl2.SDL_Rect(
            int(self.entity.sprite.x + 20), 
            int(self.entity.sprite.y + 20), 
            int(self.entity.sprite.size[0] - 40), 
            int(self.entity.sprite.size[1] - 20)
        )

    def delete(self):
        self.entity.delete()

class SkillW(Skill):
    def __init__(self, owner):
        super().__init__(owner, cooldown_time=0.1)

    def execute(self, world, factory, renderer, skill_sprites=None):
        print("Casting W: Fire Wall!")
        sprites_to_use = skill_sprites if skill_sprites else [factory.from_color(sdl2.ext.Color(200, 50, 0), size=(20, 100))]
        
        direction = 1 if self.owner.facing_right else -1
        spawn_x = self.owner.sprite.x + (70 * direction)
        spawn_y = self.owner.sprite.y - 15
        
        wall = WallObject(world, sprites_to_use, spawn_x, spawn_y, duration=4.0, damage_multiplier=self.damage_multiplier)
        return wall

# --- HÀM UPDATE LOGIC CHÍNH ---
def update_w_logic(wall_obj, enemies=None, projectiles=None, dt=0.016, network_ctx=None):
    """
    Xử lý logic cho Cột Lửa:
    1. Animation
    2. Gây dame lên Enemy (enemies)
    3. Chặn và hủy đạn (projectiles)
    """
    if not wall_obj.active: return
    
    # 1. Cập nhật Animation
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
                wall_obj.delete()
                return

        current_indices = []
        if wall_obj.anim_state == 'spawn': current_indices = wall_obj.indices_spawn
        elif wall_obj.anim_state == 'loop': current_indices = wall_obj.indices_loop
        elif wall_obj.anim_state == 'end': current_indices = wall_obj.indices_end
            
        if current_indices:
            safe_index = min(wall_obj.local_frame_index, len(current_indices) - 1)
            real_sprite_index = current_indices[safe_index]
            old_x, old_y = wall_obj.entity.sprite.position
            wall_obj.entity.sprite = wall_obj.sprites[real_sprite_index]
            wall_obj.entity.sprite.position = old_x, old_y

    # --- LOGIC VA CHẠM (Chỉ khi đang cháy - loop) ---
    if wall_obj.anim_state == 'loop':
        wall_rect = wall_obj.get_hitbox()
        current_time = time.time()

        # 2. Xử lý Đạn (Projectiles) -> Biến mất khi chạm tường
        if projectiles:
            for p in projectiles[:]:
                if not p.active: continue
                
                # Bỏ qua đạn của Player (nếu muốn bắn xuyên qua tường của mình)
                # Giả sử thuộc tính owner của đạn Player được gán là string hoặc object Player
                # Nếu không cần phân biệt thì bỏ qua dòng if này
                if hasattr(p, 'owner') and p.owner == 'player': 
                    continue
                
                if p.__class__.__name__ == 'BossKamehamehaProjectile':
                    continue

                # Lấy hitbox đạn
                px, py, pw, ph = p.get_bounds()
                p_rect = sdl2.SDL_Rect(int(px), int(py), int(pw), int(ph))
                
                if sdl2.SDL_HasIntersection(wall_rect, p_rect):
                    print("Fire Wall blocked a projectile!")
                    p.active = False  # Làm đạn biến mất ngay lập tức

        # 3. Xử lý Enemy (Gây dame nhưng KHÔNG chặn đường)
        if enemies:
            for enemy in enemies:
                # Lấy hitbox enemy
                if hasattr(enemy, 'get_bounds'):
                    ex, ey, ew, eh = enemy.get_bounds()
                    enemy_rect = sdl2.SDL_Rect(int(ex), int(ey), int(ew), int(eh))
                else:
                    enemy_rect = sdl2.SDL_Rect(int(enemy.sprite.x), int(enemy.sprite.y), 
                                               int(enemy.sprite.size[0]), int(enemy.sprite.size[1]))

                if sdl2.SDL_HasIntersection(wall_rect, enemy_rect):
                    # Gây dame theo thời gian (DoT)
                    target_net_id = getattr(enemy, 'net_id', id(enemy))
                    last_hit = wall_obj.hit_timers.get(target_net_id, 0)
                    
                    if current_time - last_hit >= wall_obj.damage_interval:
                        if network_ctx:
                            is_multi, is_host, game_client = network_ctx
                            if is_multi and game_client and game_client.is_connected():
                                etype = 'boss' if enemy.__class__.__name__ == 'Boss' else 'npc'
                                game_client.send_hit_event(etype, target_net_id, wall_obj.damage)
                                wall_obj.hit_timers[target_net_id] = current_time
                            else:
                                if hasattr(enemy, 'take_damage'):
                                    enemy.take_damage(wall_obj.damage)
                                    wall_obj.hit_timers[target_net_id] = current_time
                        else:
                            if hasattr(enemy, 'take_damage'):
                                enemy.take_damage(wall_obj.damage)
                                wall_obj.hit_timers[target_net_id] = current_time