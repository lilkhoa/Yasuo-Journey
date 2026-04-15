"""
Player 2 Class - Enhanced character with Toxin Enhancement W skill
Inherits from Player and overrides W skill to be a buff that modifies normal attacks
"""

import sys
import os
import sdl2
import sdl2.ext
import time

# Add root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)  # .../A3_Yasuo
if root_dir not in sys.path:
    sys.path.append(root_dir)

from entities.player import Player
from entities.player_2_projectile import PoisonProjectile, PlantProjectile, HealDustProjectile, NormalArrowProjectile
from combat.player_2.skill_q import SkillQLaser, update_q_laser_logic, load_laser_cast_animation, load_laser_projectile_frames
from combat.player_2.skill_w import SkillW
from combat.player_2.skill_e import SkillE, load_arrow_rain_cast_animation, update_e_aoe_logic
from settings import SKILL_W_BUFF_DURATION, SKILL_W_COST, SKILL_E_2_COST, SKILL_E_2_COOLDOWN

from combat.utils import load_image_sequence, flip_sprites_horizontal
import os

class Player2(Player):
    """
    Player 2 - The new character with enhanced W skill (Toxin Enhancement).
    
    Inherits all base mechanics from Player.
    Overrides W skill to be a buff that modifies normal attacks:
    - Ground attacks alternate between Poison and Plant projectiles
    - Air attacks spawn healing dust for allies
    - Buff lasts 5 seconds with toggle tracking
    """
    
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        """
        Initialize Player2.
        
        Args:
            world: SDL2 entity world
            factory: Sprite factory
            x, y: Starting position
            sound_manager: Sound manager instance
            renderer_ptr: SDL2 renderer pointer
        """
        super().__init__(world, factory, x, y, sound_manager, renderer_ptr)
        
        # ==========================================
        # STEP 1: OVERRIDE ASSETS AND ANIMATIONS
        # ==========================================
        player2_dir = os.path.join('./assets', 'Player_2')
        def load_scaled_sequence(folder, prefix, count, scale=1.35):
            frames = []
            for i in range(1, count + 1):
                file_path = os.path.join(player2_dir, folder, f"{prefix}{i}.png")
                
                # Bắt lỗi: Nếu file không tồn tại, bỏ qua frame này thay vì crash game
                if not os.path.exists(file_path):
                    print(f"[CẢNH BÁO] Thiếu ảnh: {file_path}")
                    continue
                
                try:
                    surf_ptr = sdl2.ext.load_image(file_path)
                    
                    # Tương thích lấy kích thước (PySDL2 versions)
                    orig_w = surf_ptr.w if hasattr(surf_ptr, 'w') else surf_ptr.contents.w
                    orig_h = surf_ptr.h if hasattr(surf_ptr, 'h') else surf_ptr.contents.h
                    
                    # Tính toán kích thước phóng to
                    new_w = int(orig_w * scale)
                    new_h = int(orig_h * scale)
                    
                    # Tạo một Surface trống với kích thước mới (Hỗ trợ Alpha channel / Trong suốt)
                    rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
                    if sys.byteorder == 'big':
                        rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff
                        
                    scaled_surf = sdl2.SDL_CreateRGBSurface(0, new_w, new_h, 32, rmask, gmask, bmask, amask)
                    
                    # Phóng to ảnh gốc dán vào bề mặt mới
                    sdl2.SDL_SetSurfaceBlendMode(surf_ptr, sdl2.SDL_BLENDMODE_NONE)
                    src_rect = sdl2.SDL_Rect(0, 0, orig_w, orig_h)
                    dst_rect = sdl2.SDL_Rect(0, 0, new_w, new_h)
                    
                    sdl2.SDL_BlitScaled(surf_ptr, src_rect, scaled_surf, dst_rect)
                    
                    # Chuyển đổi thành Sprite và lưu vào mảng
                    sprite = factory.from_surface(scaled_surf)
                    frames.append(sprite)
                    
                    # Giải phóng RAM cho ảnh gốc
                    sdl2.SDL_FreeSurface(surf_ptr)
                except Exception as e:
                    print(f"[LỖI] Không thể load hoặc scale ảnh {file_path}: {e}")
                    
            return frames
        
        # --- CÀI ĐẶT ĐỘ LỚN NHÂN VẬT TẠI ĐÂY ---
        # 1.35 nghĩa là to hơn 35%. Bạn có thể đổi thành 1.4 hoặc 1.5 tùy mắt nhìn.
        SCALE_FACTOR = 1.35

        self.anims_right = {}
        
        self.anims_right['idle'] = load_scaled_sequence('idle', 'idle_', 12, SCALE_FACTOR)
        self.anims_right['run']  = load_scaled_sequence('run', 'run_', 10, SCALE_FACTOR)
        self.anims_right['walk'] = [frame for frame in self.anims_right['run'] for _ in range(2)]
        
        self.anims_right['attack_normal'] = load_scaled_sequence('1_atk', '1_atk_', 10, SCALE_FACTOR)
        self.anims_right['block'] = load_scaled_sequence('defend', 'defend_', 19, SCALE_FACTOR)
        self.anims_right['q'] = load_scaled_sequence('2_atk', '2_atk_', 15, SCALE_FACTOR)
        self.anims_right['w'] = load_scaled_sequence('3_atk', '3_atk_', 12, SCALE_FACTOR)
        self.anims_right['e'] = load_scaled_sequence('sp_atk', 'sp_atk_', 17, SCALE_FACTOR)
        
        self.anims_right['jump_up'] = load_scaled_sequence('jump_up', 'jump_up_', 3, SCALE_FACTOR)
        self.anims_right['fall'] = load_scaled_sequence('jump_down', 'jump_down_', 3, SCALE_FACTOR)
        self.anims_right['jump'] = load_scaled_sequence('jump_full', 'jump_', 22, SCALE_FACTOR)
        self.anims_right['roll'] = load_scaled_sequence('roll', 'roll_', 8, SCALE_FACTOR)
        self.anims_right['dead'] = load_scaled_sequence('death', 'death_', 19, SCALE_FACTOR)
        self.anims_right['hurt'] = load_scaled_sequence('take_hit', 'take_hit_', 6, SCALE_FACTOR)

        # Tránh crash nếu thiếu toàn bộ ảnh Idle
        if not self.anims_right['idle']: 
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(0, 255, 0), (40, 60))]

        # Lật ảnh để tạo hoạt ảnh quay trái (hàm flip này chạy tốt trên cả ảnh đã scale)
        self.anims_left = {}
        for key, sprites in self.anims_right.items():
            if sprites:
                self.anims_left[key] = flip_sprites_horizontal(factory, sprites)
            else:
                self.anims_left[key] = []

        # Set ảnh đứng im mặc định và tạo vị trí
        self.entity.sprite = self.anims_right['idle'][0]
        self.entity.sprite.position = x, y
        # ==========================================

        # ==========================================
        # STEP 2: OVERRIDE SKILL OBJECTS
        # ==========================================
        # W Skill buff state management
        self.w_buff_active = False
        self.w_buff_timer = 0  # Timestamp when buff was activated
        self.w_attack_toggle = False  # False = Poison, True = Plant
        
        # Override Q skill with Laser (replaces parent's SkillQ tornado)
        self.skill_q = SkillQLaser(self)
        
        # Pre-load laser assets for Q skill
        _skill_asset_dir = os.path.join(root_dir, 'assets', 'Skills')
        _proj_asset_dir  = os.path.join(root_dir, 'assets', 'Projectile')
        self.laser_cast_frames     = load_laser_cast_animation(factory, _skill_asset_dir)
        self.laser_projectile_frames = load_laser_projectile_frames(factory, _proj_asset_dir)
        
        # Active laser list (mirrors active_tornadoes for Yasuo)
        self.active_lasers = []
        
        # Create W skill instance (replaces parent's SkillW)
        self.skill_w = SkillW(self)
        
        # Poison tracking (optional DoT management)
        self.w_poison_applied = {}  # target_id -> timestamp of last poison application
        
        # Create E skill instance for Arrow Rain
        self.skill_e = SkillE(self)
        # Pre-load E casting animation
        self.e_casting_frames = load_arrow_rain_cast_animation(factory, _skill_asset_dir)
        self.e_aoe = None  # Current active AoE (if any)
        
        # --- SKILLS LIST FOR HUD (Player 2 Override) ---
        self.skills = [
            self.skill_q,  # Index 0 - Q key
            self.skill_w,  # Index 1 - W key
            self.skill_e,  # Index 2 - E key
            None,          # Index 3 - R key (reserved)
            None           # Index 4 - A/S key (reserved)
        ]
        
        # --- INVENTORY SYSTEM FOR PLAYER2 ---
        # Store active inventory item(s)
        # In this implementation, support both single item and list for future expansion
        self.inventory = None  # Currently holds: None or ItemType
        self.dropped_item_net_id = None  # Track dropped item for network sync
    
    def update_skills(self, dt, enemies, network_ctx=None):
        """
        Polymorphic skill update method for Player2.
        Updates active Q lasers and the E arrow-rain AoE.
        
        Args:
            dt: Delta time
            enemies: List of enemy entities for collision
            network_ctx: Network context (is_multi, is_host, game_client) or None
        """
        # --- Q Laser update ---
        for laser in self.active_lasers[:]:
            update_q_laser_logic(laser, enemies, dt, network_ctx)
            if not laser.active:
                laser.delete()
                self.active_lasers.remove(laser)
        
        # --- E Arrow Rain AoE update ---
        if self.e_aoe is not None and self.e_aoe.active:
            update_e_aoe_logic(self.e_aoe, enemies, dt, network_ctx)
        elif self.e_aoe is not None and not self.e_aoe.active:
            self.e_aoe = None  # Cleanup reference once AoE expires

    def render_skills(self, renderer, camera):
        """
        Polymorphic skill render method for Player2.
        Renders active Q laser beams and E arrow-rain AoE.
        
        Args:
            renderer: SDL2 renderer  (raw sdlrenderer pointer)
            camera: Camera object for coordinate transformation
        """
        import sdl2
        
        # --- Render active Q lasers ---
        for laser in self.active_lasers:
            if not hasattr(laser, 'sprites') or not laser.sprites:
                continue
            sprite = laser.sprites[laser.anim_frame % len(laser.sprites)]
            if not hasattr(sprite, 'surface') or not sprite.surface:
                continue
            surface = sprite.surface
            texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
            if texture:
                # For a left-facing laser, render offset by the laser range
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
        
        # --- Render active E AoE ---
        if self.e_aoe is not None and self.e_aoe.active:
            self.e_aoe.render(camera.camera.x, camera.camera.y)
    
    def add_item_to_inventory(self, item_type):
        """
        Add an item to Player2's active inventory.
        
        In network mode, consumables go to inventory.
        Equipment/Currency are applied immediately (inherited behavior).
        
        Args:
            item_type: ItemType enum value
        """
        # Store the item in inventory
        self.inventory = item_type
        print(f"[Player2] Added to Inventory: {item_type.name}")
    
    def drop_item(self, game_client=None):
        """
        Drop the current inventory item at player's position.
        
        Args:
            game_client: GameClient instance for network synchronization
            
        Returns:
            ItemType if successfully dropped, None if inventory empty
        """
        if self.inventory is None:
            print("[Player2] Inventory is empty, nothing to drop")
            return None
        
        dropped_type = self.inventory
        
        # Send network event to server (if multiplayer)
        if game_client and game_client.is_connected():
            # Generate unique item ID for network sync
            from items.item import DroppedItem
            item_net_id = DroppedItem._next_net_id
            DroppedItem._next_net_id += 1
            
            # Notify server about dropped item
            event = {
                "type": "ITEM_DROPPED",
                "player_id": game_client.player_id,
                "item_type": dropped_type.value,  # Convert enum to int
                "x": self.x,
                "y": self.y,
                "item_net_id": item_net_id,
            }
            game_client._enqueue(event)
            self.dropped_item_net_id = item_net_id
        
        # Clear inventory
        self.inventory = None
        print(f"[Player2] Dropped item: {dropped_type.name} at ({self.x:.1f}, {self.y:.1f})")
        
        return dropped_type
    
    def start_w(self, direction=0):
        """
        Override: Activate Toxin Enhancement buff instead of spawning a wall.
        
        Args:
            direction: Direction input (used for facing)
        """
        # Check cooldown and stamina (same as parent)
        if self.stamina < SKILL_W_COST or not self.cooldowns.is_ready("skill_w"):
            return
        
        # Only cast from valid states
        if self.state not in ['idle', 'jumping']:
            return
        
        # Spend stamina and set cooldown
        self.stamina -= SKILL_W_COST
        cd = self.get_skill_cooldown('w')
        self.cooldowns.start_cooldown("skill_w", cd)
        
        # Update facing direction
        if direction:
            self.facing_right = (direction > 0)
        
        # Set state to casting animation
        self.state = 'casting_w'
        self.frame_index = 0
        
        # Play sound
        if self.sound_manager:
            try:
                self.sound_manager.play_sound("player_w1")
            except:
                pass
    
    def spawn_w_buff(self):
        """
        Called when W casting animation completes.
        Activates the Toxin Enhancement buff.
        """
        # Execute the skill (activates buff)
        self.skill_w.execute(None, None, None)  # No projectile spawning
        
        print(f"Player2: Toxin Enhancement activated for {SKILL_W_BUFF_DURATION}s!")
    
    def start_q(self, direction=0):
        """
        Override: Fire a laser beam (Q skill for Player2).
        Animation frame cycling is handled by the parent update() since
        the state 'casting_q' is already there; laser spawning happens
        in spawn_laser() which is called when the cast animation ends.
        """
        if self.stamina < 20 or not self.cooldowns.is_ready("skill_q"):  # 20 stamina = Q cost
            return
        if self.state in ['idle', 'jumping', 'run', 'walk']:
            self.stamina -= 20
            cd = self.get_skill_cooldown('q')
            self.cooldowns.start_cooldown("skill_q", cd)
            if direction:
                self.facing_right = (direction > 0)
            self.state = 'casting_q'
            self.frame_index = 0
            if self.sound_manager:
                try:
                    self.sound_manager.play_sound("player_q1")
                except:
                    pass

    def spawn_laser(self, world, factory, renderer):
        """
        Called when Q casting animation completes.
        Spawns a LaserObject and adds it to active_lasers.
        """
        # Use pre-loaded frames; fall back to coloured rectangle if missing
        sprites = self.laser_projectile_frames
        if not sprites:
            import sdl2.ext as _ext
            sprites = [factory.from_color(_ext.Color(255, 255, 0), size=(800, 80))]
        laser = self.skill_q.execute(world, factory, renderer, skill_sprites=sprites)
        if laser:
            self.active_lasers.append(laser)

    # ── Polymorphic overrides for base Player.update() animation loop ─────────
    # The base Player.update() calls self.spawn_tornado() when the 'casting_q'
    # animation ends, and self.spawn_wall() when 'casting_w' ends.
    # We redirect those calls to Player2-specific logic here.

    def spawn_tornado(self, world, factory, renderer):
        """Override: Q cast done → fire laser instead of tornado."""
        self.spawn_laser(world, factory, renderer)
        if self.sound_manager:
            try:
                self.sound_manager.play_sound("player_q2")
            except Exception:
                pass

    def spawn_wall(self, world, factory, renderer):
        """Override: W cast done → activate toxin buff instead of fire wall."""
        self.spawn_w_buff()
        if self.sound_manager:
            try:
                self.sound_manager.play_sound("player_w2")
            except Exception:
                pass


    def start_e(self, world=None, factory=None, renderer=None, direction=0):
        """
        Activate Arrow Rain skill - spawns AoE at calculated position.
        
        Args:
            world: SDL2 entity world (ignored, for compatibility with Player.start_e signature)
            factory: Sprite factory (ignored, for compatibility)
            renderer: SDL2 renderer (used for asset loading)
            direction: Direction input (used for facing)
        """
        # Check cooldown and stamina
        if self.stamina < SKILL_E_2_COST or not self.cooldowns.is_ready("skill_e"):
            return
        
        # Only cast from valid states
        if self.state not in ['idle', 'jumping']:
            return
        
        # Spend stamina and set cooldown
        self.stamina -= SKILL_E_2_COST
        cd = self.get_skill_cooldown('e')
        self.cooldowns.start_cooldown("skill_e", cd)
        
        # Update facing direction
        if direction:
            self.facing_right = (direction > 0)
        
        # Set state to casting animation
        self.state = 'casting_e'
        self.frame_index = 0
        
        # Play sound
        if self.sound_manager:
            try:
                self.sound_manager.play_sound("player_e1")
            except:
                pass
    
    def spawn_e_aoe(self, renderer):
        """
        Called when E casting animation completes.
        Spawns the Arrow Rain AoE entity and stores it for update/render.
        
        Args:
            renderer: SDL2 renderer
        """
        if self.skill_e is None:
            return
        
        # Execute the skill to spawn AoE; store reference for update_skills/render_skills
        aoe = self.skill_e.execute(renderer)
        if aoe:
            self.e_aoe = aoe
        
        print(f"Player2: Arrow Rain spawned!")
    
    def handle_movement(self, keys):
        """
        Override: Block movement during E skill casting.
        
        Args:
            keys: Keyboard state
        """
        # Block movement during E casting
        if self.is_blocking or self.state in ['casting_q', 'casting_w', 'casting_e', 'dashing_e', 'attacking', 'dead', 'hurt']:
            return
        
        # Call parent's movement handling (velocity, collision) from base class
        super().handle_movement(keys)
        
        # 1. In the air states (Jump & Fall)
        if self.is_jumping:
            if self.vel_y < 0:
                self.state = 'jump_up'
            else:
                self.state = 'fall'
    
    def update(self, dt, world, factory, renderer, game_map=None, boxes=None):
        """
        Override: Call parent update AND manage W buff duration + E AoE casting.
        
        Args:
            dt: Delta time
            world: Entity world
            factory: Sprite factory
            renderer: Renderer
            game_map: Game map for collision
            boxes: Obstacle boxes
        """
        # Call parent update (handles movement, animation, conditions, etc.)
        super().update(dt, world, factory, renderer, game_map, boxes)
        
        # Manage W buff duration
        if self.w_buff_active:
            self.skill_w.update_buff(dt)
            
            # Check if buff expired
            if not self.w_buff_active:
                self.w_attack_toggle = False  # Reset toggle on expiration
                self.w_poison_applied.clear()  # Clear poison tracking
        
        # Manage E casting animation (Arrow Rain)
        if self.state == 'casting_e':
            if self.e_casting_frames:
                self.frame_index += 1
                idx = self.frame_index % len(self.e_casting_frames)
                old_pos = self.sprite.position
                self.sprite = self.e_casting_frames[idx]
                self.sprite.position = old_pos
                
                if self.frame_index >= len(self.e_casting_frames):
                    # Casting complete – spawn AoE
                    self.spawn_e_aoe(renderer)
                    self.state = 'idle'
                    self.frame_index = 0
            else:
                # No casting frames loaded – spawn immediately
                self.spawn_e_aoe(renderer)
                self.state = 'idle'
                self.frame_index = 0
    
    def attack(self):
        """
        Override: Modified normal attack that respects W buff state.
        
        If W buff is active, this spawns special projectiles.
        Otherwise, uses parent's normal attack.
        """
        # Only attack from valid states
        if self.state not in ['idle', 'run', 'walk'] or self.is_blocking:
            return
        
        # Check attack cooldown
        if not self.cooldowns.is_ready("attack"):
            return
        
        # Set state and cooldown
        self.state = 'attacking'
        self.frame_index = 0
        cd = self.get_skill_cooldown('a')
        self.cooldowns.start_cooldown("attack", cd)
        
        # If W buff is active, we'll spawn special projectiles
        # This will be handled in the game loop when animation completes
        # by checking self.w_buff_active in a new spawn_attack_projectile() method
    
    def spawn_attack_projectile(self, renderer, projectile_manager, network_ctx=None):
        """
        Called from game loop when attack animation completes.
        Spawns appropriate projectile based on W buff state.
        
        Args:
            renderer: SDL2 renderer
            projectile_manager: Projectile manager to add projectiles
            network_ctx: Network context tuple (is_multi, is_host, game_client)
        """
        # Projectile spawn position (slightly forward of character)
        direction = 1 if self.facing_right else -1
        proj_x = self.sprite.x + (50 * direction)
        proj_y = self.sprite.y + 20
        
        # If W buff is active, spawn special projectiles
        if self.w_buff_active:
            # Air attack (jumping) → Heal Dust
            if self.vel_y != 0:
                projectile = HealDustProjectile(proj_x, proj_y, direction, self, renderer)
                projectile_manager.add_projectile(projectile)
                
                # Network sync
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        try:
                            game_client.send_skill_event(
                                'attack_w_heal',
                                direction,
                                proj_x,
                                proj_y
                            )
                        except:
                            pass
                
                print("Player2: Heal Dust spawned from air attack")
            
            # Ground attack → Alternate Poison/Plant
            else:
                if not self.w_attack_toggle:  # False = Poison
                    projectile = PoisonProjectile(
                        proj_x, proj_y, direction, self, renderer,
                        damage_multiplier=self.damage_multiplier
                    )
                    action = 'attack_w_poison'
                    print("Player2: Poison projectile spawned")
                
                else:  # True = Plant
                    projectile = PlantProjectile(proj_x, proj_y, direction, self, renderer)
                    action = 'attack_w_plant'
                    print("Player2: Plant projectile spawned")
                
                projectile_manager.add_projectile(projectile)
                
                # Toggle for next shot
                self.w_attack_toggle = not self.w_attack_toggle
                
                # Network sync
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        try:
                            game_client.send_skill_event(action, direction, proj_x, proj_y)
                        except:
                            pass
        
        else:
            # No W buff → Use normal attack (create simple damage hitbox)
            # For now, we'll just log that normal attack occurred
            print("Player2: Normal attack (no W buff active)")
            
            # Optional: Call parent attack logic or spawn normal projectile
            # This would need additional implementation based on how
            # normal attacks are handled in the base Player class
            
            # [NEW] No W buff active -> Spawn Normal Arrow
            projectile = NormalArrowProjectile(proj_x, proj_y, direction, self, renderer)
            projectile_manager.add_projectile(projectile)
            
            action = 'attack_normal'
            print("Player2: Normal Arrow spawned (Physical Damage)")
            
            # Network sync
            if network_ctx:
                is_multi, is_host, game_client = network_ctx
                if is_multi and game_client and game_client.is_connected():
                    try:
                        game_client.send_skill_event(action, direction, proj_x, proj_y)
                    except:
                        pass
    
    def apply_poison_damage(self, target, damage, tick_rate, duration):
        """
        Optional: Apply poison DoT effect to target.
        
        Called by poison projectile hit logic.
        
        Args:
            target: Enemy/Boss to poison
            damage: Damage per tick
            tick_rate: Seconds between damage ticks
            duration: Total poison duration
        """
        # Track poison application per target
        target_id = getattr(target, 'net_id', id(target))
        current_time = time.time()
        
        # Debounce: only apply poison once per target
        if target_id not in self.w_poison_applied:
            self.w_poison_applied[target_id] = current_time
            
            # Apply poison status if target supports it
            if hasattr(target, 'apply_poison'):
                target.apply_poison(duration, tick_rate, damage)
            
            # Schedule cleanup
            def cleanup_poison(tid):
                if tid in self.w_poison_applied:
                    del self.w_poison_applied[tid]
            
            # Note: Cleanup happens when poison animation finishes on target
    
    def on_hit_enemy(self, damage):
        """
        Override: Grant stamina reward on hit (same as parent).
        
        Called when player hits an enemy (for lifesteal, stamina gain).
        
        Args:
            damage: Damage dealt
        """
        super().on_hit_enemy(damage)
    
    def die(self):
        """Override: Die and clean up buff state."""
        self.w_buff_active = False
        self.w_poison_applied.clear()
        super().die()
