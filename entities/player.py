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
from settings import *
from combat.cooldown import CooldownManager
from combat.damage import DamageSystem

class Player:
    def __init__(self, world, factory, x, y):
        # --- 1. LOAD ANIMATION ---
        self.anims_right = {}
        self.anims_right['idle'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Idle.png"), cols=6, rows=1)
        self.anims_right['run']  = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Run.png"), cols=8, rows=1)
        self.anims_right['walk'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Walk.png"), cols=8, rows=1)
        self.anims_right['walk'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Walk.png"), cols=8, rows=1)
        self.anims_right['attack_normal'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_1.png"), cols=6, rows=1) 
        self.anims_right['block'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"), cols=2, rows=1) 
        self.anims_right['q']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_2.png"), cols=4, rows=1)
        self.anims_right['w']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"), cols=2, rows=1) # W cũng dùng Shield tạm hoặc khác
        self.anims_right['e']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_3.png"), cols=3, rows=1)
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
        self.gravity = GRAVITY
        self.jump_force = -PLAYER_JUMP_POWER
        self.is_jumping = False

        # --- [MỚI] CHỈ SỐ PLAYER (Stamina System) ---
        self.max_hp = PLAYER_MAX_HEALTH
        self.hp = self.max_hp
        self.max_stamina = PLAYER_MAX_STAMINA
        self.stamina = self.max_stamina # Tên biến đúng ý user
        
        self.is_running = False
        self.exhausted = False
        self.is_blocking = False 
        self.invincible = False # Cho Star Item
        self.invincible_timer = 0
        
        self.cooldowns = CooldownManager()

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

    def handle_movement(self, keys):
        """Xử lý input di chuyển liên tục (Walk/Run)"""
        if self.is_blocking: 
            # Nếu đang block thì không đi được, nhưng nếu nhả S thì main.py sẽ set blocking False
            # Ở đây ta check: nếu block -> Idle
            if self.state not in ['idle', 'casting_q', 'casting_w', 'dashing_e', 'attacking']:
                self.state = 'idle'
            return

        # Chỉ xử lý state nếu không đang làm hành động ưu tiên (Dash, Cast)
        # Jump và Attack có thể vừa đi vừa làm (Attack thì tùy)
        # Ở đây ta ưu tiên logic đi bộ/chạy đơn giản
        
        if self.state in ['casting_q', 'casting_w', 'dashing_e', 'attacking', 'dead']:
            return

        # Check Run
        is_running_input = keys[sdl2.SDL_SCANCODE_LSHIFT] or keys[sdl2.SDL_SCANCODE_RSHIFT]
        
        has_input = False
        if keys[sdl2.SDL_SCANCODE_RIGHT]:
            self.facing_right = True
            has_input = True
        elif keys[sdl2.SDL_SCANCODE_LEFT]:
            self.facing_right = False
            has_input = True
            
        if has_input:
            if is_running_input and self.try_run():
                self.state = 'run'
            else:
                self.state = 'walk'
                self.is_running = False
        else:
            if not self.is_jumping:
                self.state = 'idle'
            self.is_running = False

    def update(self, dt, world, factory, renderer, active_list_q, active_list_w, game_map=None):
        # --- [MỚI] CẬP NHẬT VẬT LÝ & STATS VỚI MAP ---
        
        # 1. Hồi phục & Cooldown
        self.regenerate()
        self.cooldowns.update(1)

        # 2. Xử lý di chuyển ngang (X) & Collision X
        # Tốc độ di chuyển
        dx = 0
        if self.state == 'run': dx = PLAYER_SPEED_RUN * dt
        elif self.state == 'walk': dx = PLAYER_SPEED_WALK * dt
        
        if dx > 0:
            if not self.facing_right: dx = -dx
            
            # Dự đoán vị trí X tiếp theo
            next_x = self.entity.sprite.x + dx
            
            # Check Collision X (Tạm bỏ theo yêu cầu User)
            # if self.check_map_collision(next_x, self.entity.sprite.y, game_map):
            #     dx = 0 # Va vào tường -> Dừng
            
            self.entity.sprite.x += int(dx)

        # 3. Xử lý trọng lực (Y) & Simple Ground Check
        self.vel_y += self.gravity
        if self.vel_y > MAX_FALL_SPEED: self.vel_y = MAX_FALL_SPEED
        
        self.entity.sprite.y += int(self.vel_y)
        
        # Check Collision Y (Simple Ground)
        # User yêu cầu "chưa cần collision", chỉ cần đi được
        if self.entity.sprite.y >= GROUND_Y:
            self.entity.sprite.y = GROUND_Y
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
        # 1. Ưu tiên cao nhất: Đang dùng Skill hoặc Đánh thường
        if self.state == 'casting_q':
            current_frames = current_anims['q']
        elif self.state == 'casting_w':
            current_frames = current_anims['w']
        elif self.state == 'dashing_e':
            current_frames = current_anims['e']
        elif self.state == 'attacking': 
            current_frames = current_anims.get('attack_normal', current_anims['idle'])
        
        # 2. Ưu tiên nhì: Thủ (Block)
        # Lưu ý: Phải giữ phím S mới kích hoạt
        elif self.is_blocking:
            current_frames = current_anims.get('block', current_anims['idle'])


            
        # 3. Ưu tiên ba: Nhảy
        elif self.is_jumping:
            current_frames = current_anims.get('jump', current_anims['idle'])
        
        # 3. Ưu tiên ba: Chạy / Đi bộ
        elif self.state == 'run':
             current_frames = current_anims.get('run', current_anims['idle'])
        elif self.state == 'walk':
             current_frames = current_anims.get('walk', current_anims['idle'])

        # 4. Mặc định: Idle
        else:
            current_frames = current_anims['idle']
        
        if not current_frames: return

        # Tốc độ Animation: Nhanh hơn nếu đang đánh thường (để cast nhanh như Attack_3)
        effective_anim_speed = 0.05 if self.state == 'attacking' else self.anim_speed

        # Chuyển frame
        if self.anim_timer >= effective_anim_speed:
            self.anim_timer = 0
            self.frame_index += 1
            
            if self.frame_index >= len(current_frames):
                if self.state == 'casting_q':
                    self.spawn_tornado(world, factory, renderer, active_list_q)
                    self.state = 'idle'
                elif self.state == 'casting_w':
                    self.spawn_wall(world, factory, renderer, active_list_w)
                    self.state = 'idle'
                elif self.state == 'dashing_e':
                     if not self.skill_e.is_dashing: self.state = 'idle'
                elif self.state == 'attacking':
                    self.state = 'idle' # Kết thúc đánh thường
                
                self.frame_index = 0
        
        # Render Sprite
        idx = self.frame_index % len(current_frames)
        
        # Lưu vị trí cũ trước khi thay sprite
        old_x, old_y = self.entity.sprite.position
        self.entity.sprite = current_frames[idx]
        self.entity.sprite.position = old_x, old_y

    def start_q(self, direction=0):
        # Kích hoạt Q (Tốn Stamina)
        if self.stamina < SKILL_Q_COST: return
        
        # Cho phép dùng Q kể cả khi đang nhảy, miễn là không đang dùng skill khác
        if self.state in ['idle', 'jumping', 'run', 'walk'] or (self.is_jumping and self.state == 'idle'):
            self.stamina -= SKILL_Q_COST
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            
            self.state = 'casting_q'
            self.frame_index = 0
            self.anim_timer = 0
            
    def start_w(self, direction=0):
        if self.stamina < SKILL_W_COST: return
        if self.state == 'idle' or (self.is_jumping and self.state == 'idle'):
            self.stamina -= SKILL_W_COST
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            
            self.state = 'casting_w'
            self.frame_index = 0
            self.anim_timer = 0
            
    def start_e(self, world, factory, renderer, direction):
        if self.stamina < SKILL_E_COST: return
        if direction == 0: return
        if self.state != 'dashing_e':
            self.stamina -= SKILL_E_COST
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

    def regenerate(self):
        """Hồi phục stats theo thời gian"""
        # 1. Hồi Máu
        if self.hp < self.max_hp:
            self.hp = min(self.hp + PLAYER_HEALTH_REGEN, self.max_hp)
            
        # 2. Hồi Stamina - CHỈ KHI ĐI BỘ (WALK)
        if self.state == 'walk':
            if self.stamina < self.max_stamina:
                self.stamina = min(self.stamina + PLAYER_STAMINA_REGEN_WALK, self.max_stamina)
            
        # UX: Thoát trạng thái kiệt sức
        if self.exhausted and self.stamina > self.max_stamina * 0.3:
            self.exhausted = False

    def try_run(self):
        """Chạy tốn Stamina"""
        if self.exhausted: return False
        
        if self.stamina >= PLAYER_RUN_COST:
            self.stamina -= PLAYER_RUN_COST
            self.is_running = True
            return True
        else:
            self.is_running = False
            self.exhausted = True
            return False

    def on_hit_enemy(self, damage_dealt):
        """Gọi khi đánh trúng quái"""
        self.stamina = min(self.stamina + Reward_Hit_Stamina, self.max_stamina)
        
        # Hút máu toàn phần
        heal = damage_dealt * (PLAYER_LIFESTEAL / 100.0)
        self.hp = min(self.hp + heal, self.max_hp)
        print(f"Hit! +Stamina & Lifesteal (+{heal} HP)")

    def on_kill_enemy(self):
        """Gọi khi giết quái"""
        self.stamina = min(self.stamina + Reward_Kill_Stamina, self.max_stamina)
        print("Kill! Large Stamina reward.")

    # --- CÁC HÀM COMBAT MỚI ---
    def attack(self):
        """Đánh thường (A) - Không tốn Energy"""
        if self.state in ['idle', 'run', 'walk'] and not self.is_blocking:
            if self.cooldowns.is_ready("attack"):
                self.state = 'attacking'
                self.frame_index = 0
                self.anim_timer = 0
                self.cooldowns.start_cooldown("attack", ATTACK_COOLDOWN)

    def set_blocking(self, blocking):
        if blocking:
             if self.stamina > 0:
                 self.is_blocking = True
                 if self.is_running: 
                     self.is_running = False
                     self.state = 'idle'
             else:
                 self.is_blocking = False
        else:
            self.is_blocking = False

    def take_damage(self, amount):
        if self.invincible:
            print("Invincible! Damage ignored.")
            return

        final_damage = int(amount)
        
        # Block Logic
        if self.is_blocking:
            cost = BLOCK_STAMINA_COST_PER_HIT
            if self.stamina >= cost: 
                self.stamina -= cost
                final_damage = int(amount * (1.0 - BLOCK_DAMAGE_REDUCTION))
                print(f"Blocked! Damage {amount}->{final_damage}. Stamina left: {int(self.stamina)}")
            else:
                print("Guard Broken! Not enough stamina.")
                self.is_blocking = False
        
        self.hp -= final_damage
        print(f"Player took {final_damage} damage! HP: {int(self.hp)}/{self.max_hp}")
        if self.hp <= 0:
            self.die()
            
    def activate_star_skill(self, duration=5.0):
        """Kích hoạt bất tử (Star Item)"""
        self.invincible = True
        # Logic timer sẽ cần update trong loop, tạm thời set flag
        print("STAR SKILL ACTIVE: Invincible!")

    def die(self):
        """Xử lý khi chết"""
        print("Player Died!")
        self.state = 'dead'
        # Thực hiện logic reset game hoặc game over ở đây

    def check_map_collision(self, x, y, game_map, check_bottom=False):
        """Kiểm tra va chạm với map tiles"""
        if not game_map: return False
        
        # Hitbox offsets (tùy chỉnh cho khớp sprite)
        # Sprite 128x128 (nhưng nhân vật thực tế căn giữa)
        # Giả sử hitbox rộng 40, cao 80, offset x+44, y+48
        hitbox_w = 40
        hitbox_h = 80
        off_x = 44
        off_y = 48
         
        check_x = x + off_x + (hitbox_w / 2) # Center X
        check_y = y + off_y
        
        if check_bottom:
             check_y += hitbox_h # Check chân
        
        # Convert to Grid Coords
        # TILE_SIZE = 96
        col = int(check_x // TILE_SIZE)
        row = int(check_y // TILE_SIZE)
        
        # Check bounds
        if row < 0 or row >= len(game_map.map_data): return False
        if col < 0 or col >= len(game_map.map_data[0]): return False
        
        tile_char = game_map.map_data[row][col]
        
        # Coi những tile này là solid
        SOLID_TILES = ['(', '-', ')', '[', '=', ']', '0', '1', '2', '3', '8', '6', '7']
        if tile_char in SOLID_TILES:
            return True
            
        return False