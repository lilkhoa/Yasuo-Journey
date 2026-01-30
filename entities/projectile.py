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
            delta_time: Time elapsed since last update
        """
        if not self.active:
            return
        
        # Update position
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        
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
    
    def render(self):
        """Render projectile sprite."""
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
        
        # Destination rectangle
        dest_rect = sdl2.SDL_Rect(
            int(self.x),
            int(self.y),
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
    
    def render(self):
        """Render Shooter projectile with individual frame textures."""
        if not self.active or not self.frame_textures:
            return
        
        # Get current frame texture
        texture = self.frame_textures[self.current_frame]
        
        # Destination rectangle
        dest_rect = sdl2.SDL_Rect(
            int(self.x),
            int(self.y),
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

class ProjectileManager:
    """
    Manager class for handling multiple projectiles.
    """
    
    def __init__(self, renderer):
        """
        Initialize projectile manager.
        
        Args:
            renderer: PySDL2 renderer
        """
        self.projectiles = []
        self.renderer = renderer
    
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
        return projectile
    
    def update_all(self, delta_time=1):
        """Update all projectiles."""
        for projectile in self.projectiles:
            projectile.update(delta_time)
        
        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]
    
    def render_all(self):
        """Render all projectiles."""
        for projectile in self.projectiles:
            projectile.render()
    
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
        """Remove all projectiles."""
        for projectile in self.projectiles:
            projectile.cleanup()
        self.projectiles.clear()
    
    def cleanup(self):
        """Clean up all projectiles."""
        self.clear_all()
