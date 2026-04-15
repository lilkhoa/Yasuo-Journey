"""
Player 2 Projectile System

Three specialized projectile classes for Player 2's W skill (Toxin Enhancement):
1. PoisonProjectile - Deals damage, optional DoT
2. PlantProjectile - Roots first enemy hit
3. HealDustProjectile - Heals allies (RemotePlayers)
"""

import os
import ctypes
import sdl2
import sdl2.ext
import time
from settings import (
    W_PROJECTILE_SPEED,
    DAMAGE_W_POISON,
    POISON_TICK_RATE,
    POISON_DURATION,
    DAMAGE_W_PLANT,
    W_PLANT_SNARE_DURATION,
    HEAL_W_DUST,
)


class Player2Projectile:
    """
    Base class for Player 2 projectiles.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        velocity_x, velocity_y: Movement velocity
        direction: Movement direction (1 for right, -1 for left)
        active: Whether projectile is still active
        owner: Reference to the entity that fired this projectile (Player2)
        renderer: SDL2 renderer
        frame_textures: List of individual frame textures
        current_frame: Current animation frame
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
        lifetime: Maximum age in frames
        age: Current age in frames
    """
    
    def __init__(self, x, y, direction, owner, renderer, frame_count, texture_dir):
        """
        Initialize Player 2 projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Player2 that fired this projectile
            renderer: PySDL2 renderer
            frame_count: Number of animation frames to load
            texture_dir: Path to texture directory
        """
        self.x = x
        self.y = y
        self.width = 48
        self.height = 48
        self.velocity_x = W_PROJECTILE_SPEED * direction
        self.velocity_y = 0
        self.direction = direction
        self.active = True
        self.owner = owner
        self.renderer = renderer
        
        # Animation
        self.frame_textures = []
        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0
        
        # Lifetime (frames until auto-destroy)
        self.lifetime = 300  # 5 seconds at 60 FPS
        self.age = 0
        
        # Load textures
        self.texture_dir = texture_dir
        self.frame_count = frame_count
        self._load_textures()
    
    def _load_textures(self):
        """Load animation frame textures."""
        for i in range(1, self.frame_count + 1):
            filename = f"arrow_hit_poison_{i}.png"  # Will be overridden in subclasses
            filepath = os.path.join(self.texture_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Projectile frame not found: {filepath}")
    
    def update(self, delta_time=1, world = None, my_map = None, obstacles = None):
        """
        Update projectile position and animation.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if not self.active:
            return
        
        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Update animation
        self._update_animation()
        
        # Update lifetime
        self.age += 1
        if self.age >= self.lifetime:
            self.active = False
    
    def _update_animation(self):
        """Update animation frame."""
        if not self.frame_textures:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_textures)
    
    def render(self, camera_x=0, camera_y=0):
        """Render projectile sprite.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        if not self.active or not self.frame_textures:
            return
        
        # Get current frame texture
        texture = self.frame_textures[self.current_frame]
        
        # Destination rectangle (apply camera offset for screen-space rendering)
        dest_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        
        # Flip sprite based on direction
        flip = sdl2.SDL_FLIP_NONE
        if self.direction < 0:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
        # Render
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            None,  # Use entire texture
            dest_rect,
            0,
            None,
            flip
        )
    
    def get_bounds(self):
        """
        Get bounding box for collision detection.
        
        Returns:
            tuple: (x, y, width, height)
        """
        return (self.x, self.y, self.width, self.height)
    
    def check_collision(self, target):
        """
        Check collision with a target entity.
        
        Args:
            target: Entity with get_bounds() method
            
        Returns:
            bool: True if collision detected
        """
        if not self.active:
            return False
        
        # Get bounding boxes
        px, py, pw, ph = self.get_bounds()
        
        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
        else:
            # Fallback for sprite-based objects
            tx = target.x if hasattr(target, 'x') else target.sprite.x
            ty = target.y if hasattr(target, 'y') else target.sprite.y
            tw = target.width if hasattr(target, 'width') else target.sprite.size[0]
            th = target.height if hasattr(target, 'height') else target.sprite.size[1]
        
        # AABB collision detection
        return (px < tx + tw and
                px + pw > tx and
                py < ty + th and
                py + ph > ty)
    
    def cleanup(self):
        """Clean up resources."""
        for texture in self.frame_textures:
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.frame_textures.clear()


