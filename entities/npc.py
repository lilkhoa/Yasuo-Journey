import os
import ctypes
import sdl2
import sdl2.ext
import sdl2.sdlmixer
import random
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
    NPC_ONRE_PATROL_RADIUS,
    NPC_ONRE_ATTACK_COOLDOWN,
    GRAVITY,
    MAX_FALL_SPEED,
    GROUND_Y
)


class NPCState(Enum):
    """Enumeration for NPC states."""
    IDLE = "Idle"
    WALK = "Walk"
    RUN = "Run"
    CHASE = "Chase"
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
    
    Attributes:
        x, y: Current position coordinates
        spawn_x, spawn_y: Initial spawn position (used for return behavior)
        width, height: Sprite dimensions
        health: Current health points
        max_health: Maximum health points
        damage: Attack damage
        attack_range: Attack range in pixels (from NPC center)
        detection_range: Player detection range in pixels (from spawn position)
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
        player: Reference to player object (for chase behavior)
        is_chasing: Flag indicating if currently chasing player
        returning_to_spawn: Flag indicating if returning to spawn after chase
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
        self.spawn_x = x
        self.spawn_y = y
        self.width = 96
        self.height = 96
        
        # Combat stats
        self.health = health
        self.max_health = health
        self.damage = damage
        self.attack_range = attack_range
        self.detection_range = detection_range
        self.vertical_detection_range = self.height - 20
        
        # Movement
        self.speed = speed
        self.direction = Direction.RIGHT
        self.velocity_x = self.speed
        self.velocity_y = 0
        self.is_flying = False
        self.ground_y = GROUND_Y
        
        # State and animation
        self.state = NPCState.WALK
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
        
        # Patrol behavior with random idle stops
        self.is_patrolling = False
        self.patrol_idle_timer = 0
        self.patrol_idle_duration_min = 60
        self.patrol_idle_duration_max = 180
        self.patrol_idle_chance = 0.008
        self.was_patrolling_before_idle = False
        self.patrol_reversals_count = 0
        
        # Projectile system (can be set by child classes)
        self.projectile_manager = None
        
        # Player interaction
        self.player = None
        
        # Chase behavior
        self.is_chasing = False
        self.chase_hysteresis_buffer = 50
        self.returning_to_spawn = False
        self.return_threshold = 20
        
        # Death state management
        self.death_animation_complete = False
        self.death_timer = 0
        self.death_removal_delay = 90
        self.ready_for_removal = False
        
        # Hurt state management (Phase 2: stunned)
        self.hurt_animation_complete = False
        
        # Death callback (for coin drops, etc.)
        self.on_death_callback = None
        
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
    
    def update(self, delta_time=1, game_map=None):
        """
        Update NPC state, animation, and movement.
        
        Args:
            delta_time: Time elapsed since last update
            game_map: GameMap instance for tile collision
        """
        if self.state == NPCState.DEAD:
            self._update_animation()
            
            if self.death_animation_complete:
                self.ready_for_removal = True
            
            return
        
        if self.health <= 0:
            self.health = 0
            self.state = NPCState.DEAD
            self.current_frame = 0
            self.death_animation_complete = False
            self.velocity_x = 0
            return
        
        if self.state == NPCState.HURT:
            self._update_animation()
            
            if self.hurt_animation_complete:
                self.hurt_animation_complete = False
                self.current_frame = 0
                self.frame_counter = 0
                
                if self.is_patrolling:
                    self.state = NPCState.WALK
                    self.velocity_x = self.speed if self.direction == Direction.RIGHT else -self.speed
                else:
                    self.state = NPCState.IDLE
                    self.velocity_x = 0
            else:
                return
        
        # Normal animation update for all other states
        self._update_animation()
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown == 0:
                self.is_attacking = False
        
        # Check for player detection and chase behavior (AI active)
        if self.player and not self.is_attacking:
            self._check_player_detection()
        
        # Update movement for movement states
        if self.state in [NPCState.WALK, NPCState.RUN, NPCState.IDLE, NPCState.CHASE]:
            self._update_movement()
            
        # --- GRAVITY & PHYSICS ---
        if not self.is_flying:
            self.velocity_y += GRAVITY
            if self.velocity_y > MAX_FALL_SPEED:
                self.velocity_y = MAX_FALL_SPEED
                
            self.y += self.velocity_y
            
            # Tile-based ground collision
            on_ground = False
            if game_map:
                npc_rect = sdl2.SDL_Rect(int(self.x), int(self.y), self.width, self.height)
                nearby_tiles = game_map.get_tile_rects_around(int(self.x), int(self.y), self.width, self.height)
                
                for tile in nearby_tiles:
                    if sdl2.SDL_HasIntersection(npc_rect, tile):
                        if self.velocity_y >= 0:  # Falling or standing
                            self.y = tile.y - self.height
                            self.velocity_y = 0
                            self.ground_y = tile.y - self.height
                            on_ground = True
                            break
                
                # Feet sensor for stability
                if not on_ground and self.velocity_y >= 0:
                    feet_rect = sdl2.SDL_Rect(int(self.x) + 10, int(self.y) + self.height, self.width - 20, 4)
                    for tile in nearby_tiles:
                        if sdl2.SDL_HasIntersection(feet_rect, tile):
                            snap_y = tile.y - self.height
                            if abs(self.y - snap_y) <= 8:
                                self.y = snap_y
                                self.velocity_y = 0
                                self.ground_y = snap_y
                                on_ground = True
                                break
            
            # Fallback: GROUND_Y safety net
            if not on_ground and self.y >= GROUND_Y:
                self.y = GROUND_Y
                self.velocity_y = 0
                
    def apply_knockup(self, force=-10):
        """Apply vertical knockup force."""
        if not self.is_flying:
            self.velocity_y = force
            self.y += force # Apply immediately to lift off ground
    
    def _update_animation(self):
        """Update animation frame based on current state."""
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        
        # Handle DEAD animation (play once, hold last frame)
        if self.state == NPCState.DEAD:
            if not self.death_animation_complete:
                self.frame_counter += self.animation_speed
                
                if self.frame_counter >= 1.0:
                    self.frame_counter = 0
                    self.current_frame += 1
                    
                    if self.current_frame >= sprite_data['frames']:
                        self.current_frame = sprite_data['frames'] - 1
                        self.death_animation_complete = True
            return
        
        if self.state == NPCState.HURT:
            if not self.hurt_animation_complete:
                self.frame_counter += self.animation_speed
                
                if self.frame_counter >= 1.0:
                    self.frame_counter = 0
                    self.current_frame += 1
                    
                    if self.current_frame >= sprite_data['frames']:
                        self.current_frame = sprite_data['frames'] - 1
                        self.hurt_animation_complete = True
            return
        
        # Normal looping animation for all other states
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % sprite_data['frames']
    
    def _update_movement(self):
        """Update NPC movement with patrol, chase, and return behaviors."""
        # Handle chase behavior
        if self.is_chasing and self.state == NPCState.CHASE:
            self._chase_player()
            return
        
        # Handle return to spawn after chase
        if self.returning_to_spawn:
            self._return_to_spawn()
            return
        
        # Handle normal patrol behavior
        if not self.is_patrolling:
            self.x += self.velocity_x
            return
        
        if self.patrol_idle_timer > 0:
            self.patrol_idle_timer -= 1
            
            if self.patrol_idle_timer == 0:
                self.state = NPCState.WALK
                self.velocity_x = self.speed if self.direction == Direction.RIGHT else -self.speed
                self.patrol_reversals_count = 0
            return
        
        self.x += self.velocity_x
        
        if self.x <= self.patrol_left_bound:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
            self.patrol_reversals_count += 1
        elif self.x >= self.patrol_right_bound:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
            self.patrol_reversals_count += 1
        
        if self.state == NPCState.WALK and self.patrol_reversals_count >= 2 and random.random() < self.patrol_idle_chance:
            self._start_patrol_idle()
    
    def _start_patrol_idle(self):
        """Start a random idle period during patrol."""
        self.state = NPCState.IDLE
        self.velocity_x = 0
        self.patrol_idle_timer = random.randint(self.patrol_idle_duration_min, self.patrol_idle_duration_max)
        self.was_patrolling_before_idle = True
    
    def _check_player_detection(self):
        """Check if player is within detection range and update chase state."""
        if not self.player or not hasattr(self.player, 'x'):
            return
        
        # Calculate detection area bounds relative to spawn position
        detection_left = self.spawn_x - self.detection_range
        detection_right = self.spawn_x + self.detection_range
        
        player_x = self.player.x + self.player.width / 2
        
        # Check if player is within detection area
        player_in_detection = detection_left <= player_x <= detection_right
        distance_y = abs((self.player.y + self.player.height / 2) - (self.y + self.height / 2))
        is_on_same_vertical_level = distance_y <= self.vertical_detection_range
        
        if not self.is_chasing and player_in_detection and is_on_same_vertical_level:
            # Player entered detection area - start chasing
            self._start_chase()
        elif self.is_chasing:
            # Add hysteresis buffer to prevent jittery behavior at boundary
            buffer_left = detection_left - self.chase_hysteresis_buffer
            buffer_right = detection_right + self.chase_hysteresis_buffer

            player_out_of_x = not (buffer_left <= player_x <= buffer_right)
            player_out_of_y = not is_on_same_vertical_level
            
            if player_out_of_x or player_out_of_y:
                self._stop_chase()
            else:
                # Player still in detection range - check distance
                distance_to_player = abs(self.x + self.width / 2 - player_x)
                distance_y = abs((self.player.y + self.player.height / 2) - (self.y + self.height / 2))
                
                if distance_to_player <= self.attack_range and distance_y <= self.vertical_detection_range:
                    # Player in attack range - update direction to face player before attacking
                    if not self.is_attacking and self.attack_cooldown == 0:
                        # Update direction to face player
                        npc_center_x = self.x + self.width / 2
                        if player_x > npc_center_x:
                            self.direction = Direction.RIGHT
                        else:
                            self.direction = Direction.LEFT
                        self._attack_player()
                else:
                    # Player out of attack range - continue chasing if not attacking
                    if not self.is_attacking and self.state != NPCState.CHASE:
                        self.state = NPCState.CHASE
    
    def _start_chase(self):
        """Start chasing the player."""
        self.is_chasing = True
        self.returning_to_spawn = False
        # Don't stop patrol mode - we'll resume after chase
        self.state = NPCState.CHASE
        self.patrol_idle_timer = 0
    
    def _stop_chase(self):
        """Stop chasing and resume patrol from current position."""
        self.is_chasing = False
        self.returning_to_spawn = False  # Don't return to spawn, patrol from current position
        self.patrol_reversals_count = 0  # Reset patrol cycle
        self.state = NPCState.WALK
        # Set velocity based on current direction to resume patrol
        self.velocity_x = self.speed if self.direction == Direction.RIGHT else -self.speed
    
    def _chase_player(self):
        """Move toward the player during chase."""
        if not self.player or not hasattr(self.player, 'x'):
            return
        
        player_center_x = self.player.x + self.player.width / 2
        npc_center_x = self.x + self.width / 2
        
        # Determine direction to player
        if player_center_x > npc_center_x:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed * 1.5  # Chase slightly faster than patrol
        else:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed * 1.5
        
        # Move toward player
        self.x += self.velocity_x
    
    def _return_to_spawn(self):
        """Return to spawn position after chase ends."""
        distance_to_spawn = abs(self.x - self.spawn_x)
        
        # Check if arrived at spawn position
        if distance_to_spawn <= self.return_threshold:
            # Arrived at spawn - resume patrol
            self.x = self.spawn_x
            self.returning_to_spawn = False
            self.patrol_reversals_count = 0  # Reset patrol cycle
            # Always resume patrol after chase
            self.state = NPCState.WALK
            # Choose a consistent patrol direction (e.g., always start going right)
            # This prevents jitter from arbitrary direction based on return path
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
            return
        
        # Move toward spawn position
        if self.x > self.spawn_x:
            self.direction = Direction.LEFT
            self.velocity_x = -self.speed
        else:
            self.direction = Direction.RIGHT
            self.velocity_x = self.speed
        
        self.x += self.velocity_x
        
        self.x += self.velocity_x
    
    def _attack_player(self):
        """Initiate attack on player (to be implemented by subclasses)."""
        # Default implementation - can be overridden
        self.attack(attack_type=1)
    
    def start_patrol(self):
        """Enable patrol mode for this NPC."""
        self.is_patrolling = True
        self.patrol_reversals_count = 0
        if self.state not in self._get_non_interruptible_states():
            self.state = NPCState.WALK
            self.velocity_x = self.speed if self.direction == Direction.RIGHT else -self.speed
    
    def stop_patrol(self):
        """Disable patrol mode for this NPC."""
        self.is_patrolling = False
        self.patrol_idle_timer = 0
    
    def set_player(self, player):
        """
        Set the player reference for chase behavior.
        
        Args:
            player: Player instance with x, y, width, height attributes
        """
        self.player = player
    
    def set_on_death_callback(self, callback):
        """
        Set the callback function to be called when NPC dies.
        
        Args:
            callback: Function to call on death, receives self as argument
        """
        self.on_death_callback = callback
    
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
        Phase 1: Instant damage impact.
        
        Args:
            amount: Damage amount to apply
        """
        if self.state == NPCState.DEAD:
            return
        
        self.health -= amount
        
        if self.health > 0:
            self.state = NPCState.HURT
            self.current_frame = 0
            self.frame_counter = 0
            self.hurt_animation_complete = False
            self.velocity_x = 0
            
            # Clear chase and attack states to ensure clean recovery
            self.is_chasing = False
            self.returning_to_spawn = False
            self.is_attacking = False
            self.attack_cooldown = 0
        else:
            self.health = 0
            self.state = NPCState.DEAD
            self.current_frame = 0
            self.death_animation_complete = False
            self.velocity_x = 0
            
            # Trigger death callback (for coin drops, etc.)
            if self.on_death_callback:
                self.on_death_callback(self)
    
    def render(self, camera_x=0, camera_y=0):
        """Render NPC sprite to screen using PySDL2.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        texture = sprite_data['texture']
        
        frame_width = sprite_data['width'] // sprite_data['frames']
        frame_height = sprite_data['height']
        
        src_rect = sdl2.SDL_Rect(
            self.current_frame * frame_width,
            0,
            frame_width,
            frame_height
        )
        
        # Apply camera offset for screen rendering (world-space to screen-space)
        dest_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        
        flip = sdl2.SDL_FLIP_NONE
        if self.direction == Direction.LEFT:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
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
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, projectile_manager=None, sound_manager=None):
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
        
        self.is_flying = True
        self.projectile_manager = projectile_manager
        self.projectile_fired_this_attack = False
        self.sound_manager = sound_manager
        self.attack_sound = None
        self._load_attack_sound()
    
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
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
        
        # CHASE state reuses RUN sprite
        if NPCState.RUN in self.sprites:
            self.sprites[NPCState.CHASE] = self.sprites[NPCState.RUN]
    
    def _calculate_frames(self, state):
        """
        Calculate number of frames in a sprite sheet.
        Based on user specifications.
        """
        frame_counts = {
            NPCState.IDLE: 5,
            NPCState.WALK: 5,
            NPCState.RUN: 5,
            NPCState.CHASE: 5,  # Reuses RUN animation
            NPCState.ATTACK_3: 7,
            NPCState.ATTACK_4: 7,
            NPCState.HURT: 3,
            NPCState.DEAD: 4
        }
        return frame_counts.get(state, 1)
    
    def _get_non_interruptible_states(self):
        """Get list of states that cannot be interrupted for Ghost."""
        return [NPCState.ATTACK_3, NPCState.ATTACK_4, NPCState.HURT, NPCState.DEAD]
    
    def _load_attack_sound(self):
        """Load Ghost attack sound effect."""
        if not self.sound_manager:
            return
        sound_path = os.path.join("assets", "NPC", "Ghost", "attack_sound.mp3")
        self.sound_manager.load_sound("ghost_attack", sound_path)
        self.attack_sound = self.sound_manager.get_sound("ghost_attack")
    
    def update(self, delta_time=1, game_map=None):
        """
        Update Ghost NPC with projectile firing logic.
        
        Args:
            delta_time: Time elapsed since last update
            game_map: GameMap instance for tile collision
        """
        # Call parent update
        super().update(delta_time, game_map)
        
        if self.is_attacking and not self.projectile_fired_this_attack:
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
        offset_x = 50 if self.direction == Direction.RIGHT else 5
        proj_x = self.x + offset_x
        proj_y = self.y + 20
        
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
        
        # Play attack sound
        if self.attack_sound:
            sdl2.sdlmixer.Mix_PlayChannel(-1, self.attack_sound, 0)


