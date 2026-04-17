import sdl2
import sdl2.ext
import os
import time
from combat.refactored_skill import BaseSkill
from combat.refactored_utils import load_image_sequence
from settings import SKILL_E_2_COOLDOWN, SKILL_E_2_CAST_RANGE, DAMAGE_SKILL_E_2, SKILL_E_2_ROOT_ZONE_HEIGHT, DEBUG_COLLISION_BOXES
from entities.leaf_ranger_aoe import ArrowRainAoE

# ─────────────────────────────────────────────────────────────────────────────
# ASSET LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_arrow_rain_cast_animation(factory, skill_asset_dir, target_size=None):
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    sprites = load_image_sequence(
        factory,
        e_folder,
        prefix="3_atk_",
        count=12,
        target_size=target_size,
        zero_pad=False
    )
    return sprites


def load_arrow_rain_cast_animation_proportional(factory, skill_asset_dir, scale_factor=1.0, crop_box=None):
    """
    Load E cast animation with proportional scaling and optional cropping.
    
    E cast sprites are 288×128 pixels (same as idle and Q cast source images).
    They need the SAME crop box as idle to keep character position consistent.
    
    Args:
        factory: Sprite factory
        skill_asset_dir: Path to Skills folder
        scale_factor: Scaling multiplier (e.g., 1.5 for LeafRanger)
        crop_box: (x, y, w, h) tuple for cropping, e.g., (117, 45, 77, 83)
    """
    import sdl2
    import sdl2.ext
    import sys
    e_folder = os.path.join(skill_asset_dir, "skill_e_2")
    
    sprites = []
    for i in range(1, 13):  # 3_atk_1.png through 3_atk_12.png
        file_path = os.path.join(e_folder, f"3_atk_{i}.png")
        if not os.path.exists(file_path):
            continue
        
        try:
            surf_ptr = sdl2.ext.load_image(file_path)
            
            # Apply crop box if provided (SAME as idle sprites)
            if crop_box:
                cx, cy, cw, ch = crop_box
                src_rect = sdl2.SDL_Rect(cx, cy, cw, ch)
            else:
                orig_w = surf_ptr.w if hasattr(surf_ptr, 'w') else surf_ptr.contents.w
                orig_h = surf_ptr.h if hasattr(surf_ptr, 'h') else surf_ptr.contents.h
                src_rect = sdl2.SDL_Rect(0, 0, orig_w, orig_h)
            
            # Scale the cropped region
            new_w = int(src_rect.w * scale_factor)
            new_h = int(src_rect.h * scale_factor)
            
            rmask, gmask, bmask, amask = 0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000
            if sys.byteorder == 'big':
                rmask, gmask, bmask, amask = 0xff000000, 0x00ff0000, 0x0000ff00, 0x000000ff
            
            scaled_surf = sdl2.SDL_CreateRGBSurface(0, new_w, new_h, 32, rmask, gmask, bmask, amask)
            sdl2.SDL_SetSurfaceBlendMode(surf_ptr, sdl2.SDL_BLENDMODE_NONE)
            
            dst_rect = sdl2.SDL_Rect(0, 0, new_w, new_h)
            sdl2.SDL_BlitScaled(surf_ptr, src_rect, scaled_surf, dst_rect)
            
            sprite = factory.from_surface(scaled_surf)
            sprites.append(sprite)
            sdl2.SDL_FreeSurface(surf_ptr)
        except Exception as e:
            print(f"[ERROR] E cast frame {i}: {e}")
    
    if sprites:
        crop_info = f"crop={crop_box}" if crop_box else "no crop"
        print(f"[E CAST] Loaded {len(sprites)} frames: {sprites[0].size if sprites else 'N/A'} (factor={scale_factor}, {crop_info})")
    
    return sprites

# ─────────────────────────────────────────────────────────────────────────────
# ARROW RAIN PROJECTILE (Falls from sky)
# ─────────────────────────────────────────────────────────────────────────────

