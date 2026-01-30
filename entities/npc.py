import os
import ctypes
import sdl2
import sdl2.ext
from enum import Enum
from settings import (
    NPC_GHOST_HEALTH,
    NPC_GHOST_DAMAGE,
    NPC_GHOST_ATTACK_RANGE,
    NPC_GHOST_SPEED,
    NPC_GHOST_DETECTION_RANGE,
    NPC_GHOST_PATROL_RADIUS,
    NPC_GHOST_ATTACK_COOLDOWN,

    NPC_SHOOTER_HEALTH,
    NPC_SHOOTER_DAMAGE,
    NPC_SHOOTER_ATTACK_RANGE,
    NPC_SHOOTER_SPEED,
    NPC_SHOOTER_DETECTION_RANGE,
    NPC_SHOOTER_PATROL_RADIUS,
    NPC_SHOOTER_ATTACK_COOLDOWN,

    NPC_ONRE_HEALTH,
    NPC_ONRE_DAMAGE,
    NPC_ONRE_ATTACK_RANGE,
    NPC_ONRE_SPEED,
    NPC_ONRE_DETECTION_RANGE,
    NPC_ONRE_PATROL_RADIUS,
    NPC_ONRE_ATTACK_COOLDOWN
)


class NPCState(Enum):
    """Enumeration for NPC states."""
    IDLE = "Idle"
    WALK = "Walk"
    RUN = "Run"
    ATTACK_1 = "Attack_1"
    ATTACK_2 = "Attack_2"
    ATTACK_3 = "Attack_3"
    ATTACK_4 = "Attack_4"
    HURT = "Hurt"
    DEAD = "Dead"


class Direction(Enum):
    """Enumeration for movement direction."""
    LEFT = -1
    RIGHT = 1


