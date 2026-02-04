"""
Projectile Module - NPC Projectile System
Handles projectile behavior, animations, and collision using PySDL2.
"""
import os
import ctypes
import sdl2
import sdl2.ext
from enum import Enum
from settings import (
    NPC_GHOST_DAMAGE,
    NPC_GHOST_PROJECTILE_SPEED,

    NPC_SHOOTER_DAMAGE,
    NPC_SHOOTER_PROJECTILE_SPEED,
)


class ProjectileType(Enum):
    """Enumeration for projectile types."""
    GHOST_CHARGE_1 = "Ghost_Charge_1"
    GHOST_CHARGE_2 = "Ghost_Charge_2"
    SHOOTER_ATTACK_1 = "Shooter_Attack_1"
    SHOOTER_ATTACK_2 = "Shooter_Attack_2"


class Projectile:
    """
    Base projectile class with animation and movement.
    
    Attributes:
        x, y: Position coordinates
        width, height: Sprite dimensions
        velocity_x, velocity_y: Movement velocity
        damage: Damage dealt on hit
        direction: Movement direction (1 for right, -1 for left)
        active: Whether projectile is still active
        owner: Reference to the entity that fired this projectile
        texture: SDL2 texture for rendering
        sprite_data: Dictionary containing sprite sheet information
        current_frame: Current animation frame
        animation_speed: Frame update rate
        frame_counter: Counter for animation timing
    """
    
    def __init__(self, x, y, velocity_x, velocity_y, damage, direction, owner, renderer):
        """
        Initialize base projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            velocity_x: Horizontal velocity
            velocity_y: Vertical velocity
            damage: Damage value
            direction: Direction (1 for right, -1 for left)
            owner: The entity that fired this projectile
            renderer: PySDL2 renderer
        """
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.damage = damage
        self.direction = direction
        self.active = True
        self.owner = owner
        self.renderer = renderer
        
        # Animation
        self.texture = None
        self.sprite_data = {}
        self.current_frame = 0
        self.animation_speed = 0.2
        self.frame_counter = 0
        
        # Lifetime (frames until auto-destroy)
        self.lifetime = 180  # 3 seconds at 60 FPS
        self.age = 0
    
    def update(self, delta_time=1):
        """
        Update projectile position and animation.
        
        Args:
            delta_time: Time elapsed since last update (not used for movement - speeds are per-frame)
        """
        if not self.active:
            return
        
        # Update position (speeds are already in pixels-per-frame)
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Update animation
        self._update_animation()
        
        # Update lifetime
        self.age += 1
        if self.age >= self.lifetime:
            self.active = False
        
        # Check if off-screen (simple bounds check)
        if self.x < -100 or self.x > 1400 or self.y < -100 or self.y > 900:
            self.active = False
    
    def _update_animation(self):
        """Update animation frame."""
        if not self.sprite_data or 'frames' not in self.sprite_data:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % self.sprite_data['frames']
    
    def render(self, camera_x=0, camera_y=0):
        """Render projectile sprite.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        if not self.active or not self.texture:
            return
        
        # Calculate source rectangle (current frame in sprite sheet)
        frame_width = self.sprite_data['width'] // self.sprite_data['frames']
        frame_height = self.sprite_data['height']
        
        src_rect = sdl2.SDL_Rect(
            self.current_frame * frame_width,
            0,
            frame_width,
            frame_height
        )
        
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
            self.texture,
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
        tx, ty, tw, th = target.get_bounds()
        
        # AABB collision detection
        return (px < tx + tw and
                px + pw > tx and
                py < ty + th and
                py + ph > ty)
    
    def on_hit(self):
        """Called when projectile hits something."""
        self.active = False
    
    def cleanup(self):
        """Clean up resources."""
        if self.texture:
            sdl2.SDL_DestroyTexture(self.texture)
            self.texture = None


class GhostProjectile(Projectile):
    """
    Ghost NPC projectile with charge animations.
    
    Supports two types:
    - Charge_1: 3 frames (for Attack_3)
    - Charge_2: 4 frames (for Attack_4)
    """
    
    def __init__(self, x, y, direction, owner, renderer, charge_type=1):
        """
        Initialize Ghost projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Ghost that fired this projectile
            renderer: PySDL2 renderer
            charge_type: Type of charge (1 or 2)
        """
        # Base velocity (will be multiplied by direction)
        velocity_x = NPC_GHOST_PROJECTILE_SPEED * direction
        velocity_y = 0
        damage = NPC_GHOST_DAMAGE
        
        super().__init__(x, y, velocity_x, velocity_y, damage, direction, owner, renderer)
        
        self.charge_type = charge_type
        self.width = 32
        self.height = 32
        
        # Load sprite
        self._load_sprite()
    
    def _load_sprite(self):
        """Load Ghost projectile sprite sheet."""
        base_path = os.path.join("assets", "Projectile", "Ghost")
        
        # Select sprite file based on charge type
        if self.charge_type == 1:
            filename = "Charge_1.png"
            frames = 3
        else:
            filename = "Charge_2.png"
            frames = 4
        
        filepath = os.path.join(base_path, filename)
        
        if os.path.exists(filepath):
            try:
                # Load texture
                surface = sdl2.ext.load_image(filepath)
                self.texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                sdl2.SDL_FreeSurface(surface)
                
                if self.texture:
                    # Get texture dimensions
                    w = ctypes.c_int()
                    h = ctypes.c_int()
                    sdl2.SDL_QueryTexture(self.texture, None, None, ctypes.byref(w), ctypes.byref(h))
                    
                    self.sprite_data = {
                        'texture': self.texture,
                        'width': w.value,
                        'height': h.value,
                        'frames': frames
                    }
                    
                    print(f"Loaded Ghost {filename}: {w.value}x{h.value} pixels, {frames} frames")
            except Exception as e:
                print(f"Failed to load {filepath}: {e}")
        else:
            print(f"Warning: Ghost projectile sprite not found: {filepath}")

class ShooterProjectile(Projectile):
    """
    Shooter NPC projectile with individual frame animations.
    
    Uses 8 separate image files (1.png through 8.png) for animation.
    Both attack types use the same projectile animation.
    """
    
    def __init__(self, x, y, direction, owner, renderer, attack_type=1):
        """
        Initialize Shooter projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            direction: Direction (1 for right, -1 for left)
            owner: The Shooter that fired this projectile
            renderer: PySDL2 renderer
            attack_type: Type of attack (1 or 2)
        """
        # Base velocity (will be multiplied by direction)
        velocity_x = NPC_SHOOTER_PROJECTILE_SPEED * direction
        velocity_y = 0
        damage = NPC_SHOOTER_DAMAGE
        
        super().__init__(x, y, velocity_x, velocity_y, damage, direction, owner, renderer)
        
        self.attack_type = attack_type
        self.width = 32
        self.height = 32
        
        # Load individual frame textures
        self.frame_textures = []
        self._load_frames()
    
    def _load_frames(self):
        """Load all 8 individual frame images."""
        base_path = os.path.join("assets", "Projectile", "Shooter")
        
        # Load frames 1-8
        for i in range(1, 9):
            filename = f"{i}.png"
            filepath = os.path.join(base_path, filename)
            
            if os.path.exists(filepath):
                try:
                    # Load texture
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Shooter projectile frame not found: {filepath}")
        
        if self.frame_textures:
            # Set sprite data using first frame dimensions
            w = ctypes.c_int()
            h = ctypes.c_int()
            sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                 ctypes.byref(w), ctypes.byref(h))
            
            self.sprite_data = {
                'frames': len(self.frame_textures),
                'width': w.value,
                'height': h.value
            }
            
            print(f"Loaded Shooter projectile: {len(self.frame_textures)} frames, {w.value}x{h.value} pixels")
        else:
            print("Error: No Shooter projectile frames loaded!")
    
    def _update_animation(self):
        """Update animation frame for individual textures."""
        if not self.frame_textures:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_textures)
    
    def render(self, camera_x=0, camera_y=0):
        """Render Shooter projectile with individual frame textures.
        
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
        flip = sdl2.SDL_FLIP_HORIZONTAL
        if self.direction < 0:
            flip = sdl2.SDL_FLIP_NONE
        
        # Render (no source rect needed for individual frames)
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            None,  # Use entire texture
            dest_rect,
            0,
            None,
            flip
        )
    
    def cleanup(self):
        """Clean up all frame textures."""
        for texture in self.frame_textures:
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.frame_textures.clear()


