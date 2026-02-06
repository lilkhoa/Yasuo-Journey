import sdl2
import sdl2.ext
import os
from combat.skill import Skill
from combat.utils import load_grid_sprite_sheet

def load_tornado_assets(factory, asset_dir):
    filename = "mytornado.png" # Đảm bảo tên file đúng (mytornado.png)
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
        self.speed = 300
        self.max_dist = max_dist
        self.max_hits = max_hits
        self.hit_count = 0
        self.active = True
        self.damage_base = 100
        self.decay_rate = 0.8 
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.02

    @property
    def sprite(self):
        return self.entity.sprite

    def delete(self):
        self.entity.delete()

class SkillQ(Skill):
    def __init__(self, owner):
        super().__init__(owner, cooldown_time=4.0)
        
    def execute(self, world, factory, renderer, skill_sprites=None, skill_surface=None):
        print("Casting Q!")
        sprites_to_use = skill_sprites if skill_sprites else [factory.from_color(sdl2.ext.Color(0,255,255), size=(50,50))]
        
        direction = 1 if self.owner.facing_right else -1
        start_x = self.owner.sprite.x + (40 * direction)
        
        # --- CHỈNH SỬA Ở ĐÂY ---
        # Cộng thêm 30 pixel để dịch lốc xuống dưới
        start_y = self.owner.sprite.y + 15
        
        tornado = TornadoObject(world, sprites_to_use, start_x, start_y, 
                                direction, max_dist=600, max_hits=5)
        return tornado

def update_q_logic(tornado_obj, npcs, dt):
    if not tornado_obj.active: return
    
    # Animation
    if len(tornado_obj.sprites) > 1:
        tornado_obj.anim_timer += dt
        if tornado_obj.anim_timer >= tornado_obj.anim_speed:
            tornado_obj.anim_timer = 0
            tornado_obj.anim_frame = (tornado_obj.anim_frame + 1) % len(tornado_obj.sprites)
            old_x, old_y = tornado_obj.entity.sprite.position
            tornado_obj.entity.sprite = tornado_obj.sprites[tornado_obj.anim_frame]
            tornado_obj.entity.sprite.position = old_x, old_y

    # Di chuyển
    move_amt = int(tornado_obj.speed * dt * tornado_obj.direction)
    tornado_obj.sprite.x += move_amt
    
    dist = abs(tornado_obj.sprite.x - tornado_obj.start_x)
    if dist >= tornado_obj.max_dist:
        tornado_obj.active = False
        tornado_obj.delete()
        return

    # Hitbox
    width = tornado_obj.sprite.size[0]
    height = tornado_obj.sprite.size[1]
    t_rect = (tornado_obj.sprite.x, tornado_obj.sprite.y, width, height)
    
    for npc in npcs:
        n_rect = (npc.sprite.x, npc.sprite.y, npc.sprite.size[0], npc.sprite.size[1])
        if (t_rect[0] < n_rect[0] + n_rect[2] and t_rect[0] + t_rect[2] > n_rect[0] and
            t_rect[1] < n_rect[1] + n_rect[3] and t_rect[1] + t_rect[3] > n_rect[1]):
            
            hit_attr = "was_hit_by_q_id_" + str(id(tornado_obj))
            if not getattr(npc, hit_attr, False):
                setattr(npc, hit_attr, True)
                current_dmg = tornado_obj.damage_base * (tornado_obj.decay_rate ** tornado_obj.hit_count)
                print(f"Q Hit! Dmg: {current_dmg:.2f}")
                # Use knockup method which sets velocity_y
                if hasattr(npc, 'apply_knockup'):
                    npc.apply_knockup(-12) # Knockup force
                else:
                    npc.sprite.y -= 20 # Fallback 
                tornado_obj.hit_count += 1
                if tornado_obj.hit_count >= tornado_obj.max_hits:
                    tornado_obj.active = False
                    tornado_obj.delete()
                    break