class NPC:
    """
    Base NPC class with shared animation, movement, and combat capabilities.
    
    This parent class consolidates common functionality for all NPC types,
    reducing code duplication and providing a consistent interface.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        health: Current health points
        max_health: Maximum health points
        damage: Attack damage
        attack_range: Attack range in pixels
        detection_range: Player detection range in pixels
        speed: Movement speed
        state: Current animation state
        direction: Movement direction (left/right)
        sprites: Dictionary of loaded sprite data
        textures: Dictionary of loaded textures
        current_frame: Current animation frame index
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
        patrol_left_bound: Left boundary for patrol
        patrol_right_bound: Right boundary for patrol
        is_attacking: Flag indicating if currently attacking
        attack_cooldown: Current attack cooldown counter
        attack_cooldown_max: Maximum attack cooldown frames
    """
    
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, 
                 health, damage, attack_range, detection_range, speed, 
                 patrol_radius, attack_cooldown_max):
        """
        Initialize base NPC.
        
        Args:
            x: Initial x position
            y: Initial y position
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            health: Maximum health points
            damage: Attack damage
            attack_range: Attack range in pixels
            detection_range: Player detection range in pixels
            speed: Movement speed
            patrol_radius: Patrol radius from spawn point
            attack_cooldown_max: Maximum attack cooldown in frames
        """
        # Position and dimensions
        self.x = x
        self.y = y
        self.width = 64
        self.height = 64
        
        # Combat stats
        self.health = health
        self.max_health = health
        self.damage = damage
        self.attack_range = attack_range
        self.detection_range = detection_range
        
        # Movement
        self.speed = speed
        self.direction = Direction.RIGHT
        self.velocity_x = self.speed
        self.velocity_y = 0
        
        # State and animation
        self.state = NPCState.IDLE
        self.textures = {}
        self.sprites = {}
        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0
        
        # PySDL2 components
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
        
        # AI behavior
        self.patrol_left_bound = x - patrol_radius
        self.patrol_right_bound = x + patrol_radius
        self.is_attacking = False
        self.attack_cooldown = 0
        self.attack_cooldown_max = attack_cooldown_max
        
        # Projectile system (can be set by child classes)
        self.projectile_manager = None
        
        # Load sprites (implemented by child classes)
        self._load_sprites()
    
    def _load_sprites(self):
        """Load sprite sheets. Must be implemented by child classes."""
        raise NotImplementedError("Subclasses must implement _load_sprites()")
    
    def _calculate_frames(self, state):
        """Calculate number of frames. Must be implemented by child classes."""
        raise NotImplementedError("Subclasses must implement _calculate_frames()")
    
    def _get_npc_folder_name(self):
        """Get the folder name for this NPC type. Must be implemented by child classes."""
        raise NotImplementedError("Subclasses must implement _get_npc_folder_name()")
    
    def update(self, delta_time=1):
        """
        Update NPC state, animation, and movement.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update animation
        self._update_animation()
        
        # Update cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown == 0:
                self.is_attacking = False
        
        # Update movement based on current state
        if self.state in [NPCState.WALK, NPCState.RUN]:
            self._update_movement()
        
        # Check if dead
        if self.health <= 0 and self.state != NPCState.DEAD:
            self.health = 0
            self.state = NPCState.DEAD
            self.current_frame = 0
    
    def _update_animation(self):
        """Update animation frame based on current state."""
        if self.state not in self.sprites:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            sprite_data = self.sprites[self.state]
            self.current_frame = (self.current_frame + 1) % sprite_data['frames']
    
    def _update_movement(self):
        """Update NPC movement with patrol behavior."""
        self.x += self.velocity_x
        
        # Check patrol boundaries and reverse direction
        if self.x <= self.patrol_left_bound:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
        elif self.x >= self.patrol_right_bound:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
    
    def move_left(self):
        """Move NPC to the left. Can be overridden by child classes."""
        self.direction = Direction.LEFT
        self.velocity_x = -self.speed
        if self.state not in self._get_non_interruptible_states():
            self.state = NPCState.WALK
    
    def move_right(self):
        """Move NPC to the right. Can be overridden by child classes."""
        self.direction = Direction.RIGHT
        self.velocity_x = self.speed
        if self.state not in self._get_non_interruptible_states():
            self.state = NPCState.WALK
    
    def stop(self):
        """Stop NPC movement."""
        self.velocity_x = 0
        if self.state == NPCState.RUN:
            self.state = NPCState.WALK
    
    def _get_non_interruptible_states(self):
        """Get list of states that cannot be interrupted. Can be overridden."""
        return [NPCState.HURT, NPCState.DEAD]
    
    def attack(self, attack_type=1):
        """
        Initiate an attack. Must be implemented by child classes.
        
        Args:
            attack_type: Type of attack
        """
        raise NotImplementedError("Subclasses must implement attack()")
    
    def take_damage(self, amount):
        """
        Apply damage to NPC.
        
        Args:
            amount: Damage amount to apply
        """
        self.health -= amount
        if self.health > 0:
            self.state = NPCState.HURT
            self.current_frame = 0
        else:
            self.health = 0
            self.state = NPCState.DEAD
            self.current_frame = 0
    
    def render(self):
        """Render NPC sprite to screen using PySDL2."""
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        texture = sprite_data['texture']
        
        # Calculate source rectangle (current frame in sprite sheet)
        frame_width = sprite_data['width'] // sprite_data['frames']
        frame_height = sprite_data['height']
        
        src_rect = sdl2.SDL_Rect(
            self.current_frame * frame_width,
            0,
            frame_width,
            frame_height
        )
        
        # Destination rectangle
        dest_rect = sdl2.SDL_Rect(
            int(self.x),
            int(self.y),
            self.width,
            self.height
        )
        
        # Flip sprite based on direction
        flip = sdl2.SDL_FLIP_NONE
        if self.direction == Direction.LEFT:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
        # Render the sprite
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            src_rect,
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
    
    def is_alive(self):
        """Check if NPC is still alive."""
        return self.health > 0
    
    def cleanup(self):
        """Clean up loaded textures."""
        for texture in self.textures.values():
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.textures.clear()
        self.sprites.clear()


class Ghost(NPC):
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, projectile_manager=None):
        """
        Initialize Ghost NPC.
        
        Args:
            x: Initial x position
            y: Initial y position
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            projectile_manager: ProjectileManager instance for spawning projectiles (optional)
        """
        super().__init__(
            x, y, sprite_factory, texture_factory, renderer,
            health=NPC_GHOST_HEALTH,
            damage=NPC_GHOST_DAMAGE,
            attack_range=NPC_GHOST_ATTACK_RANGE,
            detection_range=NPC_GHOST_DETECTION_RANGE,
            speed=NPC_GHOST_SPEED,
            patrol_radius=NPC_GHOST_PATROL_RADIUS,
            attack_cooldown_max=NPC_GHOST_ATTACK_COOLDOWN
        )
        
        # Set projectile manager for firing projectiles
        self.projectile_manager = projectile_manager
        
        # Track which frame to fire projectile (mid-attack animation)
        self.projectile_fired_this_attack = False
    
    def _get_npc_folder_name(self):
        """Get the folder name for Ghost sprites."""
        return "Ghost"
    
    def _load_sprites(self):
        """Load all Ghost sprite sheets from assets folder."""
        base_path = os.path.join("assets", "NPC", self._get_npc_folder_name())
        
        sprite_files = {
            NPCState.IDLE: "Idle.png",
            NPCState.WALK: "Walk.png",
            NPCState.RUN: "Run.png",
            NPCState.ATTACK_3: "Attack_3.png",
            NPCState.ATTACK_4: "Attack_4.png",
            NPCState.HURT: "Hurt.png",
            NPCState.DEAD: "Dead.png"
        }
        
        for state, filename in sprite_files.items():
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    # Load texture using SDL_image
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.textures[state] = texture
                        # Get texture dimensions
                        w = ctypes.c_int()
                        h = ctypes.c_int()
                        sdl2.SDL_QueryTexture(texture, None, None, ctypes.byref(w), ctypes.byref(h))
                        frames = self._calculate_frames(state)
                        self.sprites[state] = {
                            'texture': texture,
                            'width': w.value,
                            'height': h.value,
                            'frames': frames
                        }
                        # Debug output for Attack_3 and Attack_4
                        if state in [NPCState.ATTACK_3, NPCState.ATTACK_4]:
                            print(f"Loaded {state.value}: {w.value}x{h.value} pixels, {frames} frames, frame_width={w.value//frames}")
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
    
    def _calculate_frames(self, state):
        """
        Calculate number of frames in a sprite sheet.
        Based on user specifications.
        """
        frame_counts = {
            NPCState.IDLE: 5,
            NPCState.WALK: 5,
            NPCState.RUN: 5,
            NPCState.ATTACK_3: 7,
            NPCState.ATTACK_4: 7,
            NPCState.HURT: 3,
            NPCState.DEAD: 4
        }
        return frame_counts.get(state, 1)
    
    def _get_non_interruptible_states(self):
        """Get list of states that cannot be interrupted for Ghost."""
        return [NPCState.ATTACK_3, NPCState.ATTACK_4, NPCState.HURT, NPCState.DEAD]
    
    def update(self, delta_time=1):
        """
        Update Ghost NPC with projectile firing logic.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Call parent update
        super().update(delta_time)
        
        # Fire projectile at appropriate frame during attack animation
        if self.is_attacking and not self.projectile_fired_this_attack:
            # Fire projectile at frame 3 for both Attack_3 and Attack_4
            if self.current_frame >= 3:
                if self.state == NPCState.ATTACK_3:
                    self._fire_projectile(charge_type=1)
                elif self.state == NPCState.ATTACK_4:
                    self._fire_projectile(charge_type=2)
                self.projectile_fired_this_attack = True
        
        # Reset projectile flag when attack ends
        if not self.is_attacking:
            self.projectile_fired_this_attack = False
    
    def _fire_projectile(self, charge_type):
        """
        Fire a projectile from the Ghost.
        
        Args:
            charge_type: 1 for Charge_1, 2 for Charge_2
        """
        if not self.projectile_manager:
            return
        
        # Calculate projectile spawn position (in front of Ghost)
        offset_x = 25 if self.direction == Direction.RIGHT else -25
        proj_x = self.x + offset_x
        proj_y = self.y + 22
        
        direction = 1 if self.direction == Direction.RIGHT else -1
        
        # Spawn the projectile through the manager
        self.projectile_manager.spawn_ghost_projectile(
            proj_x, proj_y, direction, self, charge_type
        )
    
    def attack(self, attack_type=3):
        """
        Initiate an attack with automatic projectile firing.
        
        Args:
            attack_type: Type of attack (3 or 4 only)
        """
        if self.attack_cooldown > 0 or self.is_attacking:
            return
        
        attack_states = {
            3: NPCState.ATTACK_3,
            4: NPCState.ATTACK_4
        }
        
        self.state = attack_states.get(attack_type, NPCState.ATTACK_3)
        self.current_frame = 0
        self.is_attacking = True
        self.attack_cooldown = self.attack_cooldown_max
        self.velocity_x = 0
        self.projectile_fired_this_attack = False  # Reset for new attack


