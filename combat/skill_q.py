import sdl2
import sdl2.ext
import os
from combat.skill import Skill
from combat.utils import load_grid_sprite_sheet
from settings import DAMAGE_SKILL_Q

def load_tornado_assets(factory, asset_dir):
    filename = "mytornado.png"
    path = os.path.join(asset_dir, filename)
    sprites = load_grid_sprite_sheet(factory, path, cols=5, rows=12, target_size=(100, 120))
    return sprites

class TornadoObject:
    def __init__(self, world, sprites_list, x, y, direction, max_dist, max_hits):
        self.entity = sdl2.ext.Entity(world)
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        self.entity.sprite = self.sprites[0]
        self.entity.sprite.position = x, y
        
        self.start_x = x
        self.direction = direction 
        self.speed = 350
        self.max_dist = max_dist
        self.max_hits = max_hits
        self.hit_count = 0
        self.active = True
        self.damage_base = DAMAGE_SKILL_Q
        self.decay_rate = 0.8 
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.02
        
        # Danh sách ID các quái đã bị hit bởi lốc này (để tránh hit liên tục mỗi frame)
        # {enemy_id: cooldown_timer}
        self.hit_records = {} 
        self.hit_cooldown = 0.5 # Mỗi 0.5s mới hit lại 1 lần nếu lốc đi qua

    @property
    def sprite(self):
        return self.entity.sprite

    def delete(self):
        self.entity.delete()

class SkillQ(Skill):
    def __init__(self, owner):
        super().__init__(owner, cooldown_time=0.1)
        
    def execute(self, world, factory, renderer, skill_sprites=None, skill_surface=None):
        print("Casting Q!")
        sprites_to_use = skill_sprites if skill_sprites else [factory.from_color(sdl2.ext.Color(0,255,255), size=(50,50))]
        
        direction = 1 if self.owner.facing_right else -1
        start_x = self.owner.sprite.x + (40 * direction)
        start_y = self.owner.sprite.y + 15
        
        tornado = TornadoObject(world, sprites_to_use, start_x, start_y, 
                                direction, max_dist=700, max_hits=99) # Tăng max_hits để lốc xuyên táo
        return tornado

def update_q_logic(tornado_obj, enemies, dt):
    """
    enemies: List NPC/Boss/Minions
    """
    if not tornado_obj.active: return
    
    # 1. Animation
    if len(tornado_obj.sprites) > 1:
        tornado_obj.anim_timer += dt
        if tornado_obj.anim_timer >= tornado_obj.anim_speed:
            tornado_obj.anim_timer = 0
            tornado_obj.anim_frame = (tornado_obj.anim_frame + 1) % len(tornado_obj.sprites)
            old_x, old_y = tornado_obj.entity.sprite.position
            tornado_obj.entity.sprite = tornado_obj.sprites[tornado_obj.anim_frame]
            tornado_obj.entity.sprite.position = old_x, old_y

    # 2. Di chuyển
    move_amt = int(tornado_obj.speed * dt * tornado_obj.direction)
    tornado_obj.sprite.x += move_amt
    
    dist = abs(tornado_obj.sprite.x - tornado_obj.start_x)
    if dist >= tornado_obj.max_dist:
        tornado_obj.active = False
        tornado_obj.delete()
        return

    # 3. Hitbox Collision & Damage
    # Tạo Rect cho lốc xoáy (nhỏ hơn sprite chút cho chuẩn)
    t_width = tornado_obj.sprite.size[0]
    t_height = tornado_obj.sprite.size[1]
    tornado_rect = sdl2.SDL_Rect(int(tornado_obj.sprite.x + 20), 
                                 int(tornado_obj.sprite.y + 20), 
                                 int(t_width - 40), int(t_height - 20))
    
    # Update cooldown hit
    to_remove = []
    for eid in tornado_obj.hit_records:
        tornado_obj.hit_records[eid] -= dt
        if tornado_obj.hit_records[eid] <= 0:
            to_remove.append(eid)
    for eid in to_remove:
        del tornado_obj.hit_records[eid]

    for target in enemies:
        if not hasattr(target, 'is_alive') or not target.is_alive(): continue

        # Lấy hitbox target
        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
            target_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
        else:
            target_rect = sdl2.SDL_Rect(int(target.sprite.x), int(target.sprite.y), 
                                        int(target.sprite.size[0]), int(target.sprite.size[1]))

        # Check va chạm
        if sdl2.SDL_HasIntersection(tornado_rect, target_rect):
            target_id = id(target)
            
            # Nếu mục tiêu chưa bị hit hoặc đã hết cooldown hit
            if target_id not in tornado_obj.hit_records:
                
                # Tính damage (giảm dần theo số lần hit của lốc)
                current_dmg = tornado_obj.damage_base # Bạn có thể thêm decay_rate nếu muốn damage giảm dần
                
                print(f"Q Tornado Hit! Dmg: {current_dmg}")
                
                # --- QUAN TRỌNG: GÂY DAMAGE ---
                if hasattr(target, 'take_damage'):
                    target.take_damage(current_dmg)
                
                # Hiệu ứng hất tung (Knockup)
                if hasattr(target, 'apply_knockup'):
                    target.apply_knockup(-12)
                elif hasattr(target, 'velocity_y'): # Fallback
                    target.velocity_y = -10
                    
                # Ghi lại hit
                tornado_obj.hit_records[target_id] = tornado_obj.hit_cooldown
                tornado_obj.hit_count += 1