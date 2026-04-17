import os
import sys
import sdl2
import sdl2.ext

# Cấu hình đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from entities.base_char import BaseChar
from combat.refactored_skill_q import SkillQ, load_tornado_assets
from combat.refactored_skill_w import SkillW, load_wall_assets
from combat.refactored_skill_e import SkillE
from combat.refactored_utils import load_grid_sprite_sheet, flip_sprites_horizontal
from settings import *

PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')
SKILL_ASSET_DIR = os.path.join(root_dir, 'assets', 'Skills')

class Yasuo(BaseChar):
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        super().__init__(world, factory, x, y, sound_manager, renderer_ptr)
        
        # Khởi tạo các bộ kỹ năng cụ thể của Yasuo
        self.skill_q = SkillQ(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)
        
        # Danh sách quản lý các object chiêu thức đang tồn tại trên map
        self.active_tornadoes = []
        self.active_walls = []
        
        # Gắn vào danh sách skills để HUD có thể lấy được dữ liệu cooldown/level
        self.skills = [
            self.skill_q,  # Index 0 - Q key
            self.skill_w,  # Index 1 - W key
            self.skill_e,  # Index 2 - E key
            None,          # Index 3 - R key (reserved)
            None           # Index 4 - A/S key (reserved)
        ]
        
        # Gọi hàm load toàn bộ đồ họa
        self._load_animations(factory)
        
        # Gán khung ảnh mặc định và tọa độ xuất phát
        if self.anims_right['idle']:
            self.entity.sprite = self.anims_right['idle'][0]
            self.entity.sprite.position = x, y

    def _load_animations(self, factory):
        """Chỉ Load sprite sheet của riêng Yasuo"""
        self.anims_right['idle'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Idle.png"), cols=6, rows=1)
        self.anims_right['run']  = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Run.png"), cols=8, rows=1)
        self.anims_right['walk'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Walk.png"), cols=8, rows=1)
        self.anims_right['attack_normal'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_1.png"), cols=6, rows=1) 
        self.anims_right['block'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"), cols=2, rows=1) 
        self.anims_right['q']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_2.png"), cols=4, rows=1)
        self.anims_right['w']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"), cols=2, rows=1)
        self.anims_right['e']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_3.png"), cols=3, rows=1)
        self.anims_right['jump'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Jump.png"), cols=12, rows=1)
        self.anims_right['dead'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Dead.png"), cols=3, rows=1)
        self.anims_right['hurt'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Hurt.png"), cols=2, rows=1)

        # Fallback an toàn nếu thiếu file
        if not self.anims_right['idle']: 
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(255,0,0), (40,60))]

        # Tự động tạo mảng animation quay trái
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        # Load Skill Assets (Hình ảnh Lốc và Tường gió)
        self.tornado_frames = load_tornado_assets(factory, SKILL_ASSET_DIR)
        self.wall_frames = load_wall_assets(factory, SKILL_ASSET_DIR)

    # ================= KHỞI TẠO KÍCH HOẠT KỸ NĂNG =================
    def start_q(self, direction=0):
        if self.stamina < SKILL_Q_COST or not self.cooldowns.is_ready("skill_q"): return
        if self.state in ['idle', 'jumping', 'run', 'walk']:
            self.stamina -= SKILL_Q_COST
            cd = self.get_skill_cooldown('q')
            self.cooldowns.start_cooldown("skill_q", cd)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_q'
            self.frame_index = 0
            if self.sound_manager:
                self.sound_manager.play_sound("player_q1")

    def start_w(self, direction=0):
        if self.stamina < SKILL_W_COST or not self.cooldowns.is_ready("skill_w"): return
        if self.state in ['idle', 'jumping']:
            self.stamina -= SKILL_W_COST
            cd = self.get_skill_cooldown('w')
            self.cooldowns.start_cooldown("skill_w", cd)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_w'
            self.frame_index = 0
            if self.sound_manager:
                self.sound_manager.play_sound("player_w1")

    def start_e(self, world, factory, renderer, direction):
        if self.stamina < SKILL_E_COST or not self.cooldowns.is_ready("skill_e"): return
        if direction and self.state != 'dashing_e':
            self.stamina -= SKILL_E_COST
            cd = self.get_skill_cooldown('e')
            self.cooldowns.start_cooldown("skill_e", cd)
            self.facing_right = (direction > 0)
            self.state = 'dashing_e'
            self.frame_index = 0
            
            # Cập nhật thông số lướt theo cấp độ kỹ năng trước khi cast
            self.skill_e.update_stats(self.skill_levels['e'])
            self.skill_e.damage_multiplier = SKILL_DAMAGE_GROWTH ** self.skill_levels['e']
            self.skill_e.cast(world, factory, renderer)
            if self.sound_manager:
                self.sound_manager.play_sound("player_e1")

    # ================= HOOKS KHI ANIMATION KẾT THÚC =================
    def on_cast_q_complete(self, world, factory, renderer):
        self.spawn_tornado(world, factory, renderer)
        super().on_cast_q_complete(world, factory, renderer)

    def on_cast_w_complete(self, world, factory, renderer):
        self.spawn_wall(world, factory, renderer)
        super().on_cast_w_complete(world, factory, renderer)
        
    def on_cast_e_complete(self, world, factory, renderer):
        # Tránh can thiệp nếu Dash chưa thực sự kết thúc (Dựa theo flag của skill_e)
        if not getattr(self.skill_e, 'is_dashing', False): 
            super().on_cast_e_complete(world, factory, renderer)

    # ================= SPAWN VẬT THỂ RA MAP =================
    def spawn_tornado(self, world, factory, renderer):
        if self.tornado_frames: 
            t = self.skill_q.cast(world, factory, renderer, skill_sprites=self.tornado_frames)
            if t: self.active_tornadoes.append(t)

    def spawn_wall(self, world, factory, renderer):
        if self.wall_frames: 
            w = self.skill_w.cast(world, factory, renderer, skill_sprites=self.wall_frames)
            if w: self.active_walls.append(w)

    # ================= VÒNG LẶP UPDATE KỸ NĂNG (POLYMORPHIC) =================
    def update_skills(self, dt, enemies, projectiles=None, network_ctx=None, camera=None, game_map=None, renderer=None):
        """Cập nhật logic cho các object như lốc hoặc tường gió đang tồn tại"""
        from combat.refactored_skill_q import update_q_logic
        from combat.refactored_skill_w import update_w_logic
        
        if projectiles is None:
            projectiles = []
            
        # Update Lốc (Q)
        for t in self.active_tornadoes[:]:
            update_q_logic(t, enemies, dt, network_ctx)
            if not t.active:
                t.delete()
                self.active_tornadoes.remove(t)
        
        # Update Tường gió (W)
        for w in self.active_walls[:]:
            # Truyền thẳng mảng projectiles từ tham số hàm vào, KHÔNG ghi đè nữa!
            update_w_logic(w, enemies, projectiles, dt, network_ctx)
            if not w.active:
                w.delete()
                self.active_walls.remove(w)
        
        # Update Dash (E) - Sẽ được vòng lặp game chính xử lý thông qua `skill_e.update_dash()`

    def render_skills(self, renderer, camera):
        """Vẽ các chiêu thức đang có trên bản đồ"""
        # Vẽ Lốc
        for t in self.active_tornadoes:
            sprite = t.sprite  # Lấy an toàn thông qua try-except đã viết
            if sprite and hasattr(sprite, 'surface'):
                surface = sprite.surface
                if surface:
                    texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
                    if texture:
                        w, h = surface.w, surface.h
                        dst_rect = sdl2.SDL_Rect(
                            int(sprite.x - camera.camera.x), 
                            int(sprite.y - camera.camera.y), 
                            w, h
                        )
                        sdl2.SDL_RenderCopy(renderer, texture, None, dst_rect)
                        sdl2.SDL_DestroyTexture(texture)
        
        # Vẽ Tường gió
        for w in self.active_walls:
            sprite = w.sprite # Lấy an toàn thông qua try-except đã viết
            if sprite and hasattr(sprite, 'surface'):
                surface = sprite.surface
                if surface:
                    texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
                    if texture:
                        w_dim, h_dim = surface.w, surface.h
                        dst_rect = sdl2.SDL_Rect(
                            int(sprite.x - camera.camera.x), 
                            int(sprite.y - camera.camera.y), 
                            w_dim, h_dim
                        )
                        sdl2.SDL_RenderCopy(renderer, texture, None, dst_rect)
                        sdl2.SDL_DestroyTexture(texture)