class Shooter(NPC):
    def __init__(self, x, y, sprite_factory, texture_factory, renderer):
        """
        Initialize Shooter NPC.
        
        Args:
            x: Initial x position
            y: Initial y position
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
        """
        super().__init__(
            x, y, sprite_factory, texture_factory, renderer,
            health=NPC_SHOOTER_HEALTH,
            damage=NPC_SHOOTER_DAMAGE,
            attack_range=NPC_SHOOTER_ATTACK_RANGE,
            detection_range=NPC_SHOOTER_DETECTION_RANGE,
            speed=NPC_SHOOTER_SPEED,
            patrol_radius=NPC_SHOOTER_PATROL_RADIUS,
            attack_cooldown_max=NPC_SHOOTER_ATTACK_COOLDOWN
        )
    
    def _get_npc_folder_name(self):
        """Get the folder name for Shooter sprites."""
        return "Shooter" 
    
    def _load_sprites(self):
        """Load all Shooter sprite sheets from assets folder."""
        base_path = os.path.join("assets", "NPC", self._get_npc_folder_name())
        
        sprite_files = {
            NPCState.IDLE: "Idle.png",
            NPCState.ATTACK_1: "Attack_1.png",
            NPCState.ATTACK_2: "Attack_2.png",
            NPCState.DEAD: "Dead.png",
            NPCState.HURT: "Hurt.png",
            NPCState.RUN: "Run.png",
            NPCState.WALK: "Walk.png"
        }
        
        for state, filename in sprite_files.items():
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    # Load texture using SDL_image
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.textures[state] = texture
                        # Get texture dimensions
                        w = ctypes.c_int()
                        h = ctypes.c_int()
                        sdl2.SDL_QueryTexture(texture, None, None, ctypes.byref(w), ctypes.byref(h))
                        frames = self._calculate_frames(state)
                        self.sprites[state] = {
                            'texture': texture,
                            'width': w.value,
                            'height': h.value,
                            'frames': frames
                        }
                        print(f"Loaded Shooter {state.value}: {w.value}x{h.value} pixels, {frames} frames")
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
    
    def _calculate_frames(self, state):
        """
        Calculate number of frames in a sprite sheet.
        Based on user specifications.
        """
        frame_counts = {
            NPCState.IDLE: 7,
            NPCState.WALK: 7,
            NPCState.RUN: 8,
            NPCState.ATTACK_1: 4,
            NPCState.ATTACK_2: 4,
            NPCState.HURT: 3,
            NPCState.DEAD: 4
        }
        return frame_counts.get(state, 1)
    
    def _get_non_interruptible_states(self):
        """Get list of states that cannot be interrupted for Shooter."""
        return [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.HURT, NPCState.DEAD]
    
    def attack(self, attack_type=1):
        """
        Initiate a ranged attack.
        
        Args:
            attack_type: Type of attack (1 or 2)
        """
        if self.attack_cooldown > 0 or self.is_attacking:
            return
        
        attack_states = {
            1: NPCState.ATTACK_1,
            2: NPCState.ATTACK_2
        }
        
        self.state = attack_states.get(attack_type, NPCState.ATTACK_1)
        self.current_frame = 0
        self.is_attacking = True
        self.attack_cooldown = self.attack_cooldown_max
        self.velocity_x = 0