class ArrowRainProjectile:
    """
    Falling arrow projectile that spawns from top of screen, falls to ground,
    then creates AoE with roots at impact point.
    
    Behavior:
    - Spawns at top of visible screen (camera.camera.y)
    - Falls toward target X position (nearest enemy or max range)
    - Detects ground height using game_map
    - Applies DAMAGE_SKILL_E_2 to enemies hit during fall (no root)
    - Creates ArrowRainAoE (roots + damage) at landing position
    """
    
    def __init__(self, target_x, owner, renderer, game_map, camera, damage_multiplier=1.0):
        """
        Args:
            target_x: World X coordinate where arrow should land
            owner: LeafRanger instance
            renderer: SDL2 renderer
            game_map: GameMap instance for ground detection
            camera: Camera instance for screen positioning
            damage_multiplier: Damage scaling from skill level
        """
        self.owner = owner
        self.renderer = renderer
        self.game_map = game_map
        self.camera = camera
        self.damage_multiplier = damage_multiplier
        
        # Position - spawn at top of screen, fall to target_x
        self.target_x = target_x
        self.x = target_x  # X position (world coordinates)
        self.y = camera.camera.y  # Start at TOP EDGE of visible screen (not above it)
        
        # Movement - falling physics
        self.fall_speed = 600  # pixels per second (visible fall)
        self.active = True
        
        # Ground detection - continuously check during fall
        self.ground_detection_lookahead = 50  # pixels ahead to check for ground
        
        # Collision tracking - enemies hit during fall (no root, damage only)
        self.fall_hit_list = set()  # net_ids of enemies hit during fall
        
        # Visual representation - larger and more visible
        self.width = 80
        self.height = 80
        
        # Debug mode for collision visualization (from settings)
        self.debug_mode = DEBUG_COLLISION_BOXES
        
        print(f"[ArrowRainProjectile] Created: target_x={target_x}, start_y={self.y:.1f}, fall_speed={self.fall_speed}, debug_mode={self.debug_mode}")
    
    def _check_ground_collision(self):
        """
        Check if projectile is about to hit or has hit ground.
        Uses dynamic ground detection to handle platforms at different heights.
        
        Returns:
            float or None: Ground Y position if hit, None otherwise
        """
        if not self.game_map or not hasattr(self.game_map, 'get_ground_height_at_x'):
            return None
        
        # Check for ground starting from current Y position
        ground_y = self.game_map.get_ground_height_at_x(self.target_x, start_y=self.y)
        
        if ground_y is None:
            # No ground found below, this shouldn't happen but handle gracefully
            # Check if we've fallen below a reasonable map boundary
            from settings import WINDOW_HEIGHT
            max_fall_y = self.camera.camera.y + WINDOW_HEIGHT
            if self.y >= max_fall_y:
                print(f"[ArrowRainProjectile] WARNING: Fell below map boundary at y={self.y:.1f}, camera.y={self.camera.camera.y:.1f}")
                return self.y  # Use current position as "ground"
            return None
        
        # Check if we're within lookahead distance of ground
        distance_to_ground = ground_y - self.y
        if self.debug_mode and distance_to_ground < 200:  # Log when getting close
            print(f"[Ground Detection] y={self.y:.1f}, ground={ground_y:.1f}, distance={distance_to_ground:.1f}, lookahead={self.ground_detection_lookahead}")
        
        if self.y + self.ground_detection_lookahead >= ground_y:
            if self.debug_mode:
                print(f"[Ground Detection] COLLISION! Will land at ground_y={ground_y:.1f}")
            return ground_y
        
        return None
    
    def update(self, dt, enemies):
        """
        Update projectile - fall toward ground, check collisions.
        
        Args:
            dt: Delta time (seconds)
            enemies: List of enemies to check collision against
        
        Returns:
            ArrowRainAoE or None: AoE object if projectile landed, None otherwise
        """
        if not self.active:
            return None
        
        # Fall downward
        self.y += self.fall_speed * dt
        
        # Check for ground collision dynamically
        ground_y = self._check_ground_collision()
        
        if ground_y is not None:
            # Hit ground! Red box CENTER is at self.y
            # Calculate actual ground position: BOTTOM of red box (not center!)
            actual_ground_y = self.y + (self.height // 2) + 4
            
            print(f"[ArrowRainProjectile] Red box center at y={self.y:.1f}, bottom (ground) at y={actual_ground_y:.1f}")
            
            # Get top of screen position
            top_of_screen = self.camera.camera.y
            
            # Create AoE with dynamic height from top of screen to ACTUAL ground (bottom of box)
            aoe = ArrowRainAoE(
                x=self.x,
                ground_y=actual_ground_y,
                owner=self.owner,
                renderer=self.renderer,
                damage_multiplier=self.damage_multiplier,
                camera=self.camera,
                top_y=top_of_screen
            )
            
            # Load first frame to calculate dimensions
            aoe._get_frame_texture(0)
            
            print(f"[ArrowRainProjectile] Landed! Ground={actual_ground_y:.1f}, TopOfScreen={top_of_screen:.1f}")
            print(f"[ArrowRainProjectile] Arrow rain extends {abs(actual_ground_y - top_of_screen):.1f} pixels from sky to ground")
            
            self.active = False
            return aoe
        
        # Check collision with enemies during fall (damage only, no root)
        self._check_fall_collisions(enemies)
        
        return None
    
    def _check_fall_collisions(self, enemies):
        """
        Check if falling arrow hits any enemies.
        Enemies hit during fall take damage but are NOT rooted.
        """
        # Projectile hitbox
        proj_x = self.x - self.width // 2
        proj_y = self.y - self.height // 2
        proj_rect = sdl2.SDL_Rect(int(proj_x), int(proj_y), self.width, self.height)
        
        for enemy in enemies:
            # Skip dead enemies
            if not hasattr(enemy, 'is_alive'):
                if hasattr(enemy, 'health') and enemy.health <= 0:
                    continue
            elif not enemy.is_alive():
                continue
            
            # Get enemy ID for tracking
            enemy_id = id(enemy)  # Use Python object id as unique identifier
            
            # Skip if already hit during fall
            if enemy_id in self.fall_hit_list:
                continue
            
            # Get enemy hitbox
            if hasattr(enemy, 'get_bounds'):
                ex, ey, ew, eh = enemy.get_bounds()
            elif hasattr(enemy, 'sprite') and hasattr(enemy.sprite, 'x'):
                ex, ey = enemy.sprite.x, enemy.sprite.y
                ew, eh = getattr(enemy, 'width', 64), getattr(enemy, 'height', 64)
            else:
                continue
            
            enemy_rect = sdl2.SDL_Rect(int(ex), int(ey), int(ew), int(eh))
            
            # Check collision
            if sdl2.SDL_HasIntersection(proj_rect, enemy_rect):
                # Hit! Apply damage (no root)
                damage = DAMAGE_SKILL_E_2 * self.damage_multiplier
                
                if hasattr(enemy, 'take_damage'):
                    enemy.take_damage(damage)
                elif hasattr(enemy, 'health'):
                    enemy.health -= damage
                
                self.fall_hit_list.add(enemy_id)
                print(f"[ArrowRainProjectile] Fall hit enemy at ({ex:.1f}, {ey:.1f}), dealt {damage:.1f} damage (no root)")
    
    def render(self, renderer, camera):
        """
        Render falling arrow projectile with debug collision visualization.
        
        Args:
            renderer: SDL2 renderer
            camera: Camera for screen position conversion
        """
        if not self.active:
            return
        
        # Red box removed - physics object is invisible, only arrow rain effect shows after landing
        
        # DEBUG MODE: Render collision boxes and ground detection
        if self.debug_mode:
            # 1. Projectile hitbox (used for enemy collision)
            proj_x = self.x - self.width // 2
            proj_y = self.y - self.height // 2
            proj_screen_x = int(proj_x - camera.camera.x)
            proj_screen_y = int(proj_y - camera.camera.y)
            proj_rect = sdl2.SDL_Rect(proj_screen_x, proj_screen_y, self.width, self.height)
            
            # Yellow outline for projectile hitbox
            sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 0, 255)
            sdl2.SDL_RenderDrawRect(renderer, proj_rect)
            
            # 2. Ground detection lookahead zone
            lookahead_y = self.y + self.ground_detection_lookahead
            lookahead_screen_y = int(lookahead_y - camera.camera.y)
            lookahead_line_start_x = int(self.x - 30 - camera.camera.x)
            lookahead_line_end_x = int(self.x + 30 - camera.camera.x)
            
            # Cyan line showing lookahead distance
            sdl2.SDL_SetRenderDrawColor(renderer, 0, 255, 255, 255)
            sdl2.SDL_RenderDrawLine(renderer, 
                                   lookahead_line_start_x, lookahead_screen_y,
                                   lookahead_line_end_x, lookahead_screen_y)
            
            # 3. Check and visualize detected ground
            ground_y = self._check_ground_collision()
            if ground_y is not None:
                ground_screen_y = int(ground_y - camera.camera.y)
                ground_line_start_x = int(self.x - 50 - camera.camera.x)
                ground_line_end_x = int(self.x + 50 - camera.camera.x)
                
                # Green line showing detected ground surface
                sdl2.SDL_SetRenderDrawColor(renderer, 0, 255, 0, 255)
                sdl2.SDL_RenderDrawLine(renderer, 
                                       ground_line_start_x, ground_screen_y,
                                       ground_line_end_x, ground_screen_y)
                
                # Distance to ground text indicator
                distance_to_ground = ground_y - self.y
                print(f"[DEBUG] Projectile y={self.y:.1f}, Ground y={ground_y:.1f}, Distance={distance_to_ground:.1f}")
            
            # 4. Center crosshair
            center_x = int(self.x - camera.camera.x)
            center_y = int(self.y - camera.camera.y)
            sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)  # White
            sdl2.SDL_RenderDrawLine(renderer, center_x - 5, center_y, center_x + 5, center_y)
            sdl2.SDL_RenderDrawLine(renderer, center_x, center_y - 5, center_x, center_y + 5)
        
        # Target landing X position marker (yellow dot at bottom)
        target_screen_x = int(self.target_x - camera.camera.x)
        # Show marker on screen bottom
        from settings import WINDOW_HEIGHT
        marker_y = WINDOW_HEIGHT - 10
        marker_rect = sdl2.SDL_Rect(target_screen_x - 5, marker_y, 10, 10)
        sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 0, 255)  # Yellow marker
        sdl2.SDL_RenderFillRect(renderer, marker_rect)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN SKILL CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SkillE(BaseSkill):
    def __init__(self, owner):
        from settings import LR_SKILL_E_COST
        super().__init__(owner, name="Arrow Rain", base_cooldown=SKILL_E_2_COOLDOWN,
                         stamina_cost=LR_SKILL_E_COST)
        
        self.cast_range = SKILL_E_2_CAST_RANGE
        self.is_dashing = False # Flag giữ chỗ cho Animation của LeafRanger (Dùng chung từ BaseChar)

    def execute(self, renderer=None, game_map=None, camera=None, **kwargs):
        """
        Execute E skill - spawn falling arrow projectile.
        
        Targeting logic:
        1. Find nearest enemy/boss/minion within cast_range
        2. If found, target that enemy's X position
        3. If none found, target max_range from player
        
        Args:
            renderer: SDL2 renderer
            game_map: GameMap for ground detection
            camera: Camera for screen positioning
            **kwargs: Can contain 'enemies' list
        
        Returns:
            ArrowRainProjectile: Falling arrow projectile
        """
        if renderer is None or game_map is None or camera is None:
            print("[SkillE] ERROR: Missing renderer, game_map, or camera!")
            return None
        
        direction = 1 if self.owner.facing_right else -1
        
        # Get enemies list from kwargs
        enemies = kwargs.get('enemies', [])
        
        # Find nearest enemy within range
        target_x = None
        min_distance = float('inf')
        
        for enemy in enemies:
            # Skip dead enemies
            if not hasattr(enemy, 'is_alive'):
                if hasattr(enemy, 'health') and enemy.health <= 0:
                    continue
            elif not enemy.is_alive():
                continue
            
            # Get enemy position (use center X for accurate direction & distance)
            if hasattr(enemy, 'x'):
                enemy_x = enemy.x
            elif hasattr(enemy, 'sprite') and hasattr(enemy.sprite, 'x'):
                enemy_x = enemy.sprite.x
            else:
                continue

            # Use center X so large enemies (Boss 256px wide) are not skipped
            # when the player's sprite overlaps the enemy's left edge
            enemy_width = getattr(enemy, 'width', 0)
            enemy_center_x = enemy_x + enemy_width / 2
            
            # Check if enemy is in front of player (based on facing direction)
            dx = enemy_center_x - self.owner.x
            if direction > 0 and dx < 0:  # Facing right, enemy is left
                continue
            if direction < 0 and dx > 0:  # Facing left, enemy is right
                continue
            
            # Check if within range
            distance = abs(dx)
            if distance <= self.cast_range and distance < min_distance:
                min_distance = distance
                target_x = enemy_center_x
        
        # If no enemy found, target max range
        if target_x is None:
            target_x = self.owner.x + (self.cast_range * direction)
            print(f"[SkillE] No enemy in range, targeting max range: x={target_x:.1f}")
        else:
            print(f"[SkillE] Targeting nearest enemy at x={target_x:.1f}, distance={min_distance:.1f}")
        
        # Spawn falling projectile
        projectile = ArrowRainProjectile(
            target_x=target_x,
            owner=self.owner,
            renderer=renderer,
            game_map=game_map,
            camera=camera,
            damage_multiplier=self.damage_multiplier
        )
        
        return projectile