class BossMeleeEffect(Projectile):
    """
    Boss melee attack visual effect.
    
    This is not a true projectile but a visual effect that appears in front of the boss
    during melee attacks. Uses a rectangular hitbox extending in the direction the boss
    is facing to make it easier for players to avoid (since player can only move left/right).
    """
    
    def __init__(self, x, y, direction, owner, renderer, damage, preloaded_textures=None):
        """
        Initialize Boss melee effect.
        
        Args:
            x: Initial x position (boss center)
            y: Initial y position (boss center)
            direction: Direction (1 for right, -1 for left)
            owner: The Boss entity
            renderer: PySDL2 renderer
            damage: Damage value
            preloaded_textures: List of preloaded textures (optional)
        """
        # No velocity - melee effect is stationary relative to boss
        velocity_x = 0
        velocity_y = 0
        
        super().__init__(x, y, velocity_x, velocity_y, damage, direction, owner, renderer)
        
        # Rectangular hitbox dimensions - extends in front of boss
        # Wide but not too tall to allow dodging by moving left/right
        self.width = 120  # Extends forward
        self.height = 1024  # Vertical range
        
        # Adjust position based on direction
        if direction > 0:
            # Facing right - effect appears to the right of boss
            self.x = x
        else:
            # Facing left - effect appears to the left of boss
            self.x = x - self.width
        
        # Center vertically
        self.y = y - self.height // 2
        
        # Short lifetime - melee effect only lasts a few frames
        self.lifetime = 15  # 0.25 seconds at 60 FPS
        self.age = 0
        
        # Track which targets have been hit to prevent multiple hits
        self.hit_targets = set()
        
        # Load or use preloaded melee effect sprites
        self.frame_textures = []
        if preloaded_textures:
            # Use preloaded textures (no disk I/O - prevents lag)
            self.frame_textures = preloaded_textures
            if self.frame_textures:
                w = ctypes.c_int()
                h = ctypes.c_int()
                sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                     ctypes.byref(w), ctypes.byref(h))
                self.sprite_data = {
                    'frames': len(self.frame_textures),
                    'width': w.value,
                    'height': h.value
                }
                # Fast animation speed for quick melee effect
                self.animation_speed = 0.6
        else:
            # Fallback: load from disk (will cause lag)
            self._load_frames()
    
    def _load_frames(self):
        """Load all melee effect frame images."""
        base_path = os.path.join("assets", "Projectile", "Boss", "Melee")
        
        # Load frames 1-10 (based on directory listing)
        for i in range(1, 11):
            filename = f"{i}.png"
            filepath = os.path.join(base_path, filename)
            
            if os.path.exists(filepath):
                try:
                    # Load texture
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Boss melee frame not found: {filepath}")
        
        if self.frame_textures:
            # Set sprite data using first frame dimensions
            w = ctypes.c_int()
            h = ctypes.c_int()
            sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                 ctypes.byref(w), ctypes.byref(h))
            
            self.sprite_data = {
                'frames': len(self.frame_textures),
                'width': w.value,
                'height': h.value
            }
            
            print(f"Loaded Boss melee effect: {len(self.frame_textures)} frames, {w.value}x{h.value} pixels")
        else:
            print("Error: No Boss melee effect frames loaded!")
        
        # Fast animation speed for quick melee effect
        self.animation_speed = 0.6
    
    def update(self, delta_time=1):
        """Update melee effect - stationary with animation."""
        if not self.active:
            return
        
        # Update animation
        self._update_animation()
        
        # Update lifetime
        self.age += 1
        if self.age >= self.lifetime:
            self.active = False
    
    def _update_animation(self):
        """Update animation frame for individual textures."""
        if not self.frame_textures:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_textures)
    
    def render(self, camera_x=0, camera_y=0):
        """Render Boss melee effect with individual frame textures.
        
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
        
        # Render (no source rect needed for individual frames)
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
        Get rectangular hitbox for collision detection.
        
        Returns:
            tuple: (x, y, width, height)
        """
        return (self.x, self.y, self.width, self.height)
    
    def check_collision(self, target):
        """
        Check collision with a target entity, preventing multiple hits on same target.
        
        Args:
            target: Entity with get_bounds() method
            
        Returns:
            bool: True if collision detected and target hasn't been hit yet
        """
        if not self.active:
            return False
        
        # Check if we've already hit this target
        target_id = id(target)
        if target_id in self.hit_targets:
            return False
        
        # Get bounding boxes
        px, py, pw, ph = self.get_bounds()
        tx, ty, tw, th = target.get_bounds()
        
        # AABB collision detection
        collision = (px < tx + tw and
                    px + pw > tx and
                    py < ty + th and
                    py + ph > ty)
        
        if collision:
            # Mark this target as hit
            self.hit_targets.add(target_id)
        
        return collision
    
    def on_hit(self):
        """
        Override on_hit to NOT deactivate the effect.
        Melee effect should remain visible for its full lifetime.
        """
        # Don't set active = False - let the lifetime expire naturally
        pass
    
    def cleanup(self):
        """Clean up resources. Don't destroy textures if they're shared from manager."""
        # Only clear the list reference, don't destroy textures
        # Textures are managed by ProjectileManager if preloaded
        self.frame_textures = []