class PoisonProjectile(Player2Projectile):
    """
    Poison Projectile - Deals damage with optional DoT effect.
    
    Behavior:
    - Moves horizontally
    - Collides with enemies/bosses
    - Applies damage on first hit
    - Optional: Applies poison DoT status effect
    """
    
    def __init__(self, x, y, direction, owner, renderer, damage_multiplier=1.0):
        """
        Initialize Poison projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Player2 that fired this projectile
            renderer: PySDL2 renderer
            damage_multiplier: Damage scaling multiplier
        """
        # Load poison projectile animation (8 frames)
        base_path = os.path.join("assets", "Projectile", "Player_2", "w", "poison")
        
        super().__init__(x, y, direction, owner, renderer, 
                        frame_count=8, texture_dir=base_path)
        
        # Poison-specific stats
        self.damage = DAMAGE_W_POISON * damage_multiplier
        self.poison_duration = POISON_DURATION
        self.poison_tick_rate = POISON_TICK_RATE
        self.has_hit = False  # Track if already hit a target
    
    def _load_textures(self):
        """Load poison projectile animation frames."""
        for i in range(1, self.frame_count + 1):
            filename = f"arrow_hit_poison_{i}.png"
            filepath = os.path.join(self.texture_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Poison projectile frame not found: {filepath}")
    
    def apply_damage(self, target, network_ctx=None):
        """
        Apply poison damage to target.
        
        Args:
            target: Enemy/Boss to damage
            network_ctx: Network context tuple (is_multi, is_host, game_client)
        """
        if self.has_hit:
            return
        
        self.has_hit = True
        damage = self.damage
        target_net_id = getattr(target, 'net_id', id(target))
        
        print(f"Poison Hit! Damage: {damage}")
        
        # Apply damage - network-aware
        if network_ctx:
            is_multi, is_host, game_client = network_ctx
            if is_multi and game_client and game_client.is_connected():
                etype = 'boss' if target.__class__.__name__ == 'Boss' else 'npc'
                game_client.send_hit_event(etype, target_net_id, damage)
            else:
                if hasattr(target, 'take_damage'):
                    target.take_damage(damage)
        else:
            if hasattr(target, 'take_damage'):
                target.take_damage(damage)
        
        # Optional: Apply poison DoT effect
        if hasattr(target, 'apply_poison'):
            target.apply_poison(self.poison_duration, self.poison_tick_rate)
        
        # Deactivate projectile
        self.active = False


class PlantProjectile(Player2Projectile):
    """
    Plant Projectile - Roots the first enemy hit for a duration.
    
    Behavior:
    - Moves horizontally
    - Does NOT pierce - destroys on first hit
    - Applies root/snare status effect to first target
    - No damage dealt (root effect is the primary effect)
    """
    
    def __init__(self, x, y, direction, owner, renderer):
        """
        Initialize Plant projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Player2 that fired this projectile
            renderer: PySDL2 renderer
        """
        # Load plant projectile animation (8 frames)
        base_path = os.path.join("assets", "Projectile", "Player_2", "w", "root")
        
        super().__init__(x, y, direction, owner, renderer, 
                        frame_count=8, texture_dir=base_path)
        
        # Plant-specific stats
        self.root_duration = W_PLANT_SNARE_DURATION
        self.has_hit = False  # Can only hit once
    
    def _load_textures(self):
        """Load plant projectile animation frames."""
        for i in range(1, self.frame_count + 1):
            filename = f"arrow_hit_entangle_{i}.png"
            filepath = os.path.join(self.texture_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Plant projectile frame not found: {filepath}")
    
    def apply_root(self, target, network_ctx=None):
        """
        Apply root/snare effect to target (no damage).
        
        Args:
            target: Enemy/Boss to root
            network_ctx: Network context tuple (is_multi, is_host, game_client)
        """
        if self.has_hit:
            return
        
        self.has_hit = True
        target_net_id = getattr(target, 'net_id', id(target))
        
        print(f"Plant Root Applied! Duration: {self.root_duration}s")
        
        # Apply root effect to target
        if hasattr(target, 'snared_timer'):
            target.snared_timer = self.root_duration
        elif hasattr(target, 'apply_snare'):
            target.apply_snare(self.root_duration)
        
        # Network sync - send status event
        if network_ctx:
            is_multi, is_host, game_client = network_ctx
            if is_multi and game_client and game_client.is_connected():
                # Send root/snare status event (requires custom network packet)
                # For now, we'll use a hit event with 0 damage to signal root
                try:
                    game_client.send_status_event(target_net_id, 'snare', self.root_duration)
                except:
                    # Fallback: if send_status_event doesn't exist
                    etype = 'boss' if target.__class__.__name__ == 'Boss' else 'npc'
                    game_client.send_hit_event(etype, target_net_id, 0)
        
        # Deactivate projectile (no piercing)
        self.active = False


class HealDustProjectile(Player2Projectile):
    """
    Heal Dust Projectile - Heals allies (RemotePlayers) when jumping.
    
    Behavior:
    - Spawned only from jump + attack (air attack with W buff)
    - Does NOT collide with enemies
    - Only collides with allies/RemotePlayers
    - Applies healing when hitting ally
    - Destroys after hitting first ally
    - Visual effect: green dust particles
    """
    
    def __init__(self, x, y, direction, owner, renderer):
        """
        Initialize Heal Dust projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Player2 that fired this projectile
            renderer: PySDL2 renderer
        """
        # Load heal dust projectile animation (8 frames)
        base_path = os.path.join("assets", "Projectile", "Player_2", "w", "heal")
        
        super().__init__(x, y, direction, owner, renderer, 
                        frame_count=8, texture_dir=base_path)
        
        # Heal-specific stats
        self.heal_amount = HEAL_W_DUST
        self.has_healed = False  # Only heal once
    
    def _load_textures(self):
        """Load heal dust projectile animation frames."""
        for i in range(1, self.frame_count + 1):
            filename = f"diagonal_arrow_hit_thorns_{i}.png"
            filepath = os.path.join(self.texture_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Heal dust frame not found: {filepath}")
    
    def apply_heal(self, ally, network_ctx=None):
        """
        Heal an ally (RemotePlayer).
        
        Args:
            ally: RemotePlayer to heal
            network_ctx: Network context tuple (is_multi, is_host, game_client)
        """
        if self.has_healed:
            return
        
        self.has_healed = True
        heal_amount = self.heal_amount
        ally_net_id = getattr(ally, 'net_id', id(ally))
        
        print(f"Heal Dust Applied! Healing: {heal_amount}HP")
        
        # Apply healing to ally
        if hasattr(ally, 'heal'):
            ally.heal(heal_amount)
        elif hasattr(ally, 'hp'):
            ally.hp = min(ally.hp + heal_amount, 
                         getattr(ally, 'max_hp', ally.hp + heal_amount))
        
        # Network sync - send heal event
        if network_ctx:
            is_multi, is_host, game_client = network_ctx
            if is_multi and game_client and game_client.is_connected():
                try:
                    game_client.send_heal_event(ally_net_id, heal_amount)
                except:
                    # Fallback: if send_heal_event doesn't exist, use custom packet
                    pass
        
        # Deactivate projectile
        self.active = False
    
    def check_ally_collision(self, allies):
        """
        Check collision with allies instead of enemies.
        
        Args:
            allies: List of RemotePlayer objects
            
        Returns:
            RemotePlayer if collision detected, None otherwise
        """
        if not self.active or self.has_healed:
            return None
        
        for ally in allies:
            if self.check_collision(ally):
                return ally
        
        return None

class NormalArrowProjectile(Player2Projectile):
    """
    Normal attack arrow for Player 2.
    Travels straight and deals base physical damage.
    """
    def __init__(self, x, y, direction, owner, renderer):
        # Path to the directory of normal arrow:
        texture_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'Player_2', 'projectiles_and_effects', 'arrow')
        
        # Initialize the baseclass (temporaly pass 1 frame)
        super().__init__(x, y, direction, owner, renderer, 1, texture_dir)
        
        # --- Basic stats of normal attack
        self.velocity_x = 800 * direction  # Arrow move's speed (800 px/s)
        self.velocity_y = 0                # Go straight, now drop down.
        
        # Get the owner's physical damage
        self.damage = getattr(owner, 'attack_damage', 10) 
        
        # Range and Stuck Logic
        self.start_x = x
        # Taking reference from shooter NPC projectile speed or a fixed range (e.g., 700px)
        self.max_range = 700

        self.is_stuck = False
        self.stucker_timer = 0
        self.STUCK_DURATION = 1.0   # time in second before disappearing

        # [OVERRIDE] Process the arrow image 
        self._load_exact_arrow(texture_dir)

    def _load_exact_arrow(self, texture_dir):
        """Delete default load texture and exactly load the file arrow_.png"""
        for tex in self.frame_textures:
            if tex: sdl2.SDL_DestroyTexture(tex)
        self.frame_textures.clear()
        
        filepath = os.path.join(texture_dir, 'arrow_.png')
        if os.path.exists(filepath):
            surface = sdl2.ext.load_image(filepath)

            # Flip image if facing left
            if self.direction < 0:
                dup_surface_ptr = sdl2.SDL_DuplicateSurface(surface)
                dup_surface = dup_surface_ptr.contents
                dst_px = sdl2.ext.pixels3d(dup_surface)
                dst_px[:] = dst_px[:, ::-1, :] # Flip horizontal
                sdl2.SDL_FreeSurface(surface)
                surface = dup_surface_ptr
                
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            self.frame_textures.append(texture)
            
            # Update Hitbox to fit with the arrow
            if hasattr(surface, "contents"):
                self.width = surface.contents.w
                self.height = surface.contents.h
            else:
                self.width = surface.w
                self.height = surface.h
                
            sdl2.SDL_FreeSurface(surface)

    def check_collision(self, target):
        """
        Override to ensure that the arrow go through Yasuo (Player 1).
        Game loop system is always check projectile with enemies,
        but need to check here to ensure in Multiplayer mode.
        """
        # If target is anthoer Player (Yasuo), skip collision
        if hasattr(target, 'inventory') and target != self.owner: 
            return False
            
        return super().check_collision(target)
    
    def update(self, dt, world, my_map, interactables=None):
        """
        Modified update logic to handle sticking and range.
        """
        if not self.active:
            return

        if self.is_stuck:
            # If stuck, just wait for the duration to pass
            self.stuck_timer += dt
            if self.stuck_timer >= self.STUCK_DURATION:
                self.active = False
            return

        # 1. Standard Movement
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        
        # 2. Check Range Limit
        distance_traveled = abs(self.x - self.start_x)
        if distance_traveled >= self.max_range:
            self.active = False
            return

        # 3. Check Collision with Map Blocks (block)
        # Assuming boxes is a list of SDL_Rect or objects with .x, .y, .w, .h
        for block in my_map:
            if self.check_world_collision(block):
                self._stick_to_surface()
                return

        # 4. Check Collision with Obstacles (barrels, boxes, chests)
        if interactables:
            for obj in interactables:
                # We only stick to physical obstacles like barrels, chests, etc.
                if self.check_world_collision(obj):
                    self._stick_to_surface()
                    return

    def check_world_collision(self, obstacle):
        """Helper to check collision with non-enemy objects."""
        # Simple AABB collision check
        obj_x = getattr(obstacle, 'x', obstacle[0] if isinstance(obstacle, (list, tuple)) else 0)
        obj_y = getattr(obstacle, 'y', obstacle[1] if isinstance(obstacle, (list, tuple)) else 0)
        obj_w = getattr(obstacle, 'w', obstacle[2] if isinstance(obstacle, (list, tuple)) else 32)
        obj_h = getattr(obstacle, 'h', obstacle[3] if isinstance(obstacle, (list, tuple)) else 32)

        return (self.x < obj_x + obj_w and
                self.x + self.width > obj_x and
                self.y < obj_y + obj_h and
                self.y + self.height > obj_y)

    def _stick_to_surface(self):
        """Stops the arrow and starts the stick timer."""
        self.is_stuck = True
        self.velocity_x = 0
        self.velocity_y = 0
        self.stuck_timer = 0