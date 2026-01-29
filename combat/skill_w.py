import sdl2
import sdl2.ext
import time
import os
from combat.skill import Skill
from combat.utils import load_image_sequence

# --- LOGIC LOAD TÀI NGUYÊN ---
def load_wall_assets(factory, skill_asset_dir):
    w_folder = os.path.join(skill_asset_dir, "w")
    # Load toàn bộ 14 ảnh (fire_column_medium_1 -> 14)
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
    def __init__(self, world, sprites_list, x, y, duration):
        self.entity = sdl2.ext.Entity(world)
        self.sprites = sprites_list if isinstance(sprites_list, list) else [sprites_list]
        self.entity.sprite = self.sprites[0]
        self.entity.sprite.position = x, y
        
        self.created_at = time.time()
        self.duration = duration
        self.active = True
        
        # --- CẤU HÌNH ANIMATION 3 GIAI ĐOẠN ---
        # Python list index bắt đầu từ 0
        # Frame 1-3  => Index 0-2
        # Frame 4-9  => Index 3-8
        # Frame 10-14 => Index 9-13
        
        self.anim_state = 'spawn' # Các trạng thái: 'spawn', 'loop', 'end'
        self.indices_spawn = [0, 1, 2]
        self.indices_loop  = [3, 4, 5, 6, 7, 8]
        self.indices_end   = [9, 10, 11, 12, 13]
        
        # Biến đếm frame cục bộ cho từng giai đoạn
        self.local_frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.08 

    @property
    def sprite(self):
        return self.entity.sprite

    def delete(self):
        self.entity.delete()

class SkillW(Skill):
    def __init__(self, owner):
        super().__init__(owner, cooldown_time=15.0)

    def execute(self, world, factory, renderer, skill_sprites=None):
        print("Casting W: Fire Column (3 Stages)!")
        sprites_to_use = skill_sprites if skill_sprites else [factory.from_color(sdl2.ext.Color(200, 50, 0), size=(20, 100))]
        
        direction = 1 if self.owner.facing_right else -1
        spawn_x = self.owner.sprite.x + (70 * direction)
        # Dịch xuống 30px so với nhân vật
        spawn_y = self.owner.sprite.y - 15
        
        wall = WallObject(world, sprites_to_use, spawn_x, spawn_y, duration=4.0)
        return wall

def update_w_logic(wall_obj):
    if not wall_obj.active: return
    
    # Cập nhật thời gian animation
    wall_obj.anim_timer += 0.016 # Giả lập dt
    
    # Chỉ chuyển frame khi đủ thời gian
    if wall_obj.anim_timer >= wall_obj.anim_speed:
        wall_obj.anim_timer = 0
        wall_obj.local_frame_index += 1
        
        # --- LOGIC CHUYỂN ĐỔI TRẠNG THÁI (STATE MACHINE) ---
        
        # 1. Giai đoạn xuất hiện (1-3)
        if wall_obj.anim_state == 'spawn':
            # Nếu chạy hết ảnh spawn -> Chuyển sang loop
            if wall_obj.local_frame_index >= len(wall_obj.indices_spawn):
                wall_obj.anim_state = 'loop'
                wall_obj.local_frame_index = 0 # Reset frame cho giai đoạn mới
        
        # 2. Giai đoạn duy trì (4-9)
        elif wall_obj.anim_state == 'loop':
            # Lặp vòng tròn: Nếu hết ảnh loop thì quay về đầu list loop
            wall_obj.local_frame_index = wall_obj.local_frame_index % len(wall_obj.indices_loop)
            
            # Kiểm tra thời gian: Nếu hết giờ -> Chuyển sang end
            if time.time() - wall_obj.created_at > wall_obj.duration:
                print("Hết thời gian -> Chuyển sang tắt lửa (10-14)")
                wall_obj.anim_state = 'end'
                wall_obj.local_frame_index = 0
        
        # 3. Giai đoạn kết thúc (10-14)
        elif wall_obj.anim_state == 'end':
            # Nếu chạy hết ảnh end -> Xóa object
            if wall_obj.local_frame_index >= len(wall_obj.indices_end):
                wall_obj.active = False
                wall_obj.delete()
                print("Cột lửa biến mất hoàn toàn.")
                return

        # --- CẬP NHẬT HÌNH ẢNH ---
        # Xác định index thực tế trong list sprites tổng (14 ảnh)
        current_indices = []
        if wall_obj.anim_state == 'spawn':
            current_indices = wall_obj.indices_spawn
        elif wall_obj.anim_state == 'loop':
            current_indices = wall_obj.indices_loop
        elif wall_obj.anim_state == 'end':
            current_indices = wall_obj.indices_end
            
        # Lấy frame thực tế
        if current_indices: # Kiểm tra an toàn
            # Đảm bảo index không vượt quá giới hạn (quan trọng cho 'spawn' và 'end')
            safe_index = min(wall_obj.local_frame_index, len(current_indices) - 1)
            real_sprite_index = current_indices[safe_index]
            
            # Gán sprite mới
            old_x, old_y = wall_obj.entity.sprite.position
            wall_obj.entity.sprite = wall_obj.sprites[real_sprite_index]
            wall_obj.entity.sprite.position = old_x, old_y