class BossFlameProjectile(Projectile):
    """
    Boss ranged flame projectile.
    
    Animated flame projectile that travels toward the player.
    Uses individual frame images numbered 1-8.
    """
    
    def __init__(self, x, y, velocity_x, velocity_y, direction, owner, renderer, damage, preloaded_textures=None):
        """
        Initialize Boss flame projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            velocity_x: Horizontal velocity
            velocity_y: Vertical velocity
            direction: Direction (1 for right, -1 for left)
            owner: The Boss entity
            renderer: PySDL2 renderer
            damage: Damage value
            preloaded_textures: List of preloaded textures (optional)
        """
        super().__init__(x, y, velocity_x, velocity_y, damage, direction, owner, renderer)
        
        self.width = 64
        self.height = 64
        
        # Longer lifetime for ranged projectiles
        self.lifetime = 240  # 4 seconds at 60 FPS
        
        # Load or use preloaded flame projectile sprites
        self.frame_textures = []
        if preloaded_textures:
            # Use preloaded textures (no disk I/O - prevents lag)
            self.frame_textures = preloaded_textures
            if self.frame_textures:
                w = ctypes.c_int()
                h = ctypes.c_int()
                sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                     ctypes.byref(w), ctypes.byref(h))
                self.sprite_data = {
                    'frames': len(self.frame_textures),
                    'width': w.value,
                    'height': h.value
                }
                # Medium animation speed
                self.animation_speed = 0.25
        else:
            # Fallback: load from disk (will cause lag)
            self._load_frames()
    
    def _load_frames(self):
        """Load all flame projectile frame images."""
        base_path = os.path.join("assets", "Projectile", "Boss", "Flame")
        
        # Load frames 1-8 (based on directory listing)
        for i in range(1, 9):
            filename = f"{i}.png"
            filepath = os.path.join(base_path, filename)
            
            if os.path.exists(filepath):
                try:
                    # Load texture
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load {filepath}: {e}")
            else:
                print(f"Warning: Boss flame frame not found: {filepath}")
        
        if self.frame_textures:
            # Set sprite data using first frame dimensions
            w = ctypes.c_int()
            h = ctypes.c_int()
            sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                 ctypes.byref(w), ctypes.byref(h))
            
            self.sprite_data = {
                'frames': len(self.frame_textures),
                'width': w.value,
                'height': h.value
            }
            
            print(f"Loaded Boss flame projectile: {len(self.frame_textures)} frames, {w.value}x{h.value} pixels")
        else:
            print("Error: No Boss flame projectile frames loaded!")
        
        # Medium animation speed
        self.animation_speed = 0.25
    
    def _update_animation(self):
        """Update animation frame for individual textures."""
        if not self.frame_textures:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_textures)
    
    def render(self, camera_x=0, camera_y=0):
        """Render Boss flame projectile with individual frame textures.
        
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
        
        # Determine flip based on velocity direction (projectile travels toward target)
        flip = sdl2.SDL_FLIP_NONE
        if self.velocity_x < 0:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
        # Render (no source rect needed for individual frames)
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            None,  # Use entire texture
            dest_rect,
            0,
            None,
            flip
        )
    
    def cleanup(self):
        """Clean up resources. Don't destroy textures if they're shared from manager."""
        # Only clear the list reference, don't destroy textures
        # Textures are managed by ProjectileManager if preloaded
        self.frame_textures = []


class BossCircularFlameProjectile(Projectile):
    """
    Boss circular shooting skill flame projectile.
    
    Smaller version of flame projectile (32×32) for circular barrage skill.
    More dodge-able for the player.
    """
    
    def __init__(self, x, y, velocity_x, velocity_y, direction, owner, renderer, damage, preloaded_textures=None):
        """
        Initialize Boss circular flame projectile.
        
        Args:
            x: Initial x position
            y: Initial y position
            velocity_x: Horizontal velocity
            velocity_y: Vertical velocity
            direction: Direction (1 for right, -1 for left)
            owner: The Boss entity
            renderer: PySDL2 renderer
            damage: Damage value
            preloaded_textures: List of preloaded textures (optional)
        """
        super().__init__(x, y, velocity_x, velocity_y, damage, direction, owner, renderer)
        
        # Smaller size for dodge-ability
        self.width = 32
        self.height = 32
        
        # Standard lifetime for skill projectiles
        self.lifetime = 240  # 4 seconds at 60 FPS
        
        # Load or use preloaded flame projectile sprites (same assets, scaled down)
        self.frame_textures = []
        if preloaded_textures:
            # Use preloaded textures
            self.frame_textures = preloaded_textures
            if self.frame_textures:
                w = ctypes.c_int()
                h = ctypes.c_int()
                sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                     ctypes.byref(w), ctypes.byref(h))
                self.sprite_data = {
                    'frames': len(self.frame_textures),
                    'width': w.value,
                    'height': h.value
                }
                # Medium animation speed
                self.animation_speed = 0.25
                print(f"[BossCircularFlame] Created with {len(self.frame_textures)} preloaded textures, size {self.width}×{self.height}")
        else:
            # Fallback: load from disk (will cause lag)
            print("[BossCircularFlame] Warning: No preloaded textures, loading from disk")
            self._load_frames()
    
    def _load_frames(self):
        """Load individual frame textures from disk (fallback)."""
        base_path = os.path.join("assets", "Projectile", "Boss", "Flame")
        
        for i in range(1, 9):  # 8 frames
            filename = f"{i}.png"
            filepath = os.path.join(base_path, filename)
            
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    
                    if texture:
                        self.frame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to load frame {filepath}: {e}")
        
        if self.frame_textures:
            w = ctypes.c_int()
            h = ctypes.c_int()
            sdl2.SDL_QueryTexture(self.frame_textures[0], None, None, 
                                 ctypes.byref(w), ctypes.byref(h))
            
            print(f"Loaded Boss circular flame projectile: {len(self.frame_textures)} frames, {w.value}x{h.value} pixels")
        else:
            print("Error: No Boss circular flame projectile frames loaded!")
        
        # Medium animation speed
        self.animation_speed = 0.25
    
    def _update_animation(self):
        """Update animation frame for individual textures."""
        if not self.frame_textures:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_textures)
    
    def render(self, camera_x=0, camera_y=0):
        """Render Boss circular flame projectile with individual frame textures.
        
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
        
        # Determine flip based on velocity direction
        flip = sdl2.SDL_FLIP_NONE
        if self.velocity_x < 0:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
        # Render (no source rect needed for individual frames)
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            None,  # Use entire texture
            dest_rect,
            0,
            None,
            flip
        )
    
    def cleanup(self):
        """Clean up resources. Don't destroy textures if they're shared from manager."""
        # Only clear the list reference, don't destroy textures
        # Textures are managed by ProjectileManager if preloaded
        self.frame_textures = []