class Shooter(NPC):
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, projectile_manager=None, sound_manager=None):
        """
        Initialize Shooter NPC.
        
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
            health=NPC_SHOOTER_HEALTH,
            damage=NPC_SHOOTER_DAMAGE,
            attack_range=NPC_SHOOTER_ATTACK_RANGE,
            detection_range=NPC_SHOOTER_DETECTION_RANGE,
            speed=NPC_SHOOTER_SPEED,
            patrol_radius=NPC_SHOOTER_PATROL_RADIUS,
            attack_cooldown_max=NPC_SHOOTER_ATTACK_COOLDOWN
        )
        
        # Set projectile manager for firing projectiles
        self.projectile_manager = projectile_manager
        
        # Track which frame to fire projectile (mid-attack animation)
        self.projectile_fired_this_attack = False
        
        # Load attack sound
        self.sound_manager = sound_manager
        self.attack_sound = None
        self._load_attack_sound()
    
    def _load_attack_sound(self):
        """Load Shooter attack sound effect."""
        if not self.sound_manager:
            return
        sound_path = os.path.join("assets", "NPC", "Shooter", "attack_sound.mp3")
        self.sound_manager.load_sound("shooter_attack", sound_path)
        self.attack_sound = self.sound_manager.get_sound("shooter_attack")
    
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
        
        # CHASE state reuses RUN sprite
        if NPCState.RUN in self.sprites:
            self.sprites[NPCState.CHASE] = self.sprites[NPCState.RUN]
    
    def _calculate_frames(self, state):
        """
        Calculate number of frames in a sprite sheet.
        Based on user specifications.
        """
        frame_counts = {
            NPCState.IDLE: 7,
            NPCState.WALK: 7,
            NPCState.RUN: 8,
            NPCState.CHASE: 8,  # Reuses RUN animation
            NPCState.ATTACK_1: 4,
            NPCState.ATTACK_2: 4,
            NPCState.HURT: 3,
            NPCState.DEAD: 4
        }
        return frame_counts.get(state, 1)
    
    def _get_non_interruptible_states(self):
        """Get list of states that cannot be interrupted for Shooter."""
        return [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.HURT, NPCState.DEAD]
    
    def update(self, delta_time=1, game_map=None):
        """
        Update Shooter NPC with projectile firing logic.
        
        Args:
            delta_time: Time elapsed since last update
            game_map: GameMap instance for tile collision
        """
        # Call parent update
        super().update(delta_time, game_map)
        
        # Fire projectile at appropriate frame during attack animation
        if self.is_attacking and not self.projectile_fired_this_attack:
            # Fire projectile at frame 2 for both Attack_1 and Attack_2
            if self.current_frame >= 2:
                if self.state == NPCState.ATTACK_1:
                    self._fire_projectile(attack_type=1)
                elif self.state == NPCState.ATTACK_2:
                    self._fire_projectile(attack_type=2)
                self.projectile_fired_this_attack = True
        
        # Reset projectile flag when attack ends
        if not self.is_attacking:
            self.projectile_fired_this_attack = False
    
    def _fire_projectile(self, attack_type):
        """
        Fire a projectile from the Shooter.
        
        Args:
            attack_type: 1 for Attack_1, 2 for Attack_2
        """
        if not self.projectile_manager:
            return
        
        # Calculate projectile spawn position (in front of Shooter)
        offset_x = 25 if self.direction == Direction.RIGHT else 5
        proj_x = self.x + offset_x
        proj_y = self.y + 25
        
        direction = 1 if self.direction == Direction.RIGHT else -1
        
        # Spawn the projectile through the manager
        self.projectile_manager.spawn_shooter_projectile(
            proj_x, proj_y, direction, self, attack_type
        )
    
    def attack(self, attack_type=1):
        """
        Initiate a ranged attack with automatic projectile firing.
        
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
        self.projectile_fired_this_attack = False  # Reset for new attack
        
        # Play attack sound
        if self.attack_sound:
            sdl2.sdlmixer.Mix_PlayChannel(-1, self.attack_sound, 0)