class Onre(NPC):
    def __init__(self, x, y, sprite_factory, texture_factory, renderer):
        """
        Initialize Onre NPC.
        
        Args:
            x: Initial x position
            y: Initial y position
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
        """
        super().__init__(
            x, y, sprite_factory, texture_factory, renderer,
            health=NPC_ONRE_HEALTH,
            damage=NPC_ONRE_DAMAGE,
            attack_range=NPC_ONRE_ATTACK_RANGE,
            detection_range=NPC_ONRE_DETECTION_RANGE,
            speed=NPC_ONRE_SPEED,
            patrol_radius=NPC_ONRE_PATROL_RADIUS,
            attack_cooldown_max=NPC_ONRE_ATTACK_COOLDOWN
        )
    
    def _get_npc_folder_name(self):
        """Get the folder name for Onre sprites."""
        return "Onre"
    
    def _load_sprites(self):
        """Load all Onre sprite sheets from assets folder."""
        base_path = os.path.join("assets", "NPC", self._get_npc_folder_name())
        
        sprite_files = {
            NPCState.IDLE: "Idle.png",
            NPCState.ATTACK_1: "Attack_1.png",
            NPCState.ATTACK_2: "Attack_2.png",
            NPCState.ATTACK_3: "Attack_3.png",
            NPCState.DEAD: "Dead.png",
            NPCState.HURT: "Hurt.png",
            NPCState.RUN: "Run.png",
            NPCState.WALK: "Walk.png"
        }
        
        for state, filename in sprite_files.items():
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    # Load texture using SDL_image
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.textures[state] = texture
                        # Get texture dimensions
                        w = ctypes.c_int()
                        h = ctypes.c_int()
                        sdl2.SDL_QueryTexture(texture, None, None, ctypes.byref(w), ctypes.byref(h))
                        frames = self._calculate_frames(state)
                        self.sprites[state] = {
                            'texture': texture,
                            'width': w.value,
                            'height': h.value,
                            'frames': frames
                        }
                        print(f"Loaded Onre {state.value}: {w.value}x{h.value} pixels, {frames} frames")
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
    
    def _calculate_frames(self, state):
        """
        Calculate number of frames in a sprite sheet.
        Based on user specifications.
        """
        frame_counts = {
            NPCState.IDLE: 6,
            NPCState.WALK: 7,
            NPCState.RUN: 7,
            NPCState.ATTACK_1: 5,
            NPCState.ATTACK_2: 4,
            NPCState.ATTACK_3: 4,
            NPCState.HURT: 3,
            NPCState.DEAD: 5
        }
        return frame_counts.get(state, 1)
    
    def _get_non_interruptible_states(self):
        """Get list of states that cannot be interrupted for Onre."""
        return [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.ATTACK_3, 
                NPCState.HURT, NPCState.DEAD]
    
    def move_left(self):
        """Move Onre to the left."""
        if self.state not in self._get_non_interruptible_states():
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
    
    def move_right(self):
        """Move Onre to the right."""
        if self.state not in self._get_non_interruptible_states():
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
    
    def attack(self, attack_type=1):
        """
        Perform attack animation.
        
        Args:
            attack_type: Type of attack (1, 2, or 3)
        """
        if self.is_attacking or self.attack_cooldown > 0:
            return
        
        attack_states = {
            1: NPCState.ATTACK_1,
            2: NPCState.ATTACK_2,
            3: NPCState.ATTACK_3
        }
        
        self.state = attack_states.get(attack_type, NPCState.ATTACK_1)
        self.current_frame = 0
        self.is_attacking = True
        self.attack_cooldown = self.attack_cooldown_max
        self.velocity_x = 0


