import sdl2
import sdl2.ext
import os
import sys

# Giữ nguyên logic đường dẫn cũ của bạn
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')
SKILL_ASSET_DIR = os.path.join(root_dir, 'assets', 'Skills')

from combat.skill_q import SkillQ, load_tornado_assets
from combat.skill_w import SkillW, load_wall_assets
from combat.skill_e import SkillE
from combat.utils import load_grid_sprite_sheet, flip_sprites_horizontal

class Player:
    def __init__(self, world, factory, x, y):
        # --- 1. LOAD ANIMATION ---
        self.anims_right = {}
        self.anims_right['idle'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Idle.png"), cols=6, rows=1)
        self.anims_right['q']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_2.png"), cols=4, rows=1)
        self.anims_right['w']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"), cols=2, rows=1)
        self.anims_right['e']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_3.png"), cols=3, rows=1)
        
        # [MỚI] Load Jump Animation (1 hàng 12 cột)
        self.anims_right['jump'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Jump.png"), cols=12, rows=1)

        # Fallback nếu không load được
        if not self.anims_right['idle']: 
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(255,0,0), (40,60))]

        # --- 2. TẠO ANIMATION TRÁI (FLIP) ---
        self.anims_left = {}
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        # Load Skill Assets
        self.tornado_frames = load_tornado_assets(factory, SKILL_ASSET_DIR)
        self.wall_frames = load_wall_assets(factory, SKILL_ASSET_DIR)

        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = self.anims_right['idle'][0]
        self.entity.sprite.position = x, y
        
        self.facing_right = True
        self.move_speed = 300 # Tăng tốc độ chạy chút cho mượt
        
        # --- [MỚI] BIẾN VẬT LÝ NHẢY ---
        self.ground_y = y   # Ghi nhớ mặt đất (tạm thời)
        self.vel_y = 0      # Vận tốc trục dọc
        self.gravity = 0.8  # Trọng lực
        self.jump_force = -16 # Lực nhảy (số âm là bay lên)
        self.is_jumping = False

        self.state = 'idle'
        self.frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.10 # Animation nhanh hơn chút
        
        self.skill_q = SkillQ(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)

    @property
    def sprite(self):
        return self.entity.sprite

    def jump(self):
        """Hàm kích hoạt nhảy"""
        # Chỉ nhảy được khi đang ở dưới đất
        if not self.is_jumping:
            self.vel_y = self.jump_force
            self.is_jumping = True
            # Không thay đổi self.state thành 'jump' ở đây
            # để tránh xung đột với việc đang cast skill

    def update(self, dt, world, factory, renderer, active_list_q, active_list_w):
        # --- [MỚI] CẬP NHẬT VẬT LÝ ---
        # Áp dụng trọng lực
        self.vel_y += self.gravity
        self.entity.sprite.y += int(self.vel_y)

        # Kiểm tra va chạm mặt đất
        if self.entity.sprite.y >= self.ground_y:
            self.entity.sprite.y = self.ground_y
            self.vel_y = 0
            self.is_jumping = False
        else:
            self.is_jumping = True

        # --- ANIMATION TIMER ---
        self.anim_timer += dt
        
        # Chọn bộ hướng (Trái/Phải)
        current_anims = self.anims_right if self.facing_right else self.anims_left
        current_frames = []

        # --- [MỚI] LOGIC ƯU TIÊN ANIMATION ---
        # 1. Ưu tiên cao nhất: Đang dùng Skill (Q, W, E)
        if self.state == 'casting_q':
            current_frames = current_anims['q']
        elif self.state == 'casting_w':
            current_frames = current_anims['w']
        elif self.state == 'dashing_e':
            current_frames = current_anims['e']
        
        # 2. Ưu tiên nhì: Đang nhảy (Chỉ hiện khi KHÔNG dùng skill)
        elif self.is_jumping:
            current_frames = current_anims.get('jump', current_anims['idle'])
        
        # 3. Mặc định: Idle
        else:
            current_frames = current_anims['idle']
        
        if not current_frames: return

        # Chuyển frame
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.frame_index += 1
            
            # Xử lý khi hết vòng animation skill
            if self.frame_index >= len(current_frames):
                if self.state == 'casting_q':
                    self.spawn_tornado(world, factory, renderer, active_list_q)
                    self.state = 'idle' # Quay về idle (nhưng physics vẫn nhảy nếu chưa chạm đất)
                elif self.state == 'casting_w':
                    self.spawn_wall(world, factory, renderer, active_list_w)
                    self.state = 'idle'
                elif self.state == 'dashing_e':
                     if not self.skill_e.is_dashing: self.state = 'idle'
                
                # Nếu đang nhảy thì lặp lại frame nhảy (hoặc dừng ở frame cuối tùy ý)
                self.frame_index = 0
        
        # Render Sprite
        idx = self.frame_index % len(current_frames)
        
        # Lưu vị trí cũ trước khi thay sprite
        old_x, old_y = self.entity.sprite.position
        self.entity.sprite = current_frames[idx]
        self.entity.sprite.position = old_x, old_y

    def start_q(self, direction=0):
        # Cho phép dùng Q kể cả khi đang nhảy, miễn là không đang dùng skill khác
        if self.state in ['idle', 'jumping'] or (self.is_jumping and self.state == 'idle'):
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            
            self.state = 'casting_q'
            self.frame_index = 0
            self.anim_timer = 0
            
    def start_w(self, direction=0):
        if self.state == 'idle' or (self.is_jumping and self.state == 'idle'):
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            
            self.state = 'casting_w'
            self.frame_index = 0
            self.anim_timer = 0
            
    def start_e(self, world, factory, renderer, direction):
        if direction == 0: return
        if self.state != 'dashing_e':
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            self.state = 'dashing_e'
            self.frame_index = 0
            self.skill_e.cast(world, factory, renderer)

    def spawn_tornado(self, world, factory, renderer, active_list):
        if self.tornado_frames:
            # Lốc bay ra từ vị trí hiện tại (kể cả trên trời)
            t = self.skill_q.cast(world, factory, renderer, skill_sprites=self.tornado_frames)
            if t: active_list.append(t)

    def spawn_wall(self, world, factory, renderer, active_list):
        if self.wall_frames:
            w = self.skill_w.cast(world, factory, renderer, skill_sprites=self.wall_frames)
            if w: active_list.append(w)