class ProjectileManager:
    """
    Manager class for handling multiple projectiles.
    Preloads and caches projectile textures to prevent lag during spawning.
    """
    
    def __init__(self, renderer):
        """
        Initialize projectile manager.
        
        Args:
            renderer: PySDL2 renderer
        """
        self.projectiles = []
        self.renderer = renderer
        
        # Texture caches for boss projectiles (preloaded)
        self.boss_flame_textures = None
        self.boss_melee_textures = None
        self.boss_circular_flame_textures = None
        
        # Preload boss projectile textures
        self._preload_boss_projectile_textures()
    
    def _preload_boss_projectile_textures(self):
        """Preload boss projectile textures to prevent lag during gameplay."""
        # Preload flame projectile textures
        self.boss_flame_textures = []
        base_path = os.path.join("assets", "Projectile", "Boss", "Flame")
        for i in range(1, 9):
            filename = f"{i}.png"
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    if texture:
                        self.boss_flame_textures.append(texture)
                except Exception as e:
                    print(f"Failed to preload flame texture {filepath}: {e}")
        
        if self.boss_flame_textures:
            print(f"[ProjectileManager] Preloaded {len(self.boss_flame_textures)} boss flame textures")
        
        # Preload circular flame textures (same assets as normal flame, will be scaled to 32×32)
        self.boss_circular_flame_textures = self.boss_flame_textures  # Reuse same textures, different rendering size
        
        # Preload melee effect textures
        self.boss_melee_textures = []
        base_path = os.path.join("assets", "Projectile", "Boss", "Melee")
        for i in range(1, 11):
            filename = f"{i}.png"
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    surface = sdl2.ext.load_image(filepath)
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    sdl2.SDL_FreeSurface(surface)
                    if texture:
                        self.boss_melee_textures.append(texture)
                except Exception as e:
                    print(f"Failed to preload melee texture {filepath}: {e}")
        
        if self.boss_melee_textures:
            print(f"[ProjectileManager] Preloaded {len(self.boss_melee_textures)} boss melee textures")
    
    def spawn_ghost_projectile(self, x, y, direction, owner, charge_type=1):
        """
        Spawn a Ghost projectile.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            direction: Direction (1 for right, -1 for left)
            owner: The Ghost entity
            charge_type: Charge type (1 or 2)
            
        Returns:
            GhostProjectile: The spawned projectile
        """
        projectile = GhostProjectile(x, y, direction, owner, self.renderer, charge_type)
        self.projectiles.append(projectile)
        print(f"[PROJECTILE] Ghost projectile spawned at ({x}, {y}), dir={direction}, type={charge_type}, total={len(self.projectiles)}")
        return projectile
    
    def spawn_shooter_projectile(self, x, y, direction, owner, attack_type=1):
        """
        Spawn a Shooter projectile.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            direction: Direction (1 for right, -1 for left)
            owner: The Shooter entity
            attack_type: Attack type (1 or 2)
            
        Returns:
            ShooterProjectile: The spawned projectile
        """
        projectile = ShooterProjectile(x, y, direction, owner, self.renderer, attack_type)
        self.projectiles.append(projectile)
        print(f"[PROJECTILE] Shooter projectile spawned at ({x}, {y}), dir={direction}, type={attack_type}, total={len(self.projectiles)}")
        return projectile
    
    def spawn_boss_melee_effect(self, x, y, direction, owner, damage):
        """
        Spawn a Boss melee attack effect.
        
        Args:
            x: Boss center x position
            y: Boss center y position
            direction: Direction (1 for right, -1 for left)
            owner: The Boss entity
            damage: Damage value
            
        Returns:
            BossMeleeEffect: The spawned melee effect
        """
        melee_effect = BossMeleeEffect(x, y, direction, owner, self.renderer, damage, self.boss_melee_textures)
        self.projectiles.append(melee_effect)
        print(f"[PROJECTILE] Boss melee effect spawned at ({x}, {y}), dir={direction}, damage={damage}")
        return melee_effect
    
    def spawn_boss_flame_projectile(self, x, y, velocity_x, velocity_y, direction, owner, damage):
        """
        Spawn a Boss flame projectile.
        
        Args:
            x: Spawn x position
            y: Spawn y position
            velocity_x: Horizontal velocity
            velocity_y: Vertical velocity
            direction: Direction (1 for right, -1 for left)
            owner: The Boss entity
            damage: Damage value
            
        Returns:
            BossFlameProjectile: The spawned projectile
        """
        projectile = BossFlameProjectile(x, y, velocity_x, velocity_y, direction, owner, self.renderer, damage, self.boss_flame_textures)
        self.projectiles.append(projectile)
        print(f"[PROJECTILE] Boss flame projectile spawned at ({x:.1f}, {y:.1f}), vel=({velocity_x:.1f}, {velocity_y:.1f}), damage={damage}")
        return projectile
    
    def spawn_boss_circular_flame(self, x, y, velocity_x, velocity_y, damage, direction, owner):
        """
        Spawn a Boss circular shooting flame projectile (smaller, for skill).
        
        Args:
            x: Spawn x position
            y: Spawn y position
            velocity_x: Horizontal velocity
            velocity_y: Vertical velocity
            damage: Damage value
            direction: Direction (1 for right, -1 for left)
            owner: The Boss entity
            
        Returns:
            BossCircularFlameProjectile: The spawned projectile
        """
        projectile = BossCircularFlameProjectile(x, y, velocity_x, velocity_y, direction, owner, self.renderer, damage, self.boss_circular_flame_textures)
        self.projectiles.append(projectile)
        return projectile
    
    def update_all(self, delta_time=1):
        """Update all projectiles."""
        for projectile in self.projectiles:
            projectile.update(delta_time)
        
        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]
    
    def render_all(self, camera_x=0, camera_y=0):
        """Render all projectiles.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        if len(self.projectiles) > 0:
            print(f"[RENDER] Rendering {len(self.projectiles)} projectiles")
        for projectile in self.projectiles:
            projectile.render(camera_x, camera_y)
    
    def check_collisions(self, targets):
        """
        Check projectile collisions with targets.
        
        Args:
            targets: List of entities to check collision against
            
        Returns:
            list: List of (projectile, target) tuples for hits
        """
        hits = []
        for projectile in self.projectiles:
            if not projectile.active:
                continue
            
            for target in targets:
                # Don't hit the owner
                if target == projectile.owner:
                    continue
                
                if projectile.check_collision(target):
                    hits.append((projectile, target))
                    projectile.on_hit()
        
        return hits
    
    def clear_all(self):
        """Remove all projectiles without destroying shared textures."""
        # Don't call cleanup on individual projectiles if they use shared textures
        # Just clear the list - textures will be cleaned up in cleanup()
        self.projectiles.clear()
    
    def cleanup(self):
        """Clean up all projectiles and preloaded textures."""
        # Clear all active projectiles
        self.projectiles.clear()
        
        # Clean up preloaded boss flame textures
        if self.boss_flame_textures:
            for texture in self.boss_flame_textures:
                if texture:
                    sdl2.SDL_DestroyTexture(texture)
            self.boss_flame_textures = None
            print("[ProjectileManager] Cleaned up boss flame textures")
        
        # Clean up preloaded boss melee textures
        if self.boss_melee_textures:
            for texture in self.boss_melee_textures:
                if texture:
                    sdl2.SDL_DestroyTexture(texture)
            self.boss_melee_textures = None
            print("[ProjectileManager] Cleaned up boss melee textures")
        
        # Circular flame textures are shared with normal flame, no separate cleanup needed
        self.boss_circular_flame_textures = None
