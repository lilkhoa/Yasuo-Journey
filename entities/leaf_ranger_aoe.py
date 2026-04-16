"""
Player 2 Arrow Rain AoE (Area of Effect)

ArrowRainAoE is a static circular area that roots all enemies within it.
Appears when Player 2 casts Skill E (Arrow Rain – Large-Area Root).
"""

import os
import sdl2
import sdl2.ext
import time
from settings import (
    SKILL_E_2_WIDTH,
    SKILL_E_2_HEIGHT,
    SKILL_E_2_DURATION,
    SKILL_E_2_SNARE_DURATION,
)


class ArrowRainAoE:
    """
    Arrow Rain AoE zone - Static circular area that roots enemies.
    
    Attributes:
        x, y: Center position of AoE
        width, height: AoE dimensions (rectangular hit zone)
        active: Whether AoE is still active
        duration: Total time AoE persists
        snare_duration: How long enemies stay rooted
        created_at: Timestamp when created
        lifetime_timer: Countdown to destruction
        hit_list: Set of target IDs already hit (prevents double hits)
        frame_textures: List of animation frame textures
        current_frame: Current animation frame
        animation_speed: Frame update speed
        frame_counter: Animation timer
    """
    
    def __init__(self, x, y, owner, renderer, damage_multiplier=1.0):
        """
        Initialize Arrow Rain AoE.
        
        Args:
            x, y: Center position of AoE
            renderer: SDL2 renderer for loading textures
        """
        self.x = x
        self.y = y
        self.owner = owner
        self.damage_multiplier = damage_multiplier
        self.width = SKILL_E_2_WIDTH
        self.height = SKILL_E_2_HEIGHT
        
        self.active = True
        self.duration = SKILL_E_2_DURATION
        self.snare_duration = SKILL_E_2_SNARE_DURATION
        
        self.created_at = time.time()
        self.lifetime_timer = self.duration
        
        # Collision tracking - prevents hitting same target multiple times
        self.hit_list = set()  # Set of target net_ids that have been hit
        
        # Animation (loaded on-demand during render, not preloaded)
        self.frame_paths = []  # Paths to frame images
        self.frame_textures = {}  # Cache of loaded textures (frame_index -> texture)
        self.current_frame = 0
        self.animation_speed = 0.12
        self.frame_counter = 0
        self.renderer = renderer
        
        # Pre-build frame paths list
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        base_path = os.path.join(root_dir, "assets", "Projectile", "Player_2", "e")
        for i in range(1, 19):  # 18 frames
            self.frame_paths.append(os.path.join(base_path, f"arrow_shower_effect_{i}.png"))
        
        print(f"[ArrowRainAoE] Created at world position ({x}, {y})")
        print(f"[ArrowRainAoE] AoE will render from screen Y: {y - self.height // 2} to {y + self.height // 2}")
        print(f"[ArrowRainAoE] Duration: {SKILL_E_2_DURATION}s, Snare Duration: {SKILL_E_2_SNARE_DURATION}s")
        print(f"[ArrowRainAoE] Size: {self.width}x{self.height}")
        print(f"[ArrowRainAoE] Prebuilt frame paths: {len(self.frame_paths)} frames")
    
    def _get_frame_texture(self, frame_index):
        """
        Load texture for frame on-demand (like Q laser does).
        Uses caching so we only load once per frame.
        """
        if frame_index < 0 or frame_index >= len(self.frame_paths):
            return None
        
        # Check cache first
        if frame_index in self.frame_textures:
            return self.frame_textures[frame_index]
        
        # Not cached, load from file
        filepath = self.frame_paths[frame_index]
        if not os.path.exists(filepath):
            print(f"[ArrowRainAoE._get_frame_texture] Frame file not found: {filepath}")
            return None
        
        try:
            # Load surface from file (matches Q laser pattern)
            surface = sdl2.ext.load_image(filepath)
            if surface is None:
                print(f"[ArrowRainAoE._get_frame_texture] Failed to load surface: {filepath}")
                return None
            
            # Create texture from surface (matches Q laser pattern)
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            
            # Free surface after texture creation
            sdl2.SDL_FreeSurface(surface)
            
            if texture is None:
                # Get SDL error for debugging
                error = sdl2.SDL_GetError()
                print(f"[ArrowRainAoE._get_frame_texture] Failed to create texture: {filepath}")
                print(f"  SDL Error: {error}")
                return None
            
            # Cache the texture
            self.frame_textures[frame_index] = texture
            print(f"[ArrowRainAoE] Loaded and cached frame {frame_index + 1}")
            return texture
            
        except Exception as e:
            print(f"[ArrowRainAoE._get_frame_texture] Exception: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update(self, dt):
        """
        Update AoE animation and lifetime.
        
        Args:
            dt: Delta time (seconds)
        """
        if not self.active:
            return
        
        # Update animation
        self._update_animation()
        
        # Update lifetime countdown
        self.lifetime_timer -= dt
        print(f"[ArrowRainAoE.update] Lifetime remaining: {self.lifetime_timer:.2f}s")
        
        if self.lifetime_timer <= 0:
            print(f"[ArrowRainAoE.update] AoE expired and destroyed")
            self.active = False
    
    def _update_animation(self):
        """Update animation frame."""
        if not self.frame_paths:
            return
        
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % len(self.frame_paths)
    
    def get_hitbox(self):
        """
        Get rectangular hitbox for collision detection.
        
        Returns:
            tuple: (x, y, width, height) - hitbox coordinates and dimensions
        """
        # Center the AoE on the given position
        hitbox_x = self.x - self.width // 2
        hitbox_y = self.y - self.height // 2
        
        return (hitbox_x, hitbox_y, self.width, self.height)
    
    def check_collision(self, target):
        """
        Check if target is within AoE zone.
        
        Args:
            target: Enemy/Boss with get_bounds() method
            
        Returns:
            bool: True if collision detected
        """
        if not self.active:
            return False
        
        # Get AoE hitbox
        aoe_x, aoe_y, aoe_w, aoe_h = self.get_hitbox()
        aoe_rect = sdl2.SDL_Rect(int(aoe_x), int(aoe_y), int(aoe_w), int(aoe_h))
        
        # Get target hitbox
        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
        else:
            # Fallback for sprite-based targets
            tx = target.x if hasattr(target, 'x') else target.sprite.x
            ty = target.y if hasattr(target, 'y') else target.sprite.y
            tw = target.width if hasattr(target, 'width') else target.sprite.size[0]
            th = target.height if hasattr(target, 'height') else target.sprite.size[1]
        
        target_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
        
        # AABB collision detection
        return sdl2.SDL_HasIntersection(aoe_rect, target_rect)
    
    def apply_root(self, target, network_ctx=None):
        """
        Apply root/snare effect to target if not already hit.
        
        Args:
            target: Enemy/Boss to root
            network_ctx: Network context tuple (is_multi, is_host, game_client)
            
        Returns:
            bool: True if root was applied, False if already hit
        """
        if not self.active:
            return False
        
        target_net_id = getattr(target, 'net_id', id(target))
        
        # Only hit each target once per AoE
        if target_net_id in self.hit_list:
            return False
        
        # Mark as hit
        self.hit_list.add(target_net_id)
        
        print(f"Arrow Rain Root Applied! Duration: {self.snare_duration}s")
        
        # Apply root effect to target
        if hasattr(target, 'snare_timer'):
            target.snare_timer = self.snare_duration
        
        # Network synchronization
        if network_ctx:
            is_multi, is_host, game_client = network_ctx
            if is_multi and game_client and game_client.is_connected():
                try:
                    # Send status event for snare
                    game_client.send_status_event(target_net_id, 'snare', self.snare_duration)
                except:
                    # Fallback: if send_status_event doesn't exist
                    pass
        
        return True
    
    def render(self, camera_x=0, camera_y=0):
        """
        Render AoE animation using on-demand texture loading (matches Q laser pattern).
        
        Args:
            camera_x: Camera x offset for screen positioning
            camera_y: Camera y offset for screen positioning
        """
        if not self.active:
            return
        
        # Verify renderer is valid
        if self.renderer is None:
            print(f"[ArrowRainAoE.render] ERROR: Renderer is None!")
            return
        
        # Get current frame texture (loads on-demand, like Q laser does)
        texture = self._get_frame_texture(self.current_frame)
        
        if texture is None:
            # Texture not available, skip rendering this frame
            return
        
        # Destination rectangle (screen position)
        dest_x = int(self.x - self.width // 2 - camera_x)
        dest_y = int(self.y - self.height // 2 - camera_y)
        
        dest_rect = sdl2.SDL_Rect(
            dest_x,
            dest_y,
            self.width,
            self.height
        )
        
        # Render using same pattern as Q laser
        result = sdl2.SDL_RenderCopy(
            self.renderer,
            texture,
            None,  # Use entire texture
            dest_rect
        )
        
        if result != 0:
            error = sdl2.SDL_GetError()
            print(f"[ArrowRainAoE.render] SDL_RenderCopy FAILED on frame {self.current_frame}: {error}")
    
    def cleanup(self):
        """Clean up resources - destroy cached textures."""
        for frame_index, texture in self.frame_textures.items():
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.frame_textures.clear()
        self.hit_list.clear()