class Onre(NPC):
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, sound_manager=None):
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
        self.current_attack_cycle = 1
        self.has_dealt_damage = False  # Flag to prevent multiple hits in one attack
        
        # Melee hitbox configuration
        self.melee_hitbox_width = 20
        self.melee_hitbox_height = 60
        self.melee_hitbox_offset = 20
        self.is_flying = True
        # Dangerous frames for each attack type
        self.dangerous_frames_map = {
            NPCState.ATTACK_1: [2, 3, 4],
            NPCState.ATTACK_2: [1, 2, 3],
            NPCState.ATTACK_3: [1, 2, 3]
        }
        
        self.sound_manager = sound_manager
        self.attack_sounds = [None, None, None]
        self._load_attack_sounds()
    
    def _get_npc_folder_name(self):
        """Load Onre's three attack sound effects."""
        base_path = os.path.join("assets", "NPC", "Onre")
        
        for i in range(3):
            sound_path = os.path.join(base_path, f"attack_sound_{i+1}.mp3")
            if os.path.exists(sound_path):
                try:
                    self.attack_sounds[i] = sdl2.sdlmixer.Mix_LoadWAV(sound_path.encode('utf-8'))
                except Exception as e:
                    print(f"[Onre] Error loading attack sound {i+1}: {e}")
            else:
                print(f"[Onre] Attack sound {i+1} not found at {sound_path}")
    
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
        
        # CHASE state reuses RUN sprite
        if NPCState.RUN in self.sprites:
            self.sprites[NPCState.CHASE] = self.sprites[NPCState.RUN]
    
    def _calculate_frames(self, state):
        """
        Calculate number of frames in a sprite sheet.
        Based on user specifications.
        """
        frame_counts = {
            NPCState.IDLE: 6,
            NPCState.WALK: 7,
            NPCState.RUN: 7,
            NPCState.CHASE: 7,  # Reuses RUN animation
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
    
    def _load_attack_sounds(self):
        if not self.sound_manager:
            return
        for i in range(3):
            sound_path = os.path.join("assets", "NPC", "Onre", f"attack_sound_{i+1}.mp3")
            self.sound_manager.load_sound(f"onre_attack{i+1}", sound_path)
            self.attack_sounds[i] = self.sound_manager.get_sound(f"onre_attack{i+1}")
    
    def update(self, delta_time=1, game_map=None):
        """Update Onre NPC with melee hitbox collision detection."""
        # Call parent update
        super().update(delta_time, game_map)
        
        # Check melee hitbox during attack animation
        if self.is_attacking and self.player:
            self._check_melee_hit()
    
    def _calculate_melee_hitbox(self):
        """Calculate melee hitbox rectangle based on current position and direction.
        
        Returns:
            sdl2.SDL_Rect: The hitbox rectangle
        """
        if self.direction == Direction.RIGHT:
            hitbox_x = self.x + self.width / 2 + self.melee_hitbox_offset
        else:
            hitbox_x = self.x + self.width / 2 - self.melee_hitbox_offset - self.melee_hitbox_width
        
        hitbox_y = self.y + (self.height - self.melee_hitbox_height) / 2
        
        return sdl2.SDL_Rect(
            int(hitbox_x),
            int(hitbox_y),
            self.melee_hitbox_width,
            self.melee_hitbox_height
        )
    
    def _check_melee_hit(self):
        """Check if blade hitbox collides with player during dangerous frames."""
        # Only check during attack states
        if self.state not in [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.ATTACK_3]:
            return
        
        # Only deal damage once per attack
        if self.has_dealt_damage:
            return
        
        # Check if current frame is dangerous
        if self.current_frame not in self.dangerous_frames_map.get(self.state, []):
            return
        
        # Calculate hitbox using helper method
        hitbox = self._calculate_melee_hitbox()
        
        # Create player rectangle
        player_rect = sdl2.SDL_Rect(
            int(self.player.x),
            int(self.player.y),
            int(self.player.width),
            int(self.player.height)
        )
        
        # Check collision using SDL's built-in function
        if sdl2.SDL_HasIntersection(hitbox, player_rect):
            self.player.take_damage(self.damage)
            self.has_dealt_damage = True
    
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
        self.state = attack_states.get(self.current_attack_cycle, NPCState.ATTACK_1)
        self.current_frame = 0
        self.is_attacking = True
        self.attack_cooldown = self.attack_cooldown_max
        self.velocity_x = 0
        self.has_dealt_damage = False  # Reset damage flag for new attack
        
        # Play attack sound corresponding to current attack cycle through sound manager
        if self.sound_manager:
            sound_id = f"onre_attack{self.current_attack_cycle}"
            self.sound_manager.play_sound(sound_id)
        
        self.current_attack_cycle = (self.current_attack_cycle % 3) + 1


class NPCManager:
    def __init__(self, sprite_factory, texture_factory, renderer, projectile_manager=None, sound_manager=None):
        """
        Initialize NPC Manager.
        
        Args:
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            projectile_manager: ProjectileManager instance for NPC projectiles (optional)
            sound_manager: SoundManager instance for audio (optional)
        """
        self.npcs = []
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
        self.projectile_manager = projectile_manager
        self.sound_manager = sound_manager
    
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
                     self.renderer, self.projectile_manager, self.sound_manager)
        ghost.start_patrol()  # Auto-start patrol with spawn position as center
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
        shooter = Shooter(x, y, self.sprite_factory, self.texture_factory,
                         self.renderer, self.projectile_manager, self.sound_manager)
        shooter.start_patrol()  # Auto-start patrol with spawn position as center
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
        onre = Onre(x, y, self.sprite_factory, self.texture_factory, self.renderer, self.sound_manager)
        onre.start_patrol()  # Auto-start patrol with spawn position as center
        self.npcs.append(onre)
        return onre
    
    def update_all(self, delta_time=1, game_map=None):
        """Update all NPCs and clean up those marked for removal."""
        for npc in self.npcs:
            npc.update(delta_time, game_map)
        
        # Remove NPCs that are marked for removal (dead + delay passed)
        npcs_to_remove = [npc for npc in self.npcs if npc.ready_for_removal]
        for npc in npcs_to_remove:
            npc.cleanup()  # Clean up textures before removal
        
        # Keep only NPCs not marked for removal
        self.npcs = [npc for npc in self.npcs if not npc.ready_for_removal]
    
    def render_all(self, camera_x=0, camera_y=0):
        """Render all NPCs.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        for npc in self.npcs:
            npc.render(camera_x, camera_y)
    
    def cleanup(self):
        """Clean up all NPCs."""
        for npc in self.npcs:
            npc.cleanup()
        self.npcs.clear()
