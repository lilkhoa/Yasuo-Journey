import sys
import os
import sdl2
import sdl2.ext
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from entities.base_char import BaseChar
from entities.leaf_ranger_projectile import PoisonProjectile, PlantProjectile, HealDustProjectile, NormalArrowProjectile
from combat.player_2.refactored_skill_q import SkillQLaser, update_q_laser_logic, load_laser_cast_animation, load_laser_projectile_frames
from combat.player_2.refactored_skill_w import SkillW
from combat.player_2.refactored_skill_e import SkillE, load_arrow_rain_cast_animation, update_e_aoe_logic
from combat.utils import load_image_sequence, flip_sprites_horizontal
from settings import SKILL_W_BUFF_DURATION, SKILL_W_COST, SKILL_E_2_COST, SKILL_E_2_COOLDOWN, SKILL_DAMAGE_GROWTH

class LeafRanger(BaseChar):
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        super().__init__(world, factory, x, y, sound_manager, renderer_ptr)
        
        # Đặc trưng nhân vật: Lớn hơn 35%
        self.scale_factor = 1.5
        
        # --- THUỘC TÍNH W BUFF (Toxin Enhancement) ---
        self.w_buff_active = False
        self.w_buff_timer = 0
        self.w_attack_toggle = False  # False = Độc, True = Gai
        self.w_poison_applied = {}
        
        # --- QUẢN LÝ OBJECT SKILL RIÊNG ---
        self.active_lasers = []
        self.e_aoe = None
        
        # --- TÚI ĐỒ (Inventory System Overrides) ---
        self.inventory = None
        self.dropped_item_net_id = None
        
        # --- KHỞI TẠO BỘ SKILL ---
        self.skill_q = SkillQLaser(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)
        
        self.skills = [self.skill_q, self.skill_w, self.skill_e, None, None]
        
        # Tải đồ họa
        self._load_animations(factory)
        
        if self.anims_right['idle']:
            self.entity.sprite = self.anims_right['idle'][0]
            self.entity.sprite.position = x, y

        # Cờ để không spawn chiêu nhiều lần trong 1 vòng animation
        self._laser_spawned = False
        self._e_spawned = False

    def _load_animations(self, factory):
        player2_dir = os.path.join(root_dir, 'assets', 'Player_2')
        
        # [MỚI] Bổ sung tham số crop_box (x, y, w, h)
        def load_scaled_sequence(folder, prefix, count, scale=1.35, crop_box=None):
            frames = []
            for i in range(1, count + 1):
                file_path = os.path.join(player2_dir, folder, f"{prefix}{i}.png")
                if not os.path.exists(file_path):
                    continue
                try:
                    surf_ptr = sdl2.ext.load_image(file_path)
                    
                    # Xử lý Cắt (Crop) nếu có truyền crop_box
                    if crop_box:
                        cx, cy, cw, ch = crop_box
                        src_rect = sdl2.SDL_Rect(cx, cy, cw, ch)
                    else:
                        orig_w = surf_ptr.w if hasattr(surf_ptr, 'w') else surf_ptr.contents.w
                        orig_h = surf_ptr.h if hasattr(surf_ptr, 'h') else surf_ptr.contents.h
                        src_rect = sdl2.SDL_Rect(0, 0, orig_w, orig_h)
                        
                    new_w = int(src_rect.w * scale)
                    new_h = int(src_rect.h * scale)
                    
                    rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
                    if sys.byteorder == 'big':
                        rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff
                        
                    scaled_surf = sdl2.SDL_CreateRGBSurface(0, new_w, new_h, 32, rmask, gmask, bmask, amask)
                    sdl2.SDL_SetSurfaceBlendMode(surf_ptr, sdl2.SDL_BLENDMODE_NONE)
                    
                    dst_rect = sdl2.SDL_Rect(0, 0, new_w, new_h)
                    # Lệnh BlitScaled giờ sẽ chỉ lấy phần diện tích src_rect đã được cắt
                    sdl2.SDL_BlitScaled(surf_ptr, src_rect, scaled_surf, dst_rect)
                    
                    sprite = factory.from_surface(scaled_surf)
                    frames.append(sprite)
                    sdl2.SDL_FreeSurface(surf_ptr)
                except Exception as e:
                    print(f"[LỖI] Scale ảnh {file_path}: {e}")
            return frames

        # Khung chuẩn chung (Universal Box) tính toán từ số đo của bạn
        universal_crop = (117, 45, 77, 83)

        self.anims_right['idle'] = load_scaled_sequence('idle', 'idle_', 12, self.scale_factor, universal_crop)
        self.anims_right['run']  = load_scaled_sequence('run', 'run_', 10, self.scale_factor, universal_crop)
        self.anims_right['walk'] = [frame for frame in self.anims_right['run'] for _ in range(1)]
        
        self.anims_right['attack_normal'] = load_scaled_sequence('normal_attack', '2_atk_', 10, self.scale_factor, universal_crop)
        self.anims_right['block'] = load_scaled_sequence('defend', 'defend_', 19, self.scale_factor, universal_crop)
        
        self.anims_right['jump_up'] = load_scaled_sequence('jump_up', 'jump_up_', 3, self.scale_factor, universal_crop)
        self.anims_right['fall'] = load_scaled_sequence('jump_down', 'jump_down_', 3, self.scale_factor, universal_crop)
        # self.anims_right['jump'] = load_scaled_sequence('jump_full', 'jump_', 22, self.scale_factor, universal_crop)
        self.anims_right['dead'] = load_scaled_sequence('death', 'death_', 19, self.scale_factor, universal_crop)
        self.anims_right['hurt'] = load_scaled_sequence('take_hit', 'take_hit_', 6, self.scale_factor, universal_crop)

        if not self.anims_right['idle']: 
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(0, 255, 0), (40, 60))]

        # Load Skill Assets (Các chiêu thức Q, E riêng của Player 2 giữ nguyên size của ảnh gốc)
        _skill_asset_dir = os.path.join(root_dir, 'assets', 'Skills')
        _proj_asset_dir  = os.path.join(root_dir, 'assets', 'Projectile')
        
        self.laser_cast_frames = load_laser_cast_animation(factory, _skill_asset_dir)
        self.laser_projectile_frames = load_laser_projectile_frames(factory, _proj_asset_dir)
        self.e_casting_frames = load_arrow_rain_cast_animation(factory, _skill_asset_dir)
        
        self.anims_right['q'] = self.laser_cast_frames
        
        # W là chiêu đánh trên không
        w_folder = os.path.join(_skill_asset_dir, "skill_w_2")
        self.anims_right['w'] = load_image_sequence(factory, w_folder, "air_atk_", 10, (150, 150), zero_pad=True)
        
        self.anims_right['e'] = self.e_casting_frames

        # Tự lật ảnh cho hướng trái
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

    def get_hitbox(self):
        """
        Ghi đè Hitbox mặc định của BaseChar.
        Mục đích: Không tính phần áo choàng bay phía trên vào khung chịu đòn.
        """
        import sdl2
        scale = self.scale_factor
        
        # 1. Định nghĩa kích thước "Da thịt" thật của Leaf Ranger
        # (Yasuo mặc định là 40x80, ta giảm chiều cao xuống để trừ hao cái áo choàng)
        hitbox_w = int(35 * scale)  # Ôm sát thân người hơn
        hitbox_h = int(60 * scale)  # Chiều cao thấp hơn, chỉ tới đỉnh đầu
        
        # Lấy kích thước của khung ảnh đang render
        sprite_w = self.width if self.entity.sprite else int(77 * scale)
        sprite_h = self.height if self.entity.sprite else int(83 * scale)
        
        # 2. Căn chỉnh vị trí (Offsets)
        # Đứng giữa khung ảnh theo trục X
        offset_x = (sprite_w - hitbox_w) // 2
        
        # Ép đáy của Hitbox bằng đúng gót chân (đáy của bức ảnh)
        # Như vậy phần bị gọt bỏ đi sẽ nằm hoàn toàn ở phía trên (phần áo choàng)
        offset_y = sprite_h - hitbox_h
        
        return sdl2.SDL_Rect(int(self.x + offset_x), int(self.y + offset_y), hitbox_w, hitbox_h)

    # # ================= HOOKS DI CHUYỂN =================
    # def handle_movement(self, keys):
    #     if self.is_blocking or self.state in ['casting_q', 'casting_w', 'dashing_e', 'attacking', 'dead', 'hurt']:
    #         return
        
    #     super().handle_movement(keys)
        
    #     # Map chi tiết state ở trên không trung
    #     if self.is_jumping:
    #         if self.vel_y < 0:
    #             self.state = 'jump_up'
    #         else:
    #             self.state = 'fall'

    # ================= KHỞI TẠO KÍCH HOẠT =================
    def start_w(self, direction=0):
        if self.stamina < SKILL_W_COST or not self.cooldowns.is_ready("skill_w"): return
        # [FIX] Bổ sung trạng thái nhảy
        if self.state in ['idle', 'run', 'walk', 'jump_up', 'fall']:
            self.stamina -= SKILL_W_COST
            cd = self.get_skill_cooldown('w')
            self.cooldowns.start_cooldown("skill_w", cd)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_w'
            self.frame_index = 0
            if self.sound_manager:
                try: self.sound_manager.play_sound("player_w1")
                except: pass

    def start_q(self, direction=0):
        if self.stamina < 20 or not self.cooldowns.is_ready("skill_q"): return
        # [FIX] Bổ sung trạng thái nhảy
        if self.state in ['idle', 'run', 'walk', 'jump_up', 'fall']:
            self.stamina -= 20
            cd = self.get_skill_cooldown('q')
            self.cooldowns.start_cooldown("skill_q", cd)
            if direction: self.facing_right = (direction > 0)
            self.state = 'casting_q'
            self.frame_index = 0
            self._laser_spawned = False
            if self.sound_manager:
                try: self.sound_manager.play_sound("player_q1")
                except: pass

    def start_e(self, world=None, factory=None, renderer=None, direction=0):
        if self.stamina < SKILL_E_2_COST or not self.cooldowns.is_ready("skill_e"): return
        # [FIX] Bổ sung trạng thái nhảy
        if self.state in ['idle', 'run', 'walk', 'jump_up', 'fall']:
            self.stamina -= SKILL_E_2_COST
            cd = self.get_skill_cooldown('e')
            self.cooldowns.start_cooldown("skill_e", cd)
            if direction: self.facing_right = (direction > 0)
            
            self.state = 'dashing_e'
            self.skill_e.is_dashing = True # Khóa không cho thoát state
            self.frame_index = 0
            self._e_spawned = False
            if self.sound_manager:
                try: self.sound_manager.play_sound("player_e1")
                except: pass

    # ================= HOOKS KHI ANIMATION KẾT THÚC =================
    def on_cast_q_complete(self, world, factory, renderer):
        if not getattr(self, '_laser_spawned', False):
            self.spawn_laser(world, factory, renderer)
        self._laser_spawned = False
        if self.sound_manager:
            try: self.sound_manager.play_sound("player_q2")
            except: pass

    def on_cast_w_complete(self, world, factory, renderer):
        self.spawn_w_buff()
        if self.sound_manager:
            try: self.sound_manager.play_sound("player_w2")
            except: pass
            
    def on_cast_e_complete(self, world, factory, renderer):
        # Mưa tên đã được gọi giữa chừng (trong update), ở đây chỉ để bắt event hết hoạt ảnh
        pass

    # ================= LOGIC SINH CHIÊU =================
    def spawn_w_buff(self):
        self.skill_w.execute(None, None, None)
        
    def spawn_laser(self, world, factory, renderer):
        sprites = self.laser_projectile_frames
        if not sprites:
            sprites = [factory.from_color(sdl2.ext.Color(255, 255, 0), size=(800, 80))]
        laser = self.skill_q.execute(world, factory, renderer, skill_sprites=sprites)
        if laser:
            self.active_lasers.append(laser)

    def spawn_e_aoe(self, renderer, game_map=None):
        if self.skill_e is None: return
        aoe = self.skill_e.execute(renderer, game_map)
        if aoe:
            self.e_aoe = aoe

    # ================= VÒNG LẶP UPDATE =================
    def update(self, dt, world, factory, renderer, game_map=None, boxes=None):
        # 1. Bắn Laser ở frame thứ 9
        if self.state == 'casting_q':
            if self.frame_index >= 9 and not getattr(self, '_laser_spawned', False):
                self.spawn_laser(world, factory, renderer)
                self._laser_spawned = True
                
        # 2. Gọi mưa tên ở frame thứ 6
        if self.state == 'dashing_e':
            if self.frame_index >= 6 and not getattr(self, '_e_spawned', False):
                self.spawn_e_aoe(renderer, game_map)
                self._e_spawned = True
                
        # Update vật lý, máu, va chạm từ BaseChar
        super().update(dt, world, factory, renderer, game_map, boxes)
        
        # 3. Phá khóa animation khi E chạy hết frame
        if self.state == 'dashing_e' and getattr(self.skill_e, 'is_dashing', False):
            e_frames = self.anims_right.get('e', [])
            if e_frames and self.frame_index == len(e_frames) - 1:
                self.skill_e.is_dashing = False 
                
        # 4. Tính toán thời gian Buff W
        if self.w_buff_active:
            self.skill_w.update_buff(dt)
            if not self.w_buff_active:
                self.w_attack_toggle = False
                self.w_poison_applied.clear()

    # ================= VÒNG LẶP SKILL & RENDER =================
    def update_skills(self, dt, enemies, projectiles=None, network_ctx=None):
        for laser in self.active_lasers[:]:
            update_q_laser_logic(laser, enemies, dt, network_ctx)
            if not laser.active:
                laser.delete()
                self.active_lasers.remove(laser)
        
        if self.e_aoe is not None and self.e_aoe.active:
            update_e_aoe_logic(self.e_aoe, enemies, dt, network_ctx)
        elif self.e_aoe is not None and not self.e_aoe.active:
            self.e_aoe = None

    def render_skills(self, renderer, camera):
        for laser in self.active_lasers:
            if not hasattr(laser, 'sprites') or not laser.sprites: continue
            sprite = laser.sprites[laser.anim_frame % len(laser.sprites)]
            if not hasattr(sprite, 'surface') or not sprite.surface: continue
            
            surface = sprite.surface
            texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
            if texture:
                if laser.direction > 0:
                    render_x = int(laser.x - camera.camera.x)
                else:
                    render_x = int(laser.x - laser.max_range - camera.camera.x)
                dst_rect = sdl2.SDL_Rect(
                    render_x,
                    int(laser.y - camera.camera.y),
                    surface.w, surface.h
                )
                sdl2.SDL_RenderCopy(renderer, texture, None, dst_rect)
                sdl2.SDL_DestroyTexture(texture)
        
        if self.e_aoe is not None and self.e_aoe.active:
            # Sửa lỗi mismatch renderer
            if self.e_aoe.renderer != renderer:
                self.e_aoe.renderer = renderer
            self.e_aoe.render(camera.camera.x, camera.camera.y)

    # ================= OVERRIDE TẤN CÔNG (PROJECTILES) =================
    def spawn_attack_projectile(self, renderer, projectile_manager, network_ctx=None):
        direction = 1 if self.facing_right else -1
        proj_x = self.sprite.x + (50 * direction)
        proj_y = self.sprite.y + 70  # <--- Tăng giảm con số 40 này để chỉnh độ cao mũi tên bắn ra
        
        if self.w_buff_active:
            if self.vel_y != 0:
                projectile = HealDustProjectile(proj_x, proj_y, direction, self, renderer)
                projectile_manager.add_projectile(projectile)
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        try: game_client.send_skill_event('attack_w_heal', direction, proj_x, proj_y)
                        except: pass
            else:
                if not self.w_attack_toggle:
                    projectile = PoisonProjectile(proj_x, proj_y, direction, self, renderer, damage_multiplier=self.get_skill_damage_scale('a'))
                    action = 'attack_w_poison'
                else:
                    projectile = PlantProjectile(proj_x, proj_y, direction, self, renderer)
                    action = 'attack_w_plant'
                
                projectile_manager.add_projectile(projectile)
                self.w_attack_toggle = not self.w_attack_toggle
                
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        try: game_client.send_skill_event(action, direction, proj_x, proj_y)
                        except: pass
        else:
            projectile = NormalArrowProjectile(proj_x, proj_y, direction, self, renderer)
            projectile_manager.add_projectile(projectile)
            action = 'attack_normal'
            if network_ctx:
                is_multi, is_host, game_client = network_ctx
                if is_multi and game_client and game_client.is_connected():
                    try: game_client.send_skill_event(action, direction, proj_x, proj_y)
                    except: pass

    def apply_poison_damage(self, target, damage, tick_rate, duration):
        target_id = getattr(target, 'net_id', id(target))
        current_time = time.time()
        if target_id not in self.w_poison_applied:
            self.w_poison_applied[target_id] = current_time
            if hasattr(target, 'apply_poison'):
                target.apply_poison(duration, tick_rate, damage)
            
        def cleanup_poison(tid):
            if tid in self.w_poison_applied:
                del self.w_poison_applied[tid]

    # ================= QUẢN LÝ DROP ITEM MẠNG LƯỚI =================
    def add_item_to_inventory(self, item_type):
        self.inventory = item_type

    def drop_item(self, game_client=None):
        if self.inventory is None: return None
        dropped_type = self.inventory
        
        if game_client and game_client.is_connected():
            from items.item import DroppedItem
            item_net_id = DroppedItem._next_net_id
            DroppedItem._next_net_id += 1
            event = {
                "type": "ITEM_DROPPED",
                "player_id": game_client.player_id,
                "item_type": dropped_type.value,
                "x": self.x,
                "y": self.y,
                "item_net_id": item_net_id,
            }
            game_client._enqueue(event)
            self.dropped_item_net_id = item_net_id
            
        self.inventory = None
        return dropped_type

    def die(self):
        self.w_buff_active = False
        self.w_poison_applied.clear()
        super().die()