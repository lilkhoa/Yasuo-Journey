import sdl2
import sdl2.ext
import os
import sys

# Cấu hình đường dẫn
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

class Player:
    def __init__(self, world, factory, x, y):
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
        self.move_speed = 300
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
        self.base_attack_damage = PLAYER_ATTACK_DAMAGE
        self.attack_damage = self.base_attack_damage # Damage thực tế (có buff)
        
        self.is_blocking = False
        self.exhausted = False
        self.invincible = False # Bất tử (Star item)
        self.flash_timer = 0    # Hiệu ứng nhấp nháy đỏ khi bị đánh
        self.color_mod = (255, 255, 255) # Màu sắc nhân vật (dùng cho buff)
        
        self.buffs = {} # {name: {'timer': float, 'value': float}}

        self.state = 'idle'
        self.prev_state = 'idle'
        self.frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.10
        self.hurt_timer = 0
        self.hit_count = 0
        
        self.cooldowns = CooldownManager()
        self.skill_q = SkillQ(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)

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
    
    def get_hitbox(self):
        hitbox_w = 40
        hitbox_h = 80
        offset_x = (128 - hitbox_w) // 2
        offset_y = (128 - hitbox_h)
        return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y), hitbox_w, hitbox_h)

    # --- [FIX LỖI] THÊM HÀM NÀY ĐỂ TƯƠNG THÍCH VỚI PROJECTILE ---
    def get_bounds(self):
        """Trả về (x, y, w, h) của hitbox để hệ thống đạn NPC sử dụng"""
        rect = self.get_hitbox()
        return (rect.x, rect.y, rect.w, rect.h)

    # --- BUFF & STATS SYSTEM ---
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

        # Hiệu ứng hình ảnh cho Buff
        if "star_invincible" in self.buffs:
            import time
            # Nhấp nháy vàng
            if int(time.time() * 10) % 2 == 0:
                self.color_mod = (255, 255, 0)
            else:
                self.color_mod = (255, 200, 200)
        elif "damage_boost" in self.buffs:
            self.color_mod = (200, 100, 255) # Tím
        else:
            self.color_mod = (255, 255, 255)

    def update_stats(self):
        # Tính damage
        multiplier = 1.0
        if "damage_boost" in self.buffs:
            multiplier = self.buffs["damage_boost"]['value']
        self.attack_damage = int(self.base_attack_damage * multiplier)

    # --- LOGIC CHÍNH ---
    def update(self, dt, world, factory, renderer, active_list_q, active_list_w, game_map=None, boxes=None):
        self.regenerate()
        self.cooldowns.update(1)
        self.handle_buffs(dt) # Cập nhật buff
        
        # 1. Di chuyển X
        dx = 0
        if self.state == 'run': dx = PLAYER_SPEED_RUN * dt
        elif self.state == 'walk': dx = PLAYER_SPEED_WALK * dt
        
        if dx > 0:
            if not self.facing_right: dx = -dx
            actual_dx = int(dx)

            if boxes:
                player_rect = self.get_hitbox()
                future = sdl2.SDL_Rect(player_rect.x + int(dx), player_rect.y, player_rect.w, player_rect.h)
                for box in boxes:
                    if sdl2.SDL_HasIntersection(future, box.rect):
                        moved, box_dx = box.push(dx, dt, game_map)
                        actual_dx = int(box_dx) if moved else 0
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

        # Map collision Y
        on_ground = False
        if game_map:
            hitbox = self.get_hitbox()
            tiles = game_map.get_tile_rects_around(hitbox.x, hitbox.y, hitbox.w, hitbox.h)
            feet = sdl2.SDL_Rect(hitbox.x + 10, hitbox.y + hitbox.h, hitbox.w - 20, 4)
            
            for tile in tiles:
                if sdl2.SDL_HasIntersection(hitbox, tile):
                    if self.vel_y >= 0:
                        self.entity.sprite.y = tile.y - 128
                        self.vel_y = 0
                        self.ground_y = tile.y
                        on_ground = True
                    elif self.vel_y < 0:
                        self.entity.sprite.y = tile.y + tile.h - 48
                        self.vel_y = 0
                elif not on_ground and self.vel_y >= 0:
                     if sdl2.SDL_HasIntersection(feet, tile):
                        if abs(self.entity.sprite.y - (tile.y - 128)) <= 8:
                            self.entity.sprite.y = tile.y - 128
                            self.vel_y = 0
                            self.ground_y = tile.y
                            on_ground = True

        # Box collision Y
        if boxes and not on_ground:
            hitbox = self.get_hitbox()
            for box in boxes:
                if sdl2.SDL_HasIntersection(hitbox, box.rect):
                    if self.vel_y >= 0:
                        self.entity.sprite.y = box.rect.y - 128
                        self.vel_y = 0
                        on_ground = True
                        break
        
        self.is_jumping = not on_ground
        if on_ground: self.jump_count = 0
        if self.is_jumping and self.vel_y == 0: self.vel_y = self.gravity
        if self.entity.sprite.y > 1000: self.die()

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
                    self.state = 'idle'
                elif self.state == 'casting_w':
                    self.spawn_wall(world, factory, renderer, active_list_w)
                    self.state = 'idle'
                elif self.state == 'dashing_e':
                    if not self.skill_e.is_dashing: self.state = 'idle'
                elif self.state == 'attacking': self.state = 'idle'
                elif self.state == 'dead': 
                    self.frame_index = len(frames) - 1
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

    def handle_movement(self, keys):
        if self.is_blocking or self.state in ['casting_q', 'casting_w', 'dashing_e', 'attacking', 'dead', 'hurt']: return
        
        has_input = False
        if keys[sdl2.SDL_SCANCODE_RIGHT]:
            self.facing_right = True; has_input = True
        elif keys[sdl2.SDL_SCANCODE_LEFT]:
            self.facing_right = False; has_input = True
            
        if has_input:
            run_key = keys[sdl2.SDL_SCANCODE_LSHIFT] or keys[sdl2.SDL_SCANCODE_RSHIFT]
            if run_key and self.try_run(): self.state = 'run'
            else: self.state = 'walk'; self.is_running = False
        else:
            if not self.is_jumping: self.state = 'idle'
            self.is_running = False

    def try_run(self):
        if self.exhausted: return False
        if self.stamina >= PLAYER_RUN_COST:
            self.stamina -= PLAYER_RUN_COST; self.is_running = True; return True
        else:
            self.is_running = False; self.exhausted = True; return False

    def regenerate(self):
        if self.hp < self.max_hp: self.hp = min(self.hp + PLAYER_HEALTH_REGEN, self.max_hp)
        if self.state == 'walk' and self.stamina < self.max_stamina:
            self.stamina = min(self.stamina + PLAYER_STAMINA_REGEN_WALK, self.max_stamina)
        if self.exhausted and self.stamina > self.max_stamina * 0.3: self.exhausted = False

    def start_q(self, direction=0):
        if self.stamina < SKILL_Q_COST or not self.cooldowns.is_ready("skill_q"): return
        if self.state in ['idle', 'jumping', 'run', 'walk']:
            self.stamina -= SKILL_Q_COST
            self.cooldowns.start_cooldown("skill_q", SKILL_Q_COOLDOWN)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_q'; self.frame_index = 0

    def start_w(self, direction=0):
        if self.stamina < SKILL_W_COST or not self.cooldowns.is_ready("skill_w"): return
        if self.state in ['idle', 'jumping']:
            self.stamina -= SKILL_W_COST
            self.cooldowns.start_cooldown("skill_w", SKILL_W_COOLDOWN)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_w'; self.frame_index = 0

    def start_e(self, world, factory, renderer, direction):
        if self.stamina < SKILL_E_COST or not self.cooldowns.is_ready("skill_e"): return
        if direction and self.state != 'dashing_e':
            self.stamina -= SKILL_E_COST
            self.cooldowns.start_cooldown("skill_e", SKILL_E_COOLDOWN)
            self.facing_right = (direction > 0)
            self.state = 'dashing_e'; self.frame_index = 0
            self.skill_e.cast(world, factory, renderer)

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
                self.cooldowns.start_cooldown("attack", ATTACK_COOLDOWN)

    def set_blocking(self, blocking):
        if blocking and self.stamina > 0: self.is_blocking = True; self.state = 'idle'
        else: self.is_blocking = False

    def take_damage(self, amount):
        if self.invincible: return
        final_dmg = int(amount)
        if self.is_blocking:
            if self.stamina >= BLOCK_STAMINA_COST_PER_HIT:
                self.stamina -= BLOCK_STAMINA_COST_PER_HIT
                final_dmg = int(amount * (1.0 - BLOCK_DAMAGE_REDUCTION))
            else: self.is_blocking = False
        
        self.hp -= final_dmg
        if self.hp <= 0: self.die()
        else:
            self.flash_timer = 0.1
            self.hit_count += 1
            if self.hit_count >= PLAYER_HITS_TO_STAGGER and self.state != 'dead':
                self.state = 'hurt'; self.hurt_timer = 0; self.hit_count = 0

    def on_hit_enemy(self, damage):
        self.stamina = min(self.stamina + Reward_Hit_Stamina, self.max_stamina)
        self.hp = min(self.hp + damage * (PLAYER_LIFESTEAL/100), self.max_hp)

    def on_kill_enemy(self):
        self.stamina = min(self.stamina + Reward_Kill_Stamina, self.max_stamina)

    def die(self): self.state = 'dead'; self.frame_index = 0