class NPCManager:
    def __init__(self, sprite_factory, texture_factory, renderer, projectile_manager=None):
        """
        Initialize NPC Manager.
        
        Args:
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            projectile_manager: ProjectileManager instance for NPC projectiles (optional)
        """
        self.npcs = []
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
        self.projectile_manager = projectile_manager
    
    def spawn_ghost(self, x, y):
        """
        Spawn a new Ghost NPC.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            
        Returns:
            Ghost: The spawned Ghost instance
        """
        ghost = Ghost(x, y, self.sprite_factory, self.texture_factory, 
                     self.renderer, self.projectile_manager)
        self.npcs.append(ghost)
        return ghost
    
    def spawn_shooter(self, x, y):
        """
        Spawn a new Shooter NPC.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            
        Returns:
            Shooter: The spawned Shooter instance
        """
        shooter = Shooter(x, y, self.sprite_factory, self.texture_factory, self.renderer)
        self.npcs.append(shooter)
        return shooter
    
    def spawn_onre(self, x, y):
        """
        Spawn a new Onre NPC.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            
        Returns:
            Onre: The spawned Onre instance
        """
        onre = Onre(x, y, self.sprite_factory, self.texture_factory, self.renderer)
        self.npcs.append(onre)
        return onre
    
    def update_all(self, delta_time=1):
        """Update all NPCs."""
        for npc in self.npcs:
            npc.update(delta_time)
        
        # Remove dead NPCs after death animation completes
        self.npcs = [npc for npc in self.npcs if npc.is_alive() or npc.state != NPCState.DEAD]
    
    def render_all(self):
        """Render all NPCs."""
        for npc in self.npcs:
            npc.render()
    
    def cleanup(self):
        """Clean up all NPCs."""
        for npc in self.npcs:
            npc.cleanup()
        self.npcs.clear()