# ─────────────────────────────────────────────────────────────────────────────
# UPDATE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def update_e_projectile_logic(projectile_obj, enemies, dt):
    """
    Update falling arrow projectile.
    
    Args:
        projectile_obj: ArrowRainProjectile instance
        enemies: List of enemies
        dt: Delta time
    
    Returns:
        ArrowRainAoE or None: AoE if projectile landed, None otherwise
    """
    if not projectile_obj.active:
        return None
    
    # Update projectile (returns AoE when it lands)
    aoe = projectile_obj.update(dt, enemies)
    return aoe


def update_e_aoe_logic(aoe_obj, enemies, dt, network_ctx=None):
    """
    Update Arrow Rain AoE (roots + damage zone after projectile lands).
    
    Args:
        aoe_obj: ArrowRainAoE instance
        enemies: List of enemies
        dt: Delta time
        network_ctx: Network context for multiplayer
    """
    if not aoe_obj.active: 
        return
    
    # 1. UPDATE ANIMATION AND LIFETIME
    aoe_obj.update(dt)
    
    # 2. COLLISION SCAN - apply root + damage to enemies in AoE
    for target in enemies:
        if not hasattr(target, 'is_alive'):
            if hasattr(target, 'health') and target.health <= 0: 
                continue
        elif not target.is_alive(): 
            continue
        
        if aoe_obj.check_collision(target):
            aoe_obj.apply_root(target, network_ctx)