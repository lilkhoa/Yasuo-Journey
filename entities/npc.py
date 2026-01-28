"""
NPC Module - Ghost Enemy Implementation
Handles Ghost NPC behavior, animations, and combat mechanics using PySDL2.
"""
import os
import ctypes
import sdl2
import sdl2.ext
from enum import Enum


class NPCState(Enum):
    """Enumeration for NPC states."""
    IDLE = "Idle"
    WALK = "Walk"
    RUN = "Run"
    JUMP = "Jump"
    ATTACK_1 = "Attack_1"
    ATTACK_2 = "Attack_2"
    ATTACK_3 = "Attack_3"
    ATTACK_4 = "Attack_4"
    CHARGE_1 = "Charge_1"
    CHARGE_2 = "Charge_2"
    HURT = "Hurt"
    DEAD = "Dead"
    SCREAM = "Scream"


class Direction(Enum):
    """Enumeration for movement direction."""
    LEFT = -1
    RIGHT = 1


class Ghost:
    """
    Ghost NPC class with animation, movement, and combat capabilities.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        health: Current health points
        max_health: Maximum health points
        speed: Movement speed
        state: Current animation state
        direction: Movement direction (left/right)
        sprites: Dictionary of loaded sprite surfaces
        current_frame: Current animation frame index
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
    """
    
    def __init__(self, x, y, sprite_factory, texture_factory, renderer):
        """
        Initialize Ghost NPC.
        
        Args:
            x: Initial x position
            y: Initial y position
            sprite_factory: PySDL2 sprite factory for creating sprites
            texture_factory: PySDL2 texture factory for loading images
            renderer: PySDL2 renderer
        """
        self.x = x
        self.y = y
        self.width = 64
        self.height = 64
        
        # Combat stats
        self.health = 100
        self.max_health = 100
        self.damage = 10
        self.attack_range = 100
        
        # Movement
        self.speed = 2
        self.direction = Direction.RIGHT
        self.velocity_x = self.speed
        self.velocity_y = 0
        
        # State and animation
        self.state = NPCState.IDLE
        self.sprites = {}
        self.textures = {}
        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0
        
        # PySDL2 components
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
        
        # Load sprites
        self._load_sprites()
        
        # For movement testing, can be removed later
        self.patrol_left_bound = x - 200
        self.patrol_right_bound = x + 200
        self.is_attacking = False
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60  # frames
        
    def _load_sprites(self):
        """Load all Ghost sprite sheets from assets folder."""
        base_path = os.path.join("assets", "NPC", "Ghost")
        
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
    
    def update(self, delta_time=1):
        """
        Update Ghost NPC state, animation, and movement.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update animation
        self._update_animation()
        
        # Update cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            # Reset is_attacking when cooldown expires
            if self.attack_cooldown == 0:
                self.is_attacking = False
        
        # Update movement based on current state
        if self.state == NPCState.WALK or self.state == NPCState.RUN:
            self._update_movement()
        
        if self.health <= 0 and self.state != NPCState.DEAD:
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
        """Update Ghost movement with patrol behavior."""
        self.x += self.velocity_x

        if self.x <= self.patrol_left_bound:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
        elif self.x >= self.patrol_right_bound:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
    
    def move_left(self):
        """Move Ghost to the left."""
        self.direction = Direction.LEFT
        self.velocity_x = -self.speed
        if self.state not in [NPCState.ATTACK_3, NPCState.ATTACK_4, NPCState.HURT, NPCState.DEAD]:
            self.state = NPCState.WALK
    
    def move_right(self):
        """Move Ghost to the right."""
        self.direction = Direction.RIGHT
        self.velocity_x = self.speed
        if self.state not in [NPCState.ATTACK_3, NPCState.ATTACK_4, NPCState.HURT, NPCState.DEAD]:
            self.state = NPCState.WALK
    
    def stop(self):
        """Stop Ghost movement."""
        self.velocity_x = 0
        if self.state == NPCState.RUN:
            self.state = NPCState.WALK
    
    def attack(self, attack_type=3):
        """
        Initiate an attack.
        
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
        # Stop movement during attack
        self.velocity_x = 0
    
    def take_damage(self, amount):
        """
        Apply damage to Ghost.
        
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
        """Render Ghost sprite to screen using PySDL2."""
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        texture = sprite_data['texture']
        total_width = sprite_data['width']
        total_height = sprite_data['height']
        num_frames = sprite_data['frames']
        
        # Calculate frame dimensions
        frame_width = total_width // num_frames
        frame_height = total_height
        
        # Source rectangle (current frame in sprite sheet)
        src_rect = sdl2.SDL_Rect(
            self.current_frame * frame_width,
            0,
            frame_width,
            frame_height
        )
        
        # Destination rectangle (where to draw on screen)
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
            0,  # angle
            None,  # center
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
        """Check if Ghost is still alive."""
        return self.health > 0
    
    def cleanup(self):
        """Clean up loaded textures."""
        for texture in self.textures.values():
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.textures.clear()
        self.sprites.clear()


class Shooter:
    """
    Shooter NPC class with animation, movement, and ranged combat capabilities.
    Sprites are stored as individual frame files in separate folders.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        health: Current health points
        max_health: Maximum health points
        speed: Movement speed
        state: Current animation state
        direction: Movement direction (left/right)
        frame_textures: Dictionary of texture lists for each state
        current_frame: Current animation frame index
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
    """
    
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
        self.x = x
        self.y = y
        self.width = 64
        self.height = 64
        
        # Combat stats
        self.health = 120
        self.max_health = 120
        self.damage = 5
        self.attack_range = 200
        
        # Movement
        self.speed = 1.5
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
        
        # Load sprites
        self._load_sprites()
        
        # AI behavior
        self.patrol_left_bound = x - 150
        self.patrol_right_bound = x + 150
        self.is_attacking = False
        self.attack_cooldown = 0
        self.attack_cooldown_max = 80 
    
    def _load_sprites(self):
        """Load all Shooter sprite sheets from assets folder."""
        base_path = os.path.join("assets", "NPC", "Shooter")
        
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
    
    def update(self, delta_time=1):
        """
        Update Shooter NPC state, animation, and movement.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update animation
        self._update_animation()
        
        # Update cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            # Reset is_attacking when cooldown expires
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
        """Update Shooter movement with patrol behavior."""
        self.x += self.velocity_x
        
        # Check patrol boundaries and reverse direction
        if self.x <= self.patrol_left_bound:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
        elif self.x >= self.patrol_right_bound:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
    
    def move_left(self):
        """Move Shooter to the left."""
        self.direction = Direction.LEFT
        self.velocity_x = -self.speed
        if self.state not in [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.HURT, NPCState.DEAD]:
            self.state = NPCState.WALK
    
    def move_right(self):
        """Move Shooter to the right."""
        self.direction = Direction.RIGHT
        self.velocity_x = self.speed
        if self.state not in [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.HURT, NPCState.DEAD]:
            self.state = NPCState.WALK
    
    def stop(self):
        """Stop Shooter movement."""
        self.velocity_x = 0
        if self.state in [NPCState.WALK, NPCState.RUN]:
            self.state = NPCState.WALK
    
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
    
    def take_damage(self, amount):
        """
        Apply damage to Shooter.
        
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
        """Render Shooter sprite to screen using PySDL2."""
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
        """Check if Shooter is still alive."""
        return self.health > 0
    
    def cleanup(self):
        """Clean up loaded textures."""
        for texture in self.textures.values():
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.textures.clear()
        self.sprites.clear()


class Onre:
    """
    Onre NPC class with animation, movement, and combat capabilities.
    Sprites are stored as sprite sheet PNG files.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        health: Current health points
        max_health: Maximum health points
        speed: Movement speed
        state: Current animation state
        direction: Movement direction (left/right)
        textures: Dictionary of textures for each state
        sprites: Dictionary of sprite data for each state
        current_frame: Current animation frame index
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
    """
    
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
        self.x = x
        self.y = y
        self.width = 64
        self.height = 64
        
        # Combat stats
        self.health = 150
        self.max_health = 150
        self.damage = 8
        self.attack_range = 50
        
        # Movement
        self.speed = 2.5
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
        
        # Load sprites
        self._load_sprites()
        
        # AI behavior
        self.patrol_left_bound = x - 150
        self.patrol_right_bound = x + 150
        self.is_attacking = False
        self.attack_cooldown = 0
        self.attack_cooldown_max = 80
    
    def _load_sprites(self):
        """Load all Onre sprite sheets from assets folder."""
        base_path = os.path.join("assets", "NPC", "Onre")
        
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
    
    def update(self, delta_time=1):
        """
        Update Onre NPC state, animation, and movement.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Update animation
        self._update_animation()
        
        # Update cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            # Reset is_attacking when cooldown expires
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
        """Update Onre movement with patrol behavior."""
        self.x += self.velocity_x
        
        # Check patrol boundaries and reverse direction
        if self.x <= self.patrol_left_bound:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
        elif self.x >= self.patrol_right_bound:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
    
    def move_left(self):
        """Move Onre to the left."""
        if self.state not in [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.ATTACK_3, 
                               NPCState.HURT, NPCState.DEAD]:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
    
    def move_right(self):
        """Move Onre to the right."""
        if self.state not in [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.ATTACK_3, 
                               NPCState.HURT, NPCState.DEAD]:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
    
    def stop(self):
        """Stop Onre movement."""
        self.velocity_x = 0
    
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
    
    def take_damage(self, amount):
        """
        Apply damage to Onre.
        
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
        """Render Onre sprite to screen using PySDL2."""
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
        """Check if Onre is still alive."""
        return self.health > 0
    
    def cleanup(self):
        """Clean up loaded textures."""
        for texture in self.textures.values():
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.textures.clear()
        self.sprites.clear()


class NPCManager:
    """
    Manager class for handling multiple NPCs.
    """
    
    def __init__(self, sprite_factory, texture_factory, renderer):
        """
        Initialize NPC Manager.
        
        Args:
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
        """
        self.npcs = []
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
    
    def spawn_ghost(self, x, y):
        """
        Spawn a new Ghost NPC.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            
        Returns:
            Ghost: The spawned Ghost instance
        """
        ghost = Ghost(x, y, self.sprite_factory, self.texture_factory, self.renderer)
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
