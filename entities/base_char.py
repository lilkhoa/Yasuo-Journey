import sdl2
import sdl2.ext
import sdl2.sdlmixer
import os
import sys
import ctypes
import copy
import time

from settings import *
from combat.refactored_cooldown import CooldownManager
from items.item import ItemType, ItemCategory, ITEM_REGISTRY
from entities.mastery_emote import MasteryEmote

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)
PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')

# ==============================================================================
# CLASS CƠ SỞ CHO MỌI NHÂN VẬT (Gộp logic chung của Player và Player_2)
# ==============================================================================
class BaseChar:
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        self.sound_manager = sound_manager
        
        # Animations (Sẽ được class con nạp)
        self.anims_right = {}
        self.anims_left = {}
        
        # Entity
        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = None # Chờ class con gán
        
        # --- PHYSICS & MOVEMENT ---
        self.facing_right = True
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
        self.base_move_speed = PLAYER_SPEED_WALK
        self.base_armor = 30
        self.base_lifesteal = 0.05
        
        self.attack_damage = self.base_attack_damage 
        self.move_speed_bonus = 0
        self.lifesteal_ratio = self.base_lifesteal
        self.damage_reduction = 0.0
        self.armor = self.base_armor
        self.crit_chance = 0
        self.attack_range = 150
        self.attack_speed = 1.0
        self.hp_regen = PLAYER_HEALTH_REGEN
        
        # --- INVENTORY ---
        self.gold = 0
        self.consumables = []
        self.equipment = []
        self.max_consumables = 3
        self.max_equipments = 5

        # --- STATUS & STATE MACHINE ---
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
        
        # Skills placeholders
        self.skill_q = None
        self.skill_w = None
        self.skill_e = None
        self.skills = [None, None, None, None, None]
        
        # --- NETWORK SUPPORT ---
        self.net_id = None
        
        # --- UPGRADE SYSTEM ---
        self.skill_levels = {'q': 0, 'w': 0, 'e': 0, 'a': 0}
        
        # --- SOUND TRACKING ---
        self.was_on_ground = True
        self.walk_sound_channel = -1
        self.run_sound_channel = -1

        # --- MASTERY EMOTE ---
        self.mastery_emote = None
        if renderer_ptr:
            self.mastery_emote = MasteryEmote(renderer_ptr)

    # ================= CÁC HÀM CƠ BẢN VÀ THUỘC TÍNH =================
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

    # Hard code for yasuo
    # def get_hitbox(self):
    #     hitbox_w = 40
    #     hitbox_h = 80
    #     offset_x = (128 - hitbox_w) // 2
    #     offset_y = (128 - hitbox_h)
    #     return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y), hitbox_w, hitbox_h)

    # More flexible
    def get_hitbox(self):
        # Tính kích thước hitbox dựa trên scale_factor (nếu có)
        scale = getattr(self, 'scale_factor', 1.0)
        hitbox_w = int(40 * scale)
        hitbox_h = int(80 * scale)
        
        # Lấy kích thước thật của sprite hiện tại thay vì hardcode 128
        sprite_w = self.width if self.entity.sprite else 128
        sprite_h = self.height if self.entity.sprite else 128
        
        # Nhân vật luôn đứng ở giữa theo trục X, và chân chạm đáy trục Y
        offset_x = (sprite_w - hitbox_w) // 2
        offset_y = sprite_h - hitbox_h
        
        return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y), hitbox_w, hitbox_h)

    def get_bounds(self):
        rect = self.get_hitbox()
        return (rect.x, rect.y, rect.w, rect.h)

    def trigger_mastery(self):
        if self.mastery_emote:
            print("[Player] Mastery Emote Triggered!")
            self.mastery_emote.play()

    def render(self, renderer, camera_x, camera_y):
        if self.mastery_emote:
            self.mastery_emote.render(self.x, self.y, camera_x, camera_y)
        
        hitbox = sdl2.SDL_Rect(
            int(self.x),
            int(self.y),
            int(self.width),
            int(self.height)
        )

        # Debug collision box disabled
        # self.draw_debug_rect(renderer, hitbox, camera_x, camera_y)  # đỏ = hitbox

    # ================= HỆ THỐNG BUFF VÀ CHỈ SỐ =================
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
            if int(time.time() * 10) % 2 == 0:
                self.color_mod = (255, 255, 0)
            else:
                self.color_mod = (255, 200, 200)
        elif "damage_boost" in self.buffs:
            self.color_mod = (200, 100, 255)
        else:
            self.color_mod = (255, 255, 255)

    def update_stats(self):
        multiplier = 1.0
        if "damage_boost" in self.buffs:
            multiplier = self.buffs["damage_boost"]['value']
        
        equipment_bonus = 0
        for item in self.equipment:
            if item == ItemType.BLOODTHIRSTER: equipment_bonus += 10
            elif item == ItemType.INFINITY_EDGE: equipment_bonus += 50
            
        total_base = self.base_attack_damage + equipment_bonus
        scale_a = self.get_skill_damage_scale('a')
        self.attack_damage = int(total_base * multiplier * scale_a)
        
        self._update_skill_damage_multipliers()
    
    def _update_skill_damage_multipliers(self):
        from settings import SKILL_DAMAGE_GROWTH, SKILL_AD_RATIO
        for skill_key, skill in [('q', self.skill_q), ('w', self.skill_w), ('e', self.skill_e)]:
            if skill:
                level = self.skill_levels.get(skill_key, 0)
                level_scaling = SKILL_DAMAGE_GROWTH ** level
                ad_scaling = (self.attack_damage / self.base_attack_damage) * SKILL_AD_RATIO
                skill.damage_multiplier = level_scaling * ad_scaling

    # ================= VÒNG LẶP UPDATE (PHYSICS & ANIMATION) =================
    def update(self, dt, world, factory, renderer, game_map=None, boxes=None):
        if self.mastery_emote:
            self.mastery_emote.update()

        self.regenerate()
        self.cooldowns.update(1)
        self.handle_buffs(dt)
        
        dx = 0
        current_speed = self.move_speed
        
        if self.state == 'run': dx = PLAYER_SPEED_RUN * dt
        elif self.state == 'walk': dx = current_speed * dt
        
        # 1. Vật lý X
        if dx > 0:
            if not self.facing_right: dx = -dx
            actual_dx = int(dx)

            if boxes:
                player_rect = self.get_hitbox()
                future = sdl2.SDL_Rect(player_rect.x + actual_dx, player_rect.y, player_rect.w, player_rect.h)
                for box in boxes:
                    if sdl2.SDL_HasIntersection(future, box.rect):
                        if not self.is_jumping:
                            moved, box_dx = box.push(dx, dt, game_map, boxes)
                            actual_dx = int(box_dx) if moved else 0
                        else:
                            actual_dx = 0
                        break
            if self.entity.sprite:
                self.entity.sprite.x += actual_dx

        if game_map and self.entity.sprite:
            hitbox = self.get_hitbox()
            offset_x = hitbox.x - self.x
            offset_y = hitbox.y - self.y
            tiles = game_map.get_tile_rects_around(hitbox.x, hitbox.y, hitbox.w, hitbox.h)
            for tile in tiles:
                if sdl2.SDL_HasIntersection(hitbox, tile):
                    # Tự động tính toán khoảng cách chạm tường thay vì dùng 128
                    if dx > 0: self.entity.sprite.x = tile.x - offset_x - hitbox.w
                    elif dx < 0: self.entity.sprite.x = tile.x + tile.w - offset_x

        # 2. Vật lý Y
        if self.is_jumping:
            self.vel_y += self.gravity
            if self.vel_y > MAX_FALL_SPEED: self.vel_y = MAX_FALL_SPEED
        if self.vel_y != 0 and self.entity.sprite:
            self.entity.sprite.y += int(self.vel_y)
        
        if self.entity.sprite and self.entity.sprite.y > 700 and self.state != 'dead':
            self.die()
            return

        on_ground = False
        if game_map and self.entity.sprite:
            hitbox = self.get_hitbox()
            offset_x = hitbox.x - self.x
            offset_y = hitbox.y - self.y
            tiles = game_map.get_tile_rects_around(hitbox.x, hitbox.y, hitbox.w, hitbox.h)
            
            # Hitbox dưới chân
            feet_rect = sdl2.SDL_Rect(hitbox.x + hitbox.w//2 - 20, hitbox.y + hitbox.h, 40, 5)
            
            for tile in tiles:
                if sdl2.SDL_HasIntersection(hitbox, tile):
                    if self.vel_y > 0: 
                        align_y = tile.y - offset_y - hitbox.h 
                        self.entity.sprite.y = align_y
                        self.vel_y = 0
                        self.ground_y = tile.y
                        on_ground = True
                    elif self.vel_y < 0:
                        self.entity.sprite.y = tile.y + tile.h - offset_y
                        self.vel_y = 0
                elif not on_ground and self.vel_y >= 0:
                    if sdl2.SDL_HasIntersection(feet_rect, tile):
                        align_y = tile.y - offset_y - hitbox.h
                        if abs(self.entity.sprite.y - align_y) <= 8: 
                            self.entity.sprite.y = align_y
                            self.vel_y = 0
                            self.ground_y = tile.y
                            on_ground = True

        if boxes and not on_ground and self.entity.sprite:
            hitbox = self.get_hitbox()
            offset_y = hitbox.y - self.y
            feet_rect = sdl2.SDL_Rect(hitbox.x + hitbox.w//2 - 20, hitbox.y + hitbox.h, 40, 5)
            for box in boxes:
                if self.vel_y >= 0:
                    if sdl2.SDL_HasIntersection(feet_rect, box.rect):
                        align_y = box.rect.y - offset_y - hitbox.h
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
        if self.is_jumping and self.vel_y == 0: self.vel_y = self.gravity

        # Auto-set jump/fall state if airborne (with post-cast guard)
        # Decrement guard timer each frame
        if hasattr(self, '_post_cast_guard') and self._post_cast_guard > 0:
            self._post_cast_guard -= 1
        
        # Only auto-transition to fall/jump_up if not in protected states AND guard expired
        if self.is_jumping and self.state not in ['dead', 'hurt', 'casting_q', 'casting_w', 'dashing_e', 'attacking']:
            guard_active = (self.state == 'idle' and getattr(self, '_post_cast_guard', 0) > 0)
            if not guard_active:
                new_state = 'jump_up' if self.vel_y < 0 else 'fall'
                if self.state != new_state:
                    print(f"[Q DEBUG] Auto-transition: {self.state} → {new_state}, "
                          f"is_jumping={self.is_jumping}, vel_y={self.vel_y:.1f}, guard={getattr(self, '_post_cast_guard', 0)}")
                self.state = new_state

        if self.state == 'hurt':
            self.hurt_timer += dt
            if self.hurt_timer >= PLAYER_HURT_DURATION: self.state = 'idle'
        
        self.anim_timer += dt
        if self.flash_timer > 0: self.flash_timer -= dt

        # 3. Animation Selection
        current_anims = self.anims_right if self.facing_right else self.anims_left
        frames = []
        
        if self.state == 'dead': frames = current_anims.get('dead', current_anims.get('idle', []))
        elif self.state == 'hurt': frames = current_anims.get('hurt', current_anims.get('idle', []))
        elif self.state == 'casting_q': frames = current_anims.get('q', [])
        elif self.state == 'casting_w': frames = current_anims.get('w', [])
        elif self.state == 'dashing_e': frames = current_anims.get('e', [])
        elif self.state == 'attacking': frames = current_anims.get('attack_normal', current_anims.get('idle', []))
        elif self.is_blocking: frames = current_anims.get('block', current_anims.get('idle', []))
        elif self.state == 'run': frames = current_anims.get('run', current_anims.get('idle', []))
        elif self.state == 'walk': frames = current_anims.get('walk', current_anims.get('idle', []))
        
        # Cơ chế Fallback Đa Hình (Polymorphism):
        # Nếu là Leaf Ranger: Ưu tiên lấy 'jump_up' / 'fall'
        # Nếu là Yasuo (không có jump_up): Tự động lùi về lấy ảnh 'jump' mặc định
        elif self.state == 'jump_up': frames = current_anims.get('jump_up', current_anims.get('jump', current_anims.get('idle', [])))
        elif self.state == 'fall': frames = current_anims.get('fall', current_anims.get('jump', current_anims.get('idle', [])))
        else: frames = current_anims.get('idle', [])

        # Safety check: If frames are missing for skill casting states, force return to idle
        if not frames:
            if self.state in ['casting_q', 'casting_w', 'dashing_e', 'attacking']:
                print(f"[ANIMATION ERROR] Missing frames for state '{self.state}', forcing idle")
                self.state = 'idle'
                self.frame_index = 0
                # Try to get idle frames as fallback
                frames = current_anims.get('idle', [])
                if not frames:
                    return  # Critical failure - no idle frames either
            else:
                return

        if self.state != self.prev_state:
            self.frame_index = 0
            sprite_w = self.sprite.size[0] if self.sprite else 0
            sprite_h = self.sprite.size[1] if self.sprite else 0
            print(f"[STATE CHANGE] {self.prev_state} → {self.state}, Current sprite: ({sprite_w}×{sprite_h}), Frames available: {len(frames)}")
            self.prev_state = self.state

        speed = 0.05 if self.state == 'attacking' else self.anim_speed
        
        if self.anim_timer >= speed:
            self.anim_timer = 0
            self.frame_index += 1
            if self.frame_index >= len(frames):
                # Set guard BEFORE state change so it's active when physics runs next frame
                if self.state == 'casting_q':
                    self._post_cast_guard = 3  # 3 frames to ensure protection
                    sprite_w = self.sprite.size[0] if self.sprite else 0
                    sprite_h = self.sprite.size[1] if self.sprite else 0
                    print(f"[Q DEBUG] Animation End: casting_q → idle, sprite_size=({sprite_w},{sprite_h})")
                    self.on_cast_q_complete(world, factory, renderer)
                    self.state = 'idle'
                elif self.state == 'casting_w':
                    self.on_cast_w_complete(world, factory, renderer)
                    self.state = 'idle'
                elif self.state == 'dashing_e':
                    if hasattr(self, 'skill_e') and self.skill_e and not getattr(self.skill_e, 'is_dashing', False): 
                        self.on_cast_e_complete(world, factory, renderer)
                        self.state = 'idle'
                elif self.state == 'attacking': 
                    self.on_attack_complete(world, factory, renderer)
                    self.state = 'idle'
                elif self.state == 'dead': 
                    self.frame_index = len(frames) - 1
                    self.dead_animation_complete = True
                    return
                self.frame_index = 0

        idx = self.frame_index % len(frames)
        if self.entity.sprite:
            old_pos = self.entity.sprite.position
            old_height = self.entity.sprite.size[1]
            old_width = self.entity.sprite.size[0]
            old_state = self.state
            self.entity.sprite = frames[idx]
            new_height = self.entity.sprite.size[1]
            new_width = self.entity.sprite.size[0]
            
            # Debug log sprite size changes
            if old_width != new_width or old_height != new_height:
                print(f"[SPRITE SIZE] State={old_state}, Frame={self.frame_index}/{len(frames)}: "
                      f"({old_width}×{old_height}) → ({new_width}×{new_height})")
            
            # Adjust Y position to keep feet at same position when sprite size changes
            # (sprites are positioned by top-left, so larger sprites would sink down)
            y_adjust = old_height - new_height
            self.entity.sprite.position = (old_pos[0], old_pos[1] + y_adjust)

    # ================= HOOKS CHO CLASS CON OVERRIDE =================
    def on_cast_q_complete(self, world, factory, renderer):
        """Logic tung skill Q sau khi kết thúc animation (Tornado / Laser)"""
        if self.sound_manager: self.sound_manager.play_sound("player_q2")

    def on_cast_w_complete(self, world, factory, renderer):
        """Logic tung skill W (Tường gió / Kích hoạt Buff)"""
        if self.sound_manager: self.sound_manager.play_sound("player_w2")

    def on_cast_e_complete(self, world, factory, renderer):
        """Logic kết thúc lướt E"""
        if self.sound_manager: self.sound_manager.play_sound("player_e2")
        
    def on_attack_complete(self, world, factory, renderer):
        """Logic khi đánh thường kết thúc (Ví dụ bắn cung cho Player 2)"""
        pass

    # ================= ACTIONS CƠ BẢN =================
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

    def attack(self):
        # [FIX] Bổ sung 'jump_up' và 'fall' vào danh sách cho phép đánh
        if self.state in ['idle', 'run', 'walk', 'jump_up', 'fall'] and not self.is_blocking:
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

    # ================= SKILL & UPGRADE =================
    def get_skill_cooldown(self, skill_key):
        base_cd = 0
        if skill_key == 'q': base_cd = SKILL_Q_COOLDOWN
        elif skill_key == 'w': base_cd = SKILL_W_COOLDOWN
        elif skill_key == 'e': base_cd = SKILL_E_COOLDOWN
        elif skill_key == 'a': base_cd = ATTACK_COOLDOWN
        
        level = self.skill_levels.get(skill_key, 0)
        current_cd = base_cd
        
        from settings import SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN, FPS
        for _ in range(level):
            reduction = max(current_cd * SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN * FPS)
            current_cd -= reduction
            
        return max(0.0, current_cd)

    def get_skill_damage_scale(self, skill_key):
        level = self.skill_levels.get(skill_key, 0)
        return SKILL_DAMAGE_GROWTH ** level

    def upgrade_skill(self, skill_key):
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
            
            if skill_key == 'q' and self.skill_q: self.skill_q.update_stats(next_lvl)
            elif skill_key == 'w' and self.skill_w: self.skill_w.update_stats(next_lvl)
            elif skill_key == 'e' and self.skill_e: self.skill_e.update_stats(next_lvl)
            elif skill_key == 'a': self.update_stats()
            
            print(f"[Upgrade] Upgraded {skill_key.upper()} to Level {next_lvl} for {cost} Gold.")
            return True
        else:
            print(f"[Upgrade] Not enough gold! Need {cost}, have {self.gold}.")
            return False

    def can_upgrade_skill(self, skill_key):
        if skill_key not in self.skill_levels: return False
        current_lvl = self.skill_levels[skill_key]
        if current_lvl >= SKILL_MAX_LEVEL:
            return False
        next_lvl = current_lvl + 1
        cost = SKILL_UPGRADE_COSTS.get(next_lvl, 999)
        return self.gold >= cost

    # ================= INVENTORY =================
    def collect_item(self, item_type):
        category = ITEM_REGISTRY.get(item_type)
        if category == ItemCategory.CURRENCY:
            self.gold += 1 
            print(f"[Player] Gold: {self.gold}")
        elif category == ItemCategory.CONSUMABLE:
            if len(self.consumables) >= self.max_consumables:
                removed = self.consumables.pop(0)
                print(f"[Player] Inventory Full! Drop {removed}")
            self.consumables.append(item_type)
            print(f"[Player] Added Consumable: {item_type.name}")
        elif category == ItemCategory.EQUIPMENT:
            if len(self.equipment) >= self.max_equipments:
                removed = self.equipment.pop(0)
                print(f"[Player] Equipment Full! Lost {removed}")
            self.equipment.append(item_type)
            self.recalculate_stats()
            print(f"[Player] Equipped: {item_type.name}")

    def use_consumable(self, slot_index):
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
            print("Used Health Potion")
        elif item_type == ItemType.HOURGLASS:
            self.activate_star_skill(duration=3.0)
            print("Used Hourglass")

    def recalculate_stats(self):
        self.move_speed_bonus = 0
        self.lifesteal_ratio = self.base_lifesteal
        self.damage_reduction = 0.0
        self.armor = self.base_armor
        self.max_stamina = PLAYER_MAX_STAMINA
        
        for item in self.equipment:
            if item == ItemType.GREAVES:
                self.move_speed_bonus += 50
            elif item == ItemType.BLOODTHIRSTER:
                self.lifesteal_ratio += 0.10
                self.attack_damage += 10
            elif item == ItemType.INFINITY_EDGE:
                pass
            elif item == ItemType.THORNMAIL:
                self.armor += 10
                self.damage_reduction += 0.05 

        self.stamina = min(self.stamina, self.max_stamina)
        self.update_stats()

    # ================= NETWORK & SAVE/LOAD =================
    def get_network_state(self) -> dict:
        # State đã có jump_up/fall cho Leaf Ranger (set tự động bởi base_char.update)
        # Yasuo không dùng base_char nên không ảnh hưởng
        return {
            'x':           self.x,
            'y':           self.y,
            'vel_y':       self.vel_y,
            'facing_right': self.facing_right,
            'state':       self.state,
            'hp':          self.hp,
            'stamina':     self.stamina,
            'frame_index': self.frame_index,
            'ts':          time.monotonic(),
            'is_jumping':  self.is_jumping,
        }

    def apply_network_state(self, data: dict):
        if not data: return
        if self.entity.sprite:
            self.entity.sprite.x = int(data.get('x', self.x))
            self.entity.sprite.y = int(data.get('y', self.y))
        self.vel_y           = data.get('vel_y', self.vel_y)
        self.facing_right    = data.get('facing_right', self.facing_right)
        self.state           = data.get('state', self.state)
        self.hp              = data.get('hp', self.hp)
        self.stamina         = data.get('stamina', self.stamina)

    def get_save_data(self):
        return {
            'x': self.x, 
            'y': self.y,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'stamina': self.stamina,
            'max_stamina': self.max_stamina,
            'gold': self.gold,
            'consumables': copy.deepcopy(self.consumables),
            'equipment': copy.deepcopy(self.equipment),
            'attack_damage': self.attack_damage,
            'armor': self.armor,
            'move_speed_bonus': self.move_speed_bonus,
            'lifesteal_ratio': self.lifesteal_ratio
        }
    
    def load_save_data(self, data, spawn_x, spawn_y):
        if not data: return
        if self.entity.sprite:
            self.entity.sprite.x = spawn_x
            self.entity.sprite.y = spawn_y
        self.ground_y = spawn_y
        self.vel_y = 0
        self.hp = data['hp']
        self.max_hp = data['max_hp']
        self.stamina = data['stamina']
        self.max_stamina = data['max_stamina']
        self.gold = data['gold']
        self.consumables = copy.deepcopy(data['consumables'])
        self.equipment = copy.deepcopy(data['equipment'])
        self.attack_damage = data['attack_damage']
        self.armor = data['armor']
        self.move_speed_bonus = data['move_speed_bonus']
        self.lifesteal_ratio = data['lifesteal_ratio']
        self.state = 'idle'
        self.is_blocking = False
        self.dead_animation_complete = False
        print(f"[SYSTEM] Player respawned at Checkpoint with {self.hp} HP")

    def respawn_penalty(self, spawn_x, spawn_y):
        print(f"[SYSTEM] Respawning at Checkpoint ({spawn_x}, {spawn_y})...")
        if self.entity.sprite:
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
        old_gold = self.gold
        self.gold = int(old_gold * 0.7)
        self.consumables = []
        self.equipment = []
        self.recalculate_stats()
        print(f"[PENALTY] Gold: {old_gold} -> {self.gold}. Inventory Cleared.")
    
    def reset_to_default(self, start_x, start_y):
        if self.entity.sprite:
            self.entity.sprite.x = start_x
            self.entity.sprite.y = start_y
        self.vel_y = 0
        self.hp = self.max_hp
        self.stamina = self.max_stamina
        self.gold = int(self.gold * 0.5)
        self.consumables = []
        self.equipment = []
        self.recalculate_stats()
        self.state = 'idle'
        self.dead_animation_complete = False
        self.is_blocking = False
        self.color_mod = (255, 255, 255)

    def draw_debug_rect(self, renderer, rect, camera_x, camera_y, color=(255, 0, 0)):
        sdl2.SDL_SetRenderDrawColor(renderer, color[0], color[1], color[2], 255)
        
        debug_rect = sdl2.SDL_Rect(
            int(rect.x - camera_x),
            int(rect.y - camera_y),
            int(rect.w),
            int(rect.h)
        )
        
        sdl2.SDL_RenderDrawRect(renderer, debug_rect)