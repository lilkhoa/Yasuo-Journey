import sdl2
import sdl2.ext
import sdl2.sdlmixer
import os
import sys
import ctypes
import copy

# [CHECK] Import OpenCV
try:
    import cv2
    import numpy as np
except ImportError:
    print("Warning: 'opencv-python' or 'numpy' not found. Mastery Emote video will not play.")
    cv2 = None

# --- CẤU HÌNH ĐƯỜNG DẪN CHUẨN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir) # .../A3_Yasuo

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
from items.item import ItemType, ItemCategory, ITEM_REGISTRY

# --- CLASS XỬ LÝ MASTERY EMOTE ---
class MasteryEmote:
    def __init__(self, renderer):
        self.renderer = renderer
        self.active = False
        self.cap = None
        self.sound_chunk = None
        self.frame_texture = None
        
        self.video_path = os.path.join(PLAYER_ASSET_DIR, "videoplayback.mp4")
        self.audio_path = os.path.join(PLAYER_ASSET_DIR, "videoplayback.mp3")
        
        # [AUDIO] Load âm thanh Mastery
        if os.path.exists(self.audio_path):
            try:
                # Load file âm thanh
                self.sound_chunk = sdl2.sdlmixer.Mix_LoadWAV(self.audio_path.encode('utf-8'))
                if not self.sound_chunk:
                    print(f"[Mastery] Failed to load audio: {self.audio_path}")
                else:
                    print(f"[Mastery] Audio loaded successfully.")
            except Exception as e:
                print(f"[Mastery] Audio load error: {e}")
        else:
            print(f"[Mastery] Audio file missing: {self.audio_path}")
        
        # Kích thước resize
        self.target_width = 125
        self.target_height = 125

    def play(self):
        if not cv2: return
        if self.cap: self.cap.release()
        
        if os.path.exists(self.video_path):
            self.cap = cv2.VideoCapture(self.video_path)
            self.active = True
            
            # [AUDIO] Phát âm thanh
            if self.sound_chunk:
                sdl2.sdlmixer.Mix_PlayChannel(-1, self.sound_chunk, 0)
        else:
            print(f"[Mastery] Missing video: {self.video_path}")

    def update(self):
        if not self.active or not self.cap: return

        # 1. Đọc frame
        ret, frame = self.cap.read()
        if not ret:
            self.stop()
            return

        # 2. Resize về 133x100
        frame = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_NEAREST)

        # 3. [NEW] TẠO MASK CHO DẢI MÀU (Range Removal)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        lower_green = np.array([0, 150, 0])
        upper_green = np.array([40, 255, 40]) 
        
        mask = cv2.inRange(rgb_frame, lower_green, upper_green)

        # 4. [NEW] Chuyển sang hệ màu RGBA (Thêm kênh Alpha)
        frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        
        # Gán Alpha = 0 (Trong suốt) tại những vị trí Mask nhận diện là màu xanh
        frame_rgba[mask > 0] = [0, 0, 0, 0]

        # 5. Xoay/Lật cho khớp SDL Surface
        frame_rgba = np.rot90(frame_rgba, k=-1) 
        frame_rgba = np.flip(frame_rgba, axis=1)

        h, w, c = frame_rgba.shape 
        
        # 6. Tạo Surface 32-bit (Hỗ trợ Alpha)
        surface = sdl2.SDL_CreateRGBSurfaceFrom(
            frame_rgba.ctypes.data_as(ctypes.c_void_p),
            w, h, 32, 4 * w,
            0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000 # Mask cho R, G, B, A
        )
        
        # 7. Tạo Texture
        if self.frame_texture:
            sdl2.SDL_DestroyTexture(self.frame_texture)
        self.frame_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        sdl2.SDL_FreeSurface(surface)

    def render(self, x, y, camera_x, camera_y):
        if not self.active or not self.frame_texture: return

        # Căn giữa trên đầu
        offset_x = 64 - (self.target_width // 2)
        dst_rect = sdl2.SDL_Rect(
            int(x - camera_x + offset_x-30), 
            int(y - camera_y - self.target_height + 70),
            self.target_width+60,
            self.target_height
        )
        # Cần bật Blend Mode để kênh Alpha hoạt động (hiển thị trong suốt)
        sdl2.SDL_SetTextureBlendMode(self.frame_texture, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_RenderCopy(self.renderer, self.frame_texture, None, dst_rect)

    def stop(self):
        self.active = False
        if self.cap: self.cap.release(); self.cap = None
        if self.frame_texture: sdl2.SDL_DestroyTexture(self.frame_texture); self.frame_texture = None

    def cleanup(self):
        self.stop()
        if self.sound_chunk: sdl2.sdlmixer.Mix_FreeChunk(self.sound_chunk)

# --- PLAYER CLASS ---
class Player:
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        # --- 0. SOUND MANAGER ---
        self.sound_manager = sound_manager
        
        # --- 1. LOAD ANIMATION ---
        self.anims_right = {}
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

        # Fallback
        if not self.anims_right['idle']: 
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(255,0,0), (40,60))]

        # --- 2. TẠO ANIMATION TRÁI ---
        self.anims_left = {}
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        # Load Skill Assets
        self.tornado_frames = load_tornado_assets(factory, SKILL_ASSET_DIR)
        self.wall_frames = load_wall_assets(factory, SKILL_ASSET_DIR)

        # Entity
        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = self.anims_right['idle'][0]
        self.entity.sprite.position = x, y
        
        # --- PHYSICS & MOVEMENT ---
        self.facing_right = True
        self.move_speed_bonus = 0
        
        self.ground_y = y
        self.vel_y = 0
        self.gravity = GRAVITY
        self.jump_force = -PLAYER_JUMP_POWER
        self.is_jumping = False
        self.jump_count = 0
        self.is_running = False

        # --- STATS & COMBAT ---
        self.max_hp = PLAYER_MAX_HEALTH
        self.hp = self.max_hp
        self.max_stamina = PLAYER_MAX_STAMINA
        self.stamina = self.max_stamina
        
        # Base stats
        self.base_attack_damage = PLAYER_ATTACK_DAMAGE
        self.base_move_speed = PLAYER_SPEED_WALK
        self.base_armor = 30
        self.base_lifesteal = 0.05
        
        # Current stats ( = Base + Item)
        self.attack_damage = self.base_attack_damage 
        self.move_speed_bonus = 0
        self.lifesteal_ratio = self.base_lifesteal
        self.damage_reduction = 0.0
        self.armor = self.base_armor
        self.crit_chance = 0
        self.attack_range = 150
        self.attack_speed = 1.0
        self.hp_regen = PLAYER_HEALTH_REGEN
        
        # INVENTORY
        self.gold = 0
        self.consumables = []   # Queue size 3
        self.equipment = []    # Queue size 5
        self.max_consumables = 3
        self.max_equipments = 5


        self.is_blocking = False
        self.exhausted = False
        self.invincible = False 
        self.flash_timer = 0
        self.color_mod = (255, 255, 255)
        
        self.buffs = {} 

        self.state = 'idle'
        self.prev_state = 'idle'
        self.frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.10
        self.hurt_timer = 0
        self.hit_count = 0
        self.dead_animation_complete = False
        
        self.cooldowns = CooldownManager()
        self.skill_q = SkillQ(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)
        
        # --- SKILLS LIST FOR HUD ---
        # Group skills for easy HUD rendering
        self.skills = [
            self.skill_q,  # Index 0 - Q key
            self.skill_w,  # Index 1 - W key
            self.skill_e,  # Index 2 - E key
            None,          # Index 3 - R key (reserved)
            None           # Index 4 - A/S key (reserved)
        ]
        
        # --- NETWORK SUPPORT ---
        self.net_id = None  # Assigned by server during game initialization
        
        # --- UPGRADE SYSTEM ---
        # self.gold = 10 # Starting gold for testing (can be 0)
        self.skill_levels = {'q': 0, 'w': 0, 'e': 0, 'a': 0} # 0 = Base Level
        self.consumables = [] # List of item types (max 3)
        self.equipment = []   # List of item types (max 5)
        
        # Sound tracking
        self.was_on_ground = True
        self.walk_sound_channel = -1
        self.run_sound_channel = -1

        # [NEW] Khởi tạo Mastery Emote
        self.mastery_emote = None
        if renderer_ptr:
            self.mastery_emote = MasteryEmote(renderer_ptr)

    def trigger_mastery(self):
        if self.mastery_emote:
            print("[Player] Mastery Emote Triggered!")
            self.mastery_emote.play()

    def render(self, renderer, camera_x, camera_y):
        if self.mastery_emote:
            self.mastery_emote.render(self.x, self.y, camera_x, camera_y)

    @property
    def sprite(self): return self.entity.sprite
    @property
    def x(self): return self.entity.sprite.x
    @property
    def y(self): return self.entity.sprite.y
    @property
    def width(self): return self.entity.sprite.size[0]
    @property
    def height(self): return self.entity.sprite.size[1]
    
    @property
    def move_speed(self):
        return self.base_move_speed + self.move_speed_bonus

    def get_hitbox(self):
        hitbox_w = 40
        hitbox_h = 80
        offset_x = (128 - hitbox_w) // 2
        offset_y = (128 - hitbox_h)
        return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y), hitbox_w, hitbox_h)

    def get_bounds(self):
        rect = self.get_hitbox()
        return (rect.x, rect.y, rect.w, rect.h)

    def apply_buff(self, name, duration, value=0):
        self.buffs[name] = {'timer': duration, 'value': value}
        if name == "damage_boost":
            self.update_stats()

    def activate_star_skill(self, duration=5.0):
        self.invincible = True
        self.apply_buff("star_invincible", duration)

    def handle_buffs(self, dt):
        expired = []
        for name, data in self.buffs.items():
            data['timer'] -= dt
            if data['timer'] <= 0:
                expired.append(name)
        
        for name in expired:
            del self.buffs[name]
            if name == "damage_boost":
                self.update_stats()
            elif name == "star_invincible":
                self.invincible = False
                self.color_mod = (255, 255, 255)

        if "star_invincible" in self.buffs:
            import time
            if int(time.time() * 10) % 2 == 0:
                self.color_mod = (255, 255, 0)
            else:
                self.color_mod = (255, 200, 200)
        elif "damage_boost" in self.buffs:
            self.color_mod = (200, 100, 255)
        else:
            self.color_mod = (255, 255, 255)

    def update_stats(self):
        # Logic buff tạm thời
        multiplier = 1.0
        if "damage_boost" in self.buffs:
            multiplier = self.buffs["damage_boost"]['value']
        
        # Base dmg + Equipment Dmg
        equipment_bonus = 0
        for item in self.equipment:
            if item == ItemType.BLOODTHIRSTER: equipment_bonus += 10
            elif item == ItemType.INFINITY_EDGE: equipment_bonus += 50
            
        total_base = self.base_attack_damage + equipment_bonus
        
        # Apply Skill 'A' Growth
        scale_a = self.get_skill_damage_scale('a')
        self.attack_damage = int(total_base * multiplier * scale_a)
        
        # Update skill damage multipliers to reflect new AD
        self._update_skill_damage_multipliers()
    
    def _update_skill_damage_multipliers(self):
        """Recalculate skill damage multipliers based on current AD""" 
        from settings import SKILL_DAMAGE_GROWTH, SKILL_AD_RATIO
        
        # Update each skill's damage multiplier
        for skill_key, skill in [('q', self.skill_q), ('w', self.skill_w), ('e', self.skill_e)]:
            level = self.skill_levels.get(skill_key, 0)
            level_scaling = SKILL_DAMAGE_GROWTH ** level
            ad_scaling = (self.attack_damage / self.base_attack_damage) * SKILL_AD_RATIO
            skill.damage_multiplier = level_scaling * ad_scaling

    def update(self, dt, world, factory, renderer, active_list_q, active_list_w, game_map=None, boxes=None):
        # [NEW] Update Mastery
        if self.mastery_emote:
            self.mastery_emote.update()

        self.regenerate()
        self.cooldowns.update(1)
        self.handle_buffs(dt)
        
        dx = 0
        current_speed = self.move_speed
        
        if self.state == 'run': dx = PLAYER_SPEED_RUN * dt
        elif self.state == 'walk': dx = current_speed * dt
        
        if dx > 0:
            if not self.facing_right: dx = -dx
            actual_dx = int(dx)

            if boxes:
                player_rect = self.get_hitbox()
                # use actual_dx instead of int(dx) to ensure synchronize moving direction
                future = sdl2.SDL_Rect(player_rect.x + actual_dx, player_rect.y, player_rect.w, player_rect.h)
                for box in boxes:
                    if sdl2.SDL_HasIntersection(future, box.rect):
                        if not self.is_jumping:
                            # 1. Stand on the ground -> trying to push the box
                            moved, box_dx = box.push(dx, dt, game_map, boxes)
                            actual_dx = int(box_dx) if moved else 0
                        else:
                            # 2. is jumping -> Barrel, Box lock, do not allowed to go through
                            actual_dx = 0

                        break
            self.entity.sprite.x += actual_dx

        # Map collision X
        if game_map:
            hitbox = self.get_hitbox()
            tiles = game_map.get_tile_rects_around(hitbox.x, hitbox.y, hitbox.w, hitbox.h)
            for tile in tiles:
                if sdl2.SDL_HasIntersection(hitbox, tile):
                    if dx > 0: self.entity.sprite.x = tile.x - 128 + 44
                    elif dx < 0: self.entity.sprite.x = tile.x + tile.w - 44

        # 2. Vật lý Y
        if self.is_jumping:
            self.vel_y += self.gravity
            if self.vel_y > MAX_FALL_SPEED: self.vel_y = MAX_FALL_SPEED
        if self.vel_y != 0:
            self.entity.sprite.y += int(self.vel_y)
        
        # Death boundary check: falling into pit
        if self.entity.sprite.y > 700 and self.state != 'dead':
            self.die()
            return

        # Map collision Y
        on_ground = False
        if game_map:
            hitbox = self.get_hitbox()
            tiles = game_map.get_tile_rects_around(hitbox.x, hitbox.y, hitbox.w, hitbox.h)
            feet_rect = sdl2.SDL_Rect(hitbox.x + hitbox.w//2 - 20, hitbox.y + hitbox.h, 40, 5)
            
            for tile in tiles:
                if sdl2.SDL_HasIntersection(hitbox, tile):
                    if self.vel_y > 0: 
                        align_y = tile.y - 80 - 48  
                        self.entity.sprite.y = align_y
                        self.vel_y = 0
                        self.ground_y = tile.y
                        on_ground = True
                    elif self.vel_y < 0:
                        self.entity.sprite.y = tile.y + tile.h - 48
                        self.vel_y = 0
                elif not on_ground and self.vel_y >= 0:
                    if sdl2.SDL_HasIntersection(feet_rect, tile):
                        align_y = tile.y - 80 - 48
                        if abs(self.entity.sprite.y - align_y) <= 8: 
                            self.entity.sprite.y = align_y
                            self.vel_y = 0
                            self.ground_y = tile.y
                            on_ground = True

        if boxes and not on_ground:
            for box in boxes:
                if self.vel_y >= 0:
                    if sdl2.SDL_HasIntersection(feet_rect, box.rect):
                        align_y = box.rect.y - 80 - 48
                        self.entity.sprite.y = align_y
                        self.vel_y = 0
                        self.ground_y = box.rect.y
                        on_ground = True
                        break

        self.is_jumping = not on_ground
        if on_ground: 
            self.jump_count = 0
            if not self.was_on_ground and self.sound_manager:
                self.sound_manager.play_sound("player_land")
        self.was_on_ground = on_ground
        if self.is_jumping and self.vel_y == 0: self.vel_y = self.gravity

        # Timers
        if self.state == 'hurt':
            self.hurt_timer += dt
            if self.hurt_timer >= PLAYER_HURT_DURATION: self.state = 'idle'
        
        self.anim_timer += dt
        if self.flash_timer > 0: self.flash_timer -= dt

        # Animation Selection
        current_anims = self.anims_right if self.facing_right else self.anims_left
        frames = []
        
        if self.state == 'dead': frames = current_anims.get('dead', current_anims['idle'])
        elif self.state == 'hurt': frames = current_anims.get('hurt', current_anims['idle'])
        elif self.state == 'casting_q': frames = current_anims['q']
        elif self.state == 'casting_w': frames = current_anims['w']
        elif self.state == 'dashing_e': frames = current_anims['e']
        elif self.state == 'attacking': frames = current_anims.get('attack_normal', current_anims['idle'])
        elif self.is_blocking: frames = current_anims.get('block', current_anims['idle'])
        elif self.is_jumping: frames = current_anims.get('jump', current_anims['idle'])
        elif self.state == 'run': frames = current_anims.get('run', current_anims['idle'])
        elif self.state == 'walk': frames = current_anims.get('walk', current_anims['idle'])
        else: frames = current_anims['idle']

        if not frames: return

        if self.state != self.prev_state:
            self.frame_index = 0
            self.prev_state = self.state

        speed = 0.05 if self.state == 'attacking' else self.anim_speed
        
        if self.anim_timer >= speed:
            self.anim_timer = 0
            self.frame_index += 1
            if self.frame_index >= len(frames):
                if self.state == 'casting_q':
                    self.spawn_tornado(world, factory, renderer, active_list_q)
                    if self.sound_manager:
                        self.sound_manager.play_sound("player_q2")
                    self.state = 'idle'
                elif self.state == 'casting_w':
                    self.spawn_wall(world, factory, renderer, active_list_w)
                    if self.sound_manager:
                        self.sound_manager.play_sound("player_w2")
                    self.state = 'idle'
                elif self.state == 'dashing_e':
                    if not self.skill_e.is_dashing: 
                        if self.sound_manager:
                            self.sound_manager.play_sound("player_e2")
                        self.state = 'idle'
                elif self.state == 'attacking': self.state = 'idle'
                elif self.state == 'dead': 
                    self.frame_index = len(frames) - 1
                    self.dead_animation_complete = True
                    return
                self.frame_index = 0

        idx = self.frame_index % len(frames)
        old_pos = self.entity.sprite.position
        self.entity.sprite = frames[idx]
        self.entity.sprite.position = old_pos

    # --- ACTIONS ---
    def jump(self):
        if self.jump_count < PLAYER_MAX_JUMPS:
            self.vel_y = self.jump_force
            self.is_jumping = True
            self.jump_count += 1
            if self.sound_manager:
                self.sound_manager.play_sound("player_jump")

    def handle_movement(self, keys):
        if self.is_blocking or self.state in ['casting_q', 'casting_w', 'dashing_e', 'attacking', 'dead', 'hurt']: return
        
        has_input = False
        if keys[sdl2.SDL_SCANCODE_RIGHT]:
            self.facing_right = True; has_input = True
        elif keys[sdl2.SDL_SCANCODE_LEFT]:
            self.facing_right = False; has_input = True
            
        if has_input:
            run_key = keys[sdl2.SDL_SCANCODE_LSHIFT] or keys[sdl2.SDL_SCANCODE_RSHIFT]
            if run_key and self.try_run(): 
                self.state = 'run'
                if self.sound_manager and self.run_sound_channel == -1:
                    self.run_sound_channel = self.sound_manager.play_sound("player_run", loops=-1)
            else: 
                self.state = 'walk'
                self.is_running = False
                if self.run_sound_channel != -1:
                    sdl2.sdlmixer.Mix_HaltChannel(self.run_sound_channel)
                    self.run_sound_channel = -1
                if self.sound_manager and self.walk_sound_channel == -1:
                    self.walk_sound_channel = self.sound_manager.play_sound("player_walk", loops=-1)
        else:
            if not self.is_jumping: self.state = 'idle'
            self.is_running = False
            if self.walk_sound_channel != -1:
                sdl2.sdlmixer.Mix_HaltChannel(self.walk_sound_channel)
                self.walk_sound_channel = -1
            if self.run_sound_channel != -1:
                sdl2.sdlmixer.Mix_HaltChannel(self.run_sound_channel)
                self.run_sound_channel = -1

    def try_run(self):
        if self.exhausted: return False
        if self.stamina >= PLAYER_RUN_COST:
            self.stamina -= PLAYER_RUN_COST; self.is_running = True; return True
        else:
            self.is_running = False; self.exhausted = True; return False

    def regenerate(self):
        if self.hp < self.max_hp: self.hp = min(self.hp + self.hp_regen, self.max_hp)
        if self.state == 'walk' and self.stamina < self.max_stamina:
            self.stamina = min(self.stamina + PLAYER_STAMINA_REGEN_WALK, self.max_stamina)
        if self.exhausted and self.stamina > self.max_stamina * 0.3: self.exhausted = False

    def start_q(self, direction=0):
        if self.stamina < SKILL_Q_COST or not self.cooldowns.is_ready("skill_q"): return
        if self.state in ['idle', 'jumping', 'run', 'walk']:
            self.stamina -= SKILL_Q_COST
            cd = self.get_skill_cooldown('q')
            self.cooldowns.start_cooldown("skill_q", cd)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_q'; self.frame_index = 0
            if self.sound_manager:
                self.sound_manager.play_sound("player_q1")

    def start_w(self, direction=0):
        if self.stamina < SKILL_W_COST or not self.cooldowns.is_ready("skill_w"): return
        if self.state in ['idle', 'jumping']:
            self.stamina -= SKILL_W_COST
            cd = self.get_skill_cooldown('w')
            self.cooldowns.start_cooldown("skill_w", cd)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_w'; self.frame_index = 0
            if self.sound_manager:
                self.sound_manager.play_sound("player_w1")

    def start_e(self, world, factory, renderer, direction):
        if self.stamina < SKILL_E_COST or not self.cooldowns.is_ready("skill_e"): return
        if direction and self.state != 'dashing_e':
            self.stamina -= SKILL_E_COST
            cd = self.get_skill_cooldown('e')
            self.cooldowns.start_cooldown("skill_e", cd)
            self.facing_right = (direction > 0)
            self.state = 'dashing_e'; self.frame_index = 0
            
            # Update skill stats before cast
            self.skill_e.update_stats(self.skill_levels['e'])
            self.skill_e.damage_multiplier = SKILL_DAMAGE_GROWTH ** self.skill_levels['e'] # Sync multiplier clearly
            self.skill_e.cast(world, factory, renderer)
            if self.sound_manager:
                self.sound_manager.play_sound("player_e1")

    def spawn_tornado(self, world, factory, renderer, active_list):
        if self.tornado_frames: 
            t = self.skill_q.cast(world, factory, renderer, skill_sprites=self.tornado_frames)
            if t: active_list.append(t)

    def spawn_wall(self, world, factory, renderer, active_list):
        if self.wall_frames: 
            w = self.skill_w.cast(world, factory, renderer, skill_sprites=self.wall_frames)
            if w: active_list.append(w)

    def attack(self):
        if self.state in ['idle', 'run', 'walk'] and not self.is_blocking:
            if self.cooldowns.is_ready("attack"):
                self.state = 'attacking'; self.frame_index = 0
                cd = self.get_skill_cooldown('a')
                self.cooldowns.start_cooldown("attack", cd)

    def set_blocking(self, blocking):
        if blocking and self.stamina > 0: self.is_blocking = True; self.state = 'idle'
        else: self.is_blocking = False

    def take_damage(self, amount):
        if self.invincible: return
        final_dmg = int(amount)
        if self.damage_reduction > 0:
            final_dmg = int(final_dmg * (1.0 - self.damage_reduction))
        damage_after_armor = max(1, final_dmg - int(self.armor * 0.1))

        if self.is_blocking:
            if self.stamina >= BLOCK_STAMINA_COST_PER_HIT:
                self.stamina -= BLOCK_STAMINA_COST_PER_HIT
                damage_after_armor = int(damage_after_armor * (1.0 - BLOCK_DAMAGE_REDUCTION))
            else: self.is_blocking = False
        
        self.hp -= damage_after_armor
        if self.hp <= 0: self.die()
        else:
            self.flash_timer = 0.1
            self.hit_count += 1
            if self.sound_manager:
                self.sound_manager.play_sound("player_hit")
            if self.hit_count >= PLAYER_HITS_TO_STAGGER and self.state != 'dead':
                if self.sound_manager:
                    self.sound_manager.play_sound("player_hurt", duration=1000)
                self.state = 'hurt'; self.hurt_timer = 0; self.hit_count = 0

    def on_hit_enemy(self, damage):
        self.stamina = min(self.stamina + Reward_Hit_Stamina, self.max_stamina)
        heal = int(damage * self.lifesteal_ratio)
        if heal > 0: self.hp = min(self.hp + heal, self.max_hp)

    def on_kill_enemy(self):
        self.stamina = min(self.stamina + Reward_Kill_Stamina, self.max_stamina)

    def die(self): self.state = 'dead'; self.frame_index = 0

    # --- UPGRADE METHODS ---
    def get_skill_cooldown(self, skill_key):
        """Calculate cooldown based on level"""
        base_cd = 0
        if skill_key == 'q': base_cd = SKILL_Q_COOLDOWN
        elif skill_key == 'w': base_cd = SKILL_W_COOLDOWN
        elif skill_key == 'e': base_cd = SKILL_E_COOLDOWN
        elif skill_key == 'a': base_cd = ATTACK_COOLDOWN
        
        level = self.skill_levels.get(skill_key, 0)
        current_cd = base_cd
        
        # New Logic: Reduce by max(25% of current, 0.2s) per level
        from settings import SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN, FPS
        
        for _ in range(level):
            reduction = max(current_cd * SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN * FPS)
            current_cd -= reduction
            
        return max(0.0, current_cd)

    def get_skill_damage_scale(self, skill_key):
        """Return damage multiplier for a skill"""
        level = self.skill_levels.get(skill_key, 0)
        return SKILL_DAMAGE_GROWTH ** level

    def upgrade_skill(self, skill_key):
        """Upgrade a skill if affordable"""
        if skill_key not in self.skill_levels: return False
        
        current_lvl = self.skill_levels[skill_key]
        if current_lvl >= SKILL_MAX_LEVEL:
            print(f"[Upgrade] Skill {skill_key.upper()} is max level!")
            return False
            
        next_lvl = current_lvl + 1
        cost = SKILL_UPGRADE_COSTS.get(next_lvl, 999)
        
        if self.gold >= cost:
            self.gold -= cost
            self.skill_levels[skill_key] = next_lvl
            
            # Update Skill Object Logic
            if skill_key == 'q': self.skill_q.update_stats(next_lvl)
            elif skill_key == 'w': self.skill_w.update_stats(next_lvl)
            elif skill_key == 'e': self.skill_e.update_stats(next_lvl)
            elif skill_key == 'a': self.update_stats() # Recalculate AD
            
            print(f"[Upgrade] Upgraded {skill_key.upper()} to Level {next_lvl} for {cost} Gold.")
            return True
        else:
            print(f"[Upgrade] Not enough gold! Need {cost}, have {self.gold}.")
            return False

    def can_upgrade_skill(self, skill_key):
        """Check if a skill can be upgraded (for UI)"""
        if skill_key not in self.skill_levels: return False
        
        current_lvl = self.skill_levels[skill_key]
        if current_lvl >= SKILL_MAX_LEVEL:
            return False
            
        next_lvl = current_lvl + 1
        cost = SKILL_UPGRADE_COSTS.get(next_lvl, 999)
        
        return self.gold >= cost

    def collect_item(self, item_type):
        category = ITEM_REGISTRY.get(item_type)

        if category == ItemCategory.CURRENCY:
            self.gold += 1 
            print(f"[Player] Gold: {self.gold}")

        elif category == ItemCategory.CONSUMABLE:
            if len(self.consumables) >= self.max_consumables:
                removed = self.consumables.pop(0)   # FIFO
                print(f"[Player] Inventory Full! Drop {removed}")
            
            self.consumables.append(item_type)
            print(f"[Player] Added Consumable: {item_type.name}")

        elif category == ItemCategory.EQUIPMENT:
            if len(self.equipment) >= self.max_equipments:
                removed = self.equipment.pop(0)
                print(f"[Player] Equipment Full! Lost {removed}")
            
            self.equipment.append(item_type)
            self.recalculate_stats()    # Recalculate stats based on new list
            print(f"[Player] Equipped: {item_type.name}")

    def use_consumable(self, slot_index):
        """
            Called when pressing 1, 2, 3
            Returns the ItemType if successful, None if slot is empty
        """
        if 0 <= slot_index < len(self.consumables):
            item_type = self.consumables.pop(slot_index)
            self.apply_consumable_effect(item_type)
            return item_type
        return None

    def apply_consumable_effect(self, item_type):
        if item_type == ItemType.TEAR:
            self.stamina += 50
            print("Used Tear of Goddess")
        if item_type == ItemType.HEALTH_POTION:
            self.hp = min(self.hp + 100, self.max_hp)
            # if self.sound_manager: self.sound_manager.play_sound("player_land") # Reuse sound or add potion sound
            print("Used Health Potion")
        elif item_type == ItemType.HOURGLASS:
            self.activate_star_skill(duration=3.0)
            print("Used Hourglass")

    def recalculate_stats(self):
        # Reset to base
        self.move_speed_bonus = 0
        self.lifesteal_ratio = self.base_lifesteal
        self.damage_reduction = 0.0
        self.armor = self.base_armor
        self.max_stamina = PLAYER_MAX_STAMINA # Reset stamina max
        
        equipment_bonus = 0
        
        # Apply all items in queue
        for item in self.equipment:
            if item == ItemType.GREAVES:
                self.move_speed_bonus += 50
            elif item == ItemType.BLOODTHIRSTER:
                self.lifesteal_ratio += 0.10
                self.attack_damage += 10
            elif item == ItemType.INFINITY_EDGE:
                equipment_bonus += 50
            elif item == ItemType.THORNMAIL:
                self.armor += 10
                self.damage_reduction += 0.05 

        # Cap stats if needed
        self.stamina = min(self.stamina, self.max_stamina)

        self.update_stats()

    # ── Multiplayer network helpers ─────────────────────────────────────────

    def get_network_state(self) -> dict:
        """
        Return a snapshot dict suitable for a PLAYER_STATE packet.
        Called every frame by the network layer.
        """
        import time as _time
        return {
            'x':           self.x,
            'y':           self.y,
            'vel_y':       self.vel_y,
            'facing_right': self.facing_right,
            'state':       self.state,
            'hp':          self.hp,
            'stamina':     self.stamina,
            'frame_index': self.frame_index,
            'ts':          _time.monotonic(),
        }

    def apply_network_state(self, data: dict):
        """
        Apply a PLAYER_STATE packet received by the server (from the remote client)
        so the server-side entity list stays authoritative.
        Only updates position/hp/state; does NOT drive animations.
        """
        if not data:
            return
        self.entity.sprite.x = int(data.get('x', self.x))
        self.entity.sprite.y = int(data.get('y', self.y))
        self.vel_y           = data.get('vel_y', self.vel_y)
        self.facing_right    = data.get('facing_right', self.facing_right)
        self.state           = data.get('state', self.state)
        self.hp              = data.get('hp', self.hp)
        self.stamina         = data.get('stamina', self.stamina)

    def get_save_data(self):
        """
            Wrap all current stats of player
        """
        return {
            # 1. Vị trí (Sẽ bị ghi đè bởi vị trí Checkpoint)
            'x': self.x, 
            'y': self.y,
            
            # 2. Chỉ số sinh tồn
            'hp': self.hp,
            'max_hp': self.max_hp,
            'stamina': self.stamina,
            'max_stamina': self.max_stamina,
            
            # 3. Tài sản & Túi đồ (Phải dùng copy để tránh lỗi tham chiếu)
            'gold': self.gold,
            'consumables': copy.deepcopy(self.consumables),
            'equipment': copy.deepcopy(self.equipment),
            
            # 4. Chỉ số chiến đấu (đã cộng dồn từ đồ)
            'attack_damage': self.attack_damage,
            'armor': self.armor,
            'move_speed_bonus': self.move_speed_bonus,
            'lifesteal_ratio': self.lifesteal_ratio
        }
    
    def load_save_data(self, data, spawn_x, spawn_y):
        """Khôi phục trạng thái nhân vật từ dữ liệu đã lưu"""
        if not data: return

        # 1. Khôi phục vị trí (Tại tượng)
        self.entity.sprite.x = spawn_x
        self.entity.sprite.y = spawn_y
        self.ground_y = spawn_y
        self.vel_y = 0
        
        # 2. Khôi phục chỉ số
        self.hp = data['hp']
        self.max_hp = data['max_hp']
        self.stamina = data['stamina']
        self.max_stamina = data['max_stamina']
        
        # 3. Khôi phục túi đồ
        self.gold = data['gold']
        self.consumables = copy.deepcopy(data['consumables'])
        self.equipment = copy.deepcopy(data['equipment'])
        
        # 4. Khôi phục chỉ số chiến đấu
        self.attack_damage = data['attack_damage']
        self.armor = data['armor']
        self.move_speed_bonus = data['move_speed_bonus']
        self.lifesteal_ratio = data['lifesteal_ratio']
        
        # Reset các trạng thái
        self.state = 'idle'
        self.is_blocking = False
        self.dead_animation_complete = False
        print(f"[SYSTEM] Player respawned at Checkpoint with {self.hp} HP")

    def respawn_penalty(self, spawn_x, spawn_y):
        """
            Respawn at the latest checkpoint with the penalty
            - lose 30% gold
            - lose of equipments and consumables
        """
        print(f"[SYSTEM] Respawning at Checkpoint ({spawn_x}, {spawn_y})...")

        # 1. Reset position and the live state
        self.entity.sprite.x = spawn_x
        self.entity.sprite.y = spawn_y
        self.ground_y = spawn_y
        self.vel_y = 0

        self.hp = self.max_hp
        self.stamina = self.max_stamina
        self.state = 'idle'
        self.dead_animation_complete = False
        self.is_blocking = False
        self.invincible = False
        self.color_mod = (255, 255, 255)

        # 2. Resolved penalty
        old_gold = self.gold
        self.gold = int(old_gold * 0.7)

        self.consumables = []
        self.equipment = []

        self.recalculate_stats()

        print(f"[PENALTY] Gold: {old_gold} -> {self.gold}. Inventory Cleared.")
    
    def reset_to_default(self, start_x, start_y):
        """
            Reset all to the initial state
        """
        self.entity.sprite.x = start_x
        self.entity.sprite.y = start_y
        self.vel_y = 0

        self.hp = self.max_hp
        self.stamina = self.max_stamina

        # reset all
        self.gold = int(self.gold * 0.5) # penalty 50% of gold
        self.consumables = []
        self.equipment = []
        self.recalculate_stats()

        self.state = 'idle'
        self.dead_animation_complete = False
        self.is_blocking = False
        self.color_mod = (255, 255, 255)