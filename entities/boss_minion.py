"""
Boss Minion Module
Implements boss summoned minions that chase and attack the player.
"""
import os
import ctypes
import sdl2
import sdl2.ext
import math
from enum import Enum
from settings import (
    BOSS_MINION_SIZE,
    BOSS_MINION_HEALTH_BASE,
    BOSS_MINION_SPEED,
    BOSS_MINION_DETECTION_RANGE,
    BOSS_MINION_ATTACK_RANGE,
    BOSS_MINION_ATTACK_COOLDOWN,
    BOSS_MINION_DAMAGE,
    BOSS_MINION_FIREBALL_SPEED,
    METEOR_GROUND_Y,
    GRAVITY,
)


class MinionState(Enum):
    IDLE = "Idle"
    IDLE_BLINK = "Idle Blink"
    WALKING = "Walking"
    ATTACKING = "Attacking"
    HURT = "Hurt"
    DYING = "Dying"


class Direction(Enum):
    LEFT = -1
    RIGHT = 1


class BossMinion:
    
    def __init__(self, x, y, sprite_factory, renderer, projectile_manager, preloaded_textures=None):
        self.x = x
        self.y = y
        self.width = BOSS_MINION_SIZE
        self.height = BOSS_MINION_SIZE
        
        self.preloaded_textures = preloaded_textures
        self.using_shared_textures = preloaded_textures is not None
        
        self.health = BOSS_MINION_HEALTH_BASE
        self.max_health = BOSS_MINION_HEALTH_BASE
        self.speed = BOSS_MINION_SPEED
        self.detection_range = BOSS_MINION_DETECTION_RANGE
        self.attack_range = BOSS_MINION_ATTACK_RANGE
        self.attack_cooldown_max = BOSS_MINION_ATTACK_COOLDOWN
        self.damage = BOSS_MINION_DAMAGE
        
        self.state = MinionState.IDLE
        self.direction = Direction.RIGHT
        self.textures = {}
        self.sprites = {}
        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0
        
        self.sprite_factory = sprite_factory
        self.renderer = renderer
        self.projectile_manager = projectile_manager
        
        self.attack_cooldown = 0
        self.player = None
        
        # Physics
        self.ground_y = METEOR_GROUND_Y - self.height
        self.velocity_y = 0
        self.gravity = GRAVITY
        
        # Apply gravity to start on ground
        if self.y < self.ground_y:
            self.y = self.ground_y
        
        self.hurt_animation_complete = False
        self.death_animation_complete = False
        self.ready_for_removal = False
        
        self._load_sprites()
    
    def _load_sprites(self):
        # Use preloaded textures if available
        if self.preloaded_textures:
            for state, state_data in self.preloaded_textures.items():
                self.textures[state] = state_data['textures']
                self.sprites[state] = {'frames': state_data['frames']}
            return
        
        # Fallback: load from disk (will cause lag)
        base_path = os.path.join("assets", "Boss", "Boss_NPCs")
        
        state_mapping = {
            MinionState.IDLE: ("Idle", 12),
            MinionState.IDLE_BLINK: ("Idle Blink", 10),
            MinionState.WALKING: ("Walking", 12),
            MinionState.ATTACKING: ("Attacking", 12),
            MinionState.HURT: ("Hurt", 3),
            MinionState.DYING: ("Dying", 15)
        }
        
        for state, (folder_name, frame_count) in state_mapping.items():
            folder_path = os.path.join(base_path, folder_name)
            textures = []
            
            for i in range(frame_count):
                filepath = os.path.join(folder_path, f"{i}.png")
                if os.path.exists(filepath):
                    try:
                        surface = sdl2.ext.load_image(filepath)
                        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                        sdl2.SDL_FreeSurface(surface)
                        if texture:
                            textures.append(texture)
                    except Exception as e:
                        print(f"Failed to load minion texture {filepath}: {e}")
            
            if textures:
                self.textures[state] = textures
                self.sprites[state] = {'frames': len(textures)}
    
    def set_player(self, player):
        self.player = player
    
    def update(self, delta_time=1):
        if self.state == MinionState.DYING:
            self._update_animation()
            if self.death_animation_complete:
                self.ready_for_removal = True
            return
        
        if self.health <= 0:
            self.health = 0
            self.state = MinionState.DYING
            self.current_frame = 0
            self.death_animation_complete = False
            return
        
        if self.state == MinionState.HURT:
            self._update_animation()
            if self.hurt_animation_complete:
                self.hurt_animation_complete = False
                self.current_frame = 0
                self.frame_counter = 0
                self.state = MinionState.IDLE
            return
        
        self._update_animation()
        
        # Apply gravity
        self._apply_gravity()
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Don't update AI while attacking - let animation complete
        if self.state == MinionState.ATTACKING:
            return
        
        if self.player:
            self._update_ai()
    
    def _update_ai(self):
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        minion_center_x = self.x + self.width / 2
        minion_center_y = self.y + self.height / 2
        
        dx = player_center_x - minion_center_x
        dy = player_center_y - minion_center_y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Face player
        if dx > 0:
            self.direction = Direction.RIGHT
        else:
            self.direction = Direction.LEFT
        
        # Attack if in range
        if distance <= self.attack_range and self.attack_cooldown == 0:
            self._start_attack()
        elif distance <= self.detection_range:
            # Chase player (only left/right movement, gravity handles Y)
            if self.state != MinionState.ATTACKING:
                self.state = MinionState.WALKING
                # Move toward player horizontally only
                if abs(dx) > 5:  # Dead zone to prevent jittering
                    move_direction = 1 if dx > 0 else -1
                    self.x += move_direction * self.speed
        else:
            if self.state != MinionState.ATTACKING:
                self.state = MinionState.IDLE
    
    def _apply_gravity(self):
        """Apply gravity and keep minion on ground."""
        if self.y < self.ground_y:
            self.velocity_y += self.gravity
            self.y += self.velocity_y
            
            # Clamp to ground
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.velocity_y = 0
        else:
            # Already on ground
            self.y = self.ground_y
            self.velocity_y = 0
    
    def _start_attack(self):
        self.state = MinionState.ATTACKING
        self.current_frame = 0
        self.frame_counter = 0
        self.attack_cooldown = self.attack_cooldown_max
        # Projectile will fire at frame 6 during animation update
    
    def _fire_projectile(self):
        if not self.projectile_manager or not self.player:
            return
        
        # Calculate trajectory
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        minion_center_x = self.x + self.width / 2
        minion_center_y = self.y + self.height / 2
        
        dx = player_center_x - minion_center_x
        dy = player_center_y - minion_center_y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 0:
            velocity_x = (dx / distance) * BOSS_MINION_FIREBALL_SPEED
            velocity_y = (dy / distance) * BOSS_MINION_FIREBALL_SPEED
            
            direction = 1 if velocity_x >= 0 else -1
            
            self.projectile_manager.spawn_minion_fireball(
                minion_center_x, minion_center_y,
                velocity_x, velocity_y,
                self.damage,
                direction,
                self
            )
    
    def _update_animation(self):
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        
        if self.state == MinionState.DYING:
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                self.current_frame += 1
                if self.current_frame >= sprite_data['frames']:
                    self.current_frame = sprite_data['frames'] - 1
                    self.death_animation_complete = True
            return
        
        if self.state == MinionState.HURT:
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                self.current_frame += 1
                if self.current_frame >= sprite_data['frames']:
                    self.current_frame = sprite_data['frames'] - 1
                    self.hurt_animation_complete = True
            return
        
        if self.state == MinionState.ATTACKING:
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                self.current_frame += 1
                
                # Fire at specific frame
                if self.current_frame == 6:
                    self._fire_projectile()
                
                if self.current_frame >= sprite_data['frames']:
                    self.state = MinionState.IDLE
                    self.current_frame = 0
                    self.frame_counter = 0
            return
        
        # Normal looping animation
        self.frame_counter += self.animation_speed
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % sprite_data['frames']
    
    def take_damage(self, amount):
        if self.state == MinionState.DYING:
            return
        
        self.health -= amount
        if self.health > 0:
            self.state = MinionState.HURT
            self.current_frame = 0
            self.frame_counter = 0
            self.hurt_animation_complete = False
    
    def render(self, camera_x=0, camera_y=0):
        if self.state not in self.textures:
            return
        
        textures = self.textures[self.state]
        if self.current_frame >= len(textures):
            return
        
        texture = textures[self.current_frame]
        
        dest_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        
        flip = sdl2.SDL_FLIP_NONE if self.direction == Direction.RIGHT else sdl2.SDL_FLIP_HORIZONTAL
        
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            None,
            dest_rect,
            0,
            None,
            flip
        )
    
    def get_bounds(self):
        return (self.x, self.y, self.width, self.height)
    
    def cleanup_shared(self):
        """Clean up when using shared textures (don't destroy them)."""
        self.textures.clear()
        self.sprites.clear()
    
    def cleanup(self):
        """Clean up when using own textures (destroy them)."""
        if not self.using_shared_textures:
            for state_textures in self.textures.values():
                for texture in state_textures:
                    if texture:
                        sdl2.SDL_DestroyTexture(texture)
        self.textures.clear()
        self.sprites.clear()

    def is_alive(self):
        return self.health > 0 and self.state != MinionState.DYING
