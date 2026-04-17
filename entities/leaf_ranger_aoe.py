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
    SKILL_E_2_ROOT_ZONE_HEIGHT,
    DEBUG_COLLISION_BOXES,
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
    
    def __init__(self, x, ground_y, owner, renderer, damage_multiplier=1.0, camera=None, top_y=None):
        """
        Initialize Arrow Rain AoE.
        
        Args:
            x: World X position (center)
            ground_y: Ground Y position (where effect bottom should be)
            owner: LeafRanger instance
            renderer: SDL2 renderer for loading textures
            damage_multiplier: Damage scaling
            camera: Camera instance for top-of-screen positioning
            top_y: Optional explicit top Y position (defaults to camera.camera.y)
        """
        self.x = x
        self.ground_y = ground_y
        self.camera = camera
        self.owner = owner
        self.damage_multiplier = damage_multiplier
        
        # Determine top of effect (top of visible screen or explicit value)
        if top_y is not None:
            self.top_y = top_y
        elif camera is not None:
            self.top_y = camera.camera.y  # Top of visible screen
        else:
            self.top_y = ground_y - 600  # Fallback: 600 pixels above ground
        
        # Calculate Y position (center between top and ground)
        self.y = (self.top_y + ground_y) / 2
        
        # Natural sprite dimensions (loaded from texture)
        self.natural_width = None
        self.natural_height = None
        self.natural_size_loaded = False
        
        # Width scale: use natural size (no scaling) - 256px
        self.width_scale = 1.0  # Natural width, not too wide
        
        # Height: dynamically calculated to extend from top_y to ground_y
        self.desired_height = abs(ground_y - self.top_y)
        # self.desired_height = SKILL_E_2_HEIGHT  # Use fixed height from settings for consistent AoE size
        
        # Rendered dimensions (calculated after texture load)
        self.width = None
        self.height = None
        
        # Collision box (will be set to center portion of scaled sprite)
        self.collision_width = None
        self.collision_height = None
        
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
        
        print(f"[ArrowRainAoE] Created at x={x}, ground_y={ground_y}, top_y={self.top_y}, center_y={self.y}")
        print(f"[ArrowRainAoE] Will extend {self.desired_height:.1f} pixels from sky to ground")
        print(f"[ArrowRainAoE] Duration: {SKILL_E_2_DURATION}s, Snare Duration: {SKILL_E_2_SNARE_DURATION}s")
        print(f"[ArrowRainAoE] Prebuilt frame paths: {len(self.frame_paths)} frames")
    
    def _get_frame_texture(self, frame_index):
        """
        Load texture for frame on-demand (like Q laser does).
        Uses caching so we only load once per frame.
        Also extracts natural sprite dimensions on first load.
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
            
            # Extract natural dimensions from first loaded texture
            if not self.natural_size_loaded:
                # Handle both direct surface and pointer surface access
                self.natural_width = surface.w if hasattr(surface, 'w') else surface.contents.w
                self.natural_height = surface.h if hasattr(surface, 'h') else surface.contents.h
                self.natural_size_loaded = True
                
                # Width: Apply modest fixed scale (1.5x)
                self.width = int(self.natural_width * self.width_scale)
                
                # Height: Scale to fill from top of screen to ground
                # Calculate height scale needed to reach desired height
                self.height_scale = self.desired_height / self.natural_height
                self.height = int(self.natural_height * self.height_scale)
                
                # E skill sprite is 256×128 but mostly empty pixels
                # Collision box uses center 60% width, 80% height of SCALED size
                self.collision_width = int(self.width * 0.6)
                self.collision_height = int(self.height * 0.8)
                
                print(f"[ArrowRainAoE] Natural sprite: {self.natural_width}×{self.natural_height}")
                print(f"[ArrowRainAoE] Width scale: {self.width_scale}x = {self.width}px")
                print(f"[ArrowRainAoE] Height scale: {self.height_scale:.2f}x = {self.height}px (extends from y={self.top_y:.1f} to y={self.ground_y:.1f})")
                print(f"[ArrowRainAoE] Collision box (center content): {self.collision_width}×{self.collision_height}")
            
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
        Uses collision box (center content area) not full sprite size.
        
        Returns:
            tuple: (x, y, width, height) - hitbox coordinates and dimensions
        """
        # If dimensions not loaded yet, return None
        if self.collision_width is None or self.collision_height is None:
            return (int(self.x), int(self.y), 0, 0)
        
        # Center the collision box on the given position
        hitbox_x = self.x - self.collision_width // 2
        hitbox_y = self.y - self.collision_height // 2
        
        return (hitbox_x, hitbox_y, self.collision_width, self.collision_height)
    
    def get_root_zone_hitbox(self):
        """
        Get hitbox for the root zone (bottom portion where roots appear).
        Only enemies in this zone are rooted.
        Root zone is bottom 30% of collision box where roots grow.
        
        Returns:
            tuple: (x, y, width, height) - root zone hitbox
        """
        # If dimensions not loaded yet, return None
        if self.collision_width is None or self.collision_height is None:
            return (int(self.x), int(self.y), 0, 0)
        
        # Root zone is bottom 30% of collision box (where roots appear)
        root_height = int(self.collision_height * 0.3)
        hitbox_x = self.x - self.collision_width // 2
        # Root zone starts from bottom of collision area
        hitbox_y = (self.y + self.collision_height // 2) - root_height
        
        return (hitbox_x, hitbox_y, self.collision_width, root_height)
    
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
        Apply effects to target if not already hit.
        
        Two zones:
        1. Full AoE: All enemies take damage
        2. Root zone (bottom portion): Enemies also get rooted
        
        Args:
            target: Enemy/Boss to affect
            network_ctx: Network context tuple (is_multi, is_host, game_client)
            
        Returns:
            bool: True if effect was applied, False if already hit
        """
        if not self.active:
            return False
        
        from settings import DAMAGE_SKILL_E_2
        
        target_net_id = getattr(target, 'net_id', id(target))
        
        # Only hit each target once per AoE
        if target_net_id in self.hit_list:
            return False
        
        # Mark as hit
        self.hit_list.add(target_net_id)
        
        # Check if target is in root zone (bottom portion)
        in_root_zone = self._check_root_zone_collision(target)
        
        # Apply damage (all enemies in AoE)
        damage = DAMAGE_SKILL_E_2 * self.damage_multiplier
        if hasattr(target, 'take_damage'):
            target.take_damage(damage)
        elif hasattr(target, 'health'):
            target.health -= damage
        
        # Apply root ONLY if in root zone
        if in_root_zone:
            if hasattr(target, 'snare_timer'):
                target.snare_timer = self.snare_duration
            print(f"[ArrowRainAoE] Root applied! Duration: {self.snare_duration}s, Damage: {damage:.1f}")
        else:
            print(f"[ArrowRainAoE] Damage only (not in root zone): {damage:.1f}")
        
        # Network synchronization
        if network_ctx and in_root_zone:
            is_multi, is_host, game_client = network_ctx
            if is_multi and game_client and game_client.is_connected():
                try:
                    # Send status event for snare
                    game_client.send_status_event(target_net_id, 'snare', self.snare_duration)
                except:
                    pass
        
        return True
    
    def _check_root_zone_collision(self, target):
        """
        Check if target is within the root zone (bottom portion of AoE).
        
        Args:
            target: Enemy/Boss to check
        
        Returns:
            bool: True if target is in root zone
        """
        # Get root zone hitbox
        rz_x, rz_y, rz_w, rz_h = self.get_root_zone_hitbox()
        rz_rect = sdl2.SDL_Rect(int(rz_x), int(rz_y), int(rz_w), int(rz_h))
        
        # Get target hitbox
        if hasattr(target, 'get_bounds'):
            tx, ty, tw, th = target.get_bounds()
        else:
            tx = target.x if hasattr(target, 'x') else target.sprite.x
            ty = target.y if hasattr(target, 'y') else target.sprite.y
            tw = target.width if hasattr(target, 'width') else target.sprite.size[0]
            th = target.height if hasattr(target, 'height') else target.sprite.size[1]
        
        target_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
        
        return sdl2.SDL_HasIntersection(rz_rect, target_rect)
    
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
        
        # If dimensions not loaded yet, skip rendering
        if self.width is None or self.height is None:
            return
        
        # Destination rectangle (screen position) - stretched to extend from sky to ground
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
        
        # DEBUG MODE: Render collision zones (controlled by settings.DEBUG_COLLISION_BOXES)
        if DEBUG_COLLISION_BOXES:
            # 1. Full AoE zone (damage zone) - Blue outline
            aoe_x, aoe_y, aoe_w, aoe_h = self.get_hitbox()
            aoe_screen_x = int(aoe_x - camera_x)
            aoe_screen_y = int(aoe_y - camera_y)
            aoe_rect = sdl2.SDL_Rect(aoe_screen_x, aoe_screen_y, aoe_w, aoe_h)
            
            sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 150, 255, 255)  # Blue
            sdl2.SDL_RenderDrawRect(self.renderer, aoe_rect)
            
            # Draw diagonal lines to show AoE boundary
            sdl2.SDL_RenderDrawLine(self.renderer,
                                   aoe_screen_x, aoe_screen_y,
                                   aoe_screen_x + aoe_w, aoe_screen_y + aoe_h)
            sdl2.SDL_RenderDrawLine(self.renderer,
                                   aoe_screen_x + aoe_w, aoe_screen_y,
                                   aoe_screen_x, aoe_screen_y + aoe_h)
            
            # 2. Root zone (bottom portion) - Green filled rectangle with transparency
            rz_x, rz_y, rz_w, rz_h = self.get_root_zone_hitbox()
            rz_screen_x = int(rz_x - camera_x)
            rz_screen_y = int(rz_y - camera_y)
            rz_rect = sdl2.SDL_Rect(rz_screen_x, rz_screen_y, rz_w, rz_h)
            
            # Green outline for root zone
            sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 255, 0, 255)  # Bright green
            sdl2.SDL_RenderDrawRect(self.renderer, rz_rect)
            
            # Thicker border for root zone (draw multiple lines)
            for offset in range(1, 3):
                offset_rect = sdl2.SDL_Rect(rz_screen_x - offset, rz_screen_y - offset, 
                                           rz_w + offset * 2, rz_h + offset * 2)
                sdl2.SDL_RenderDrawRect(self.renderer, offset_rect)
            
            # 3. Center marker
            center_screen_x = int(self.x - camera_x)
            center_screen_y = int(self.y - camera_y)
            sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 0, 255)  # Yellow
            sdl2.SDL_RenderDrawLine(self.renderer, 
                                   center_screen_x - 10, center_screen_y,
                                   center_screen_x + 10, center_screen_y)
            sdl2.SDL_RenderDrawLine(self.renderer,
                                   center_screen_x, center_screen_y - 10,
                                   center_screen_x, center_screen_y + 10)
    
    def cleanup(self):
        """Clean up resources - destroy cached textures."""
        for frame_index, texture in self.frame_textures.items():
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        self.frame_textures.clear()
        self.hit_list.clear()
