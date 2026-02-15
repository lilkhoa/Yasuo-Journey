"""
Boss Module - Final Boss Implementation
Handles boss behavior, animations, and special skills using PySDL2.
"""
import os
import ctypes
import sdl2
import sdl2.ext
import random
from enum import Enum
from settings import (
    BOSS_HEALTH,
    BOSS_SPEED,
    BOSS_MELEE_DAMAGE,
    BOSS_MELEE_RANGE,
    BOSS_MELEE_COOLDOWN,
    BOSS_MELEE_HIT_FRAME,
    BOSS_RANGED_DAMAGE,
    BOSS_PROJECTILE_SPEED,
    BOSS_RANGED_COOLDOWN,
    BOSS_LASER_DAMAGE,
    BOSS_METEOR_DAMAGE,
    BOSS_SKILL_COOLDOWN,
    WINDOW_WIDTH,
    WINDOW_HEIGHT
)
from entities.boss_skills import CircularShootingSkill, MeteorSkill, SummonMinionsSkill
from entities.boss_minion import BossMinion


class BossState(Enum):
    """Enumeration for boss states."""
    IDLE = "Idle"
    IDLE_BLINK = "Idle_Blink"
    WALKING = "Walking"
    ATTACKING = "Attacking"
    CASTING = "Casting_Spells"
    HURT = "Hurt"
    DYING = "Dying"


class Direction(Enum):
    """Enumeration for direction."""
    LEFT = -1
    RIGHT = 1


class SkillType(Enum):
    """Enumeration for boss special skills."""
    CIRCULAR_SHOOTING = "circular_shooting"
    METEOR = "meteor"
    KAMEHAMEHA = "kamehameha"
    SUMMON_MINIONS = "summon_minions"


class Boss:
    """
    Final Boss with advanced AI, multiple attack patterns, and special skills.
    
    Attributes:
        x, y: Current position coordinates
        spawn_x, spawn_y: Initial spawn position
        center_x, center_y: Screen center position for circular shooting
        width, height: Sprite dimensions
        health, max_health: Health points
        speed: Movement speed
        state: Current animation state
        direction: Facing direction
        textures: Dictionary of loaded textures
        sprites: Dictionary of sprite data
        current_frame: Current animation frame
        animation_speed: Frame update rate
        frame_counter: Animation timing counter
        
        # Combat
        melee_damage, melee_range, melee_cooldown: Melee attack stats
        ranged_damage, ranged_cooldown: Ranged attack stats
        attack_cooldown: Current attack cooldown counter
        is_attacking: Attack state flag
        attack_type: Current attack type ('melee' or 'ranged')
        
        # Special Skills
        skill_cooldown: Current skill cooldown
        skill_cooldown_max: Maximum skill cooldown
        current_skill: Currently executing skill
        skill_phase: Current phase of skill execution
        skill_timer: Timer for skill phases
        
        # HP Thresholds for Meteor
        meteor_triggered_75: Flag for 75% HP meteor
        meteor_triggered_50: Flag for 50% HP meteor
        meteor_triggered_25: Flag for 25% HP meteor
        
        # Movement for skills
        is_moving_to_center: Flag for circular shooting movement
        is_returning_from_center: Flag for returning after skill
        target_x, target_y: Target position for movement
        
        # Animation states
        hurt_animation_complete: Hurt animation finished flag
        death_animation_complete: Death animation finished flag
        ready_for_removal: Boss ready to be removed
        
        # References
        player: Reference to player object
        projectile_manager: Manager for boss projectiles
        renderer: PySDL2 renderer
    """
    
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, projectile_manager=None, sound_manager=None, camera=None):
        """
        Initialize Boss.
        
        Args:
            x: Initial x position
            y: Initial y position (ground level)
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            projectile_manager: ProjectileManager for spawning projectiles
            sound_manager: SoundManager for audio playback
            camera: Camera instance for screen position calculations
        """
        # Position and dimensions
        self.x = x
        self.y = y
        self.spawn_x = x
        self.spawn_y = y
        self.width = 256
        self.height = 256
        
        # Combat stats from settings
        self.health = BOSS_HEALTH
        self.max_health = BOSS_HEALTH
        self.speed = BOSS_SPEED
        
        # Melee attack stats
        self.melee_damage = BOSS_MELEE_DAMAGE
        self.melee_range = BOSS_MELEE_RANGE
        self.melee_cooldown = BOSS_MELEE_COOLDOWN
        self.melee_hit_frame = BOSS_MELEE_HIT_FRAME
        
        # Ranged attack stats
        self.ranged_damage = BOSS_RANGED_DAMAGE
        self.ranged_cooldown = BOSS_RANGED_COOLDOWN
        self.projectile_speed = BOSS_PROJECTILE_SPEED
        
        # Skill stats
        self.laser_damage = BOSS_LASER_DAMAGE
        self.meteor_damage = BOSS_METEOR_DAMAGE
        self.skill_cooldown_max = BOSS_SKILL_COOLDOWN
        
        # State and animation
        self.state = BossState.IDLE
        self.direction = Direction.LEFT
        self.textures = {}
        self.sprites = {}
        self.current_frame = 0
        self.animation_speed = 0.15
        self.frame_counter = 0
        
        # PySDL2 components
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
        
        # Combat state
        self.is_attacking = False
        self.attack_cooldown = 0
        self.attack_type = None
        self.attack_hit_delivered = False
        
        # Special skills
        self.skill_cooldown = self.skill_cooldown_max
        self.current_skill = None
        self.skill_phase = 0
        self.skill_timer = 0
        
        # Skill instances
        self.circular_shooting_skill = None
        self.meteor_skill = None
        self.summon_minions_skill = None
        
        # HP threshold tracking for meteor skill
        self.meteor_triggered_75 = False
        self.meteor_triggered_50 = False
        self.meteor_triggered_25 = False
        
        # Movement for skills
        self.is_moving_to_center = False
        self.is_returning_from_center = False
        self.target_x = 0
        self.target_y = 0
        self.velocity_x = 0
        self.velocity_y = 0
        
        # Animation completion flags
        self.hurt_animation_complete = False
        self.death_animation_complete = False
        self.ready_for_removal = False
        
        # Poise / Break Bar System (Super Armor)
        self.poise = 100
        self.max_poise = 100
        self.poise_damage_per_hit = 10
        self.poise_regen_rate = 0.5
        self.damage_flash_timer = 0
        self.damage_flash_duration = 8
        
        # Idle blink system
        self.idle_blink_timer = 0
        self.idle_blink_chance = 0.01
        self.idle_blink_cooldown = 0
        self.min_blink_cooldown = 120
        
        # Jump system (boss jumps while idle)
        self.is_jumping = False
        self.jump_timer = 0
        self.jump_cooldown = 0
        self.jump_chance = 0.003
        self.min_jump_cooldown = 180
        self.ground_y = y
        self.vel_y = 0
        self.gravity = 0.5
        self.jump_force = -12
        
        # References
        self.player = None
        self.projectile_manager = projectile_manager
        self.sound_manager = sound_manager
        self.camera = camera
        
        # Summoned minions
        self.minions = []
        self.minion_textures_preloaded = None
        
        # Load boss sprites
        self._load_sprites()
        
        # Preload minion textures to prevent lag on spawn
        self._preload_minion_textures()
    
    def _preload_minion_textures(self):
        """Preload minion textures to prevent lag during spawning."""
        base_path = os.path.join("assets", "Boss", "Boss_NPCs")
        
        from entities.boss_minion import MinionState
        
        state_mapping = {
            MinionState.IDLE: ("Idle", 12),
            MinionState.IDLE_BLINK: ("Idle Blink", 10),
            MinionState.WALKING: ("Walking", 12),
            MinionState.ATTACKING: ("Attacking", 12),
            MinionState.HURT: ("Hurt", 3),
            MinionState.DYING: ("Dying", 15)
        }
        
        self.minion_textures_preloaded = {}
        
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
                        print(f"Failed to preload minion texture {filepath}: {e}")
            
            if textures:
                self.minion_textures_preloaded[state] = {
                    'textures': textures,
                    'frames': len(textures)
                }
    
    def _load_sprites(self):
        """Load all boss sprite sequences from assets folder."""
        base_path = os.path.join("assets", "Boss", "Boss")
        
        # Map states to folder names and frame counts
        sprite_folders = {
            BossState.IDLE: ("Idle", 12),
            BossState.IDLE_BLINK: ("Idle Blink", 12),
            BossState.WALKING: ("Walking", 12),
            BossState.ATTACKING: ("Attacking", 12),
            BossState.CASTING: ("Casting Spells", 12),
            BossState.HURT: ("Hurt", 6),
            BossState.DYING: ("Dying", 15),
        }
        
        for state, (folder_name, frame_count) in sprite_folders.items():
            folder_path = os.path.join(base_path, folder_name)
            
            if os.path.exists(folder_path):
                try:
                    # Load all numbered images from folder
                    frames = []
                    for i in range(frame_count):
                        filepath = os.path.join(folder_path, f"{i}.png")
                        
                        if os.path.exists(filepath):
                            surface = sdl2.ext.load_image(filepath)
                            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                            
                            # Get dimensions from first frame
                            if i == 0:
                                w = ctypes.c_int()
                                h = ctypes.c_int()
                                sdl2.SDL_QueryTexture(texture, None, None, ctypes.byref(w), ctypes.byref(h))
                                frame_width = w.value
                                frame_height = h.value
                            
                            frames.append(texture)
                            sdl2.SDL_FreeSurface(surface)
                        else:
                            print(f"Warning: Missing frame {filepath}")
                    
                    if frames:
                        self.sprites[state] = {
                            'textures': frames,  # List of individual textures
                            'width': frame_width,
                            'height': frame_height,
                            'frames': len(frames)
                        }
                except Exception as e:
                    print(f"Failed to load boss sprites from {folder_path}: {e}")
            else:
                print(f"Warning: Boss sprite folder not found: {folder_path}")
    
    def set_player(self, player):
        """
        Set player reference for AI targeting.
        
        Args:
            player: Player instance
        """
        self.player = player
    
    def is_on_screen(self):
        """
        Check if boss is visible on screen.
        
        Returns:
            bool: True if boss is visible on current screen, False otherwise
        """
        if not self.camera:
            return True  # Always active if no camera reference
        
        # Calculate boss screen position
        boss_screen_x = self.x - self.camera.camera.x
        boss_screen_right = boss_screen_x + self.width
        
        # Check if boss is within screen bounds (with small margin)
        margin = 100
        return (boss_screen_right > -margin and 
                boss_screen_x < WINDOW_WIDTH + margin)
    
    def update(self, delta_time=1):
        """
        Update boss AI, state, animation, and movement.
        
        Args:
            delta_time: Time elapsed since last update
        """
        # Handle death state
        if self.state == BossState.DYING:
            self._update_animation()
            if self.death_animation_complete:
                self.ready_for_removal = True
            return
        
        # Check for death
        if self.health <= 0:
            self.health = 0
            self.state = BossState.DYING
            self.current_frame = 0
            self.death_animation_complete = False
            self.velocity_x = 0
            self.velocity_y = 0
            self.is_jumping = False
            return
        
        # Handle hurt state (stunned, cannot act)
        if self.state == BossState.HURT:
            self._update_animation()
            if self.hurt_animation_complete:
                self.hurt_animation_complete = False
                self.current_frame = 0
                self.frame_counter = 0
                self.state = BossState.IDLE
            return
        
        # Update damage flash timer (red flash when taking damage without stagger)
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= 1
        
        # Regenerate poise slowly over time (not during HURT state)
        if self.state != BossState.HURT and self.poise < self.max_poise:
            self.poise = min(self.max_poise, self.poise + self.poise_regen_rate)
        
        # Update animation
        self._update_animation()
        
        # Update cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown == 0:
                self.is_attacking = False
                self.attack_hit_delivered = False
        
        if self.skill_cooldown < self.skill_cooldown_max:
            self.skill_cooldown += 1
        
        if self.idle_blink_cooldown > 0:
            self.idle_blink_cooldown -= 1
        
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
        
        if self.current_skill is None:
            self._check_meteor_thresholds()
        
        # Update movement if moving for skill (must be before skill update)
        if self.is_moving_to_center or self.is_returning_from_center:
            self._update_skill_movement()
        
        self._update_minions()
        
        # Update skill execution if active
        if self.current_skill is not None:
            self._update_skill()
            return
        
        # Update jumping physics
        if self.is_jumping:
            self._update_jump()
        
        # Boss only uses skills when visible on screen
        if self.skill_cooldown >= self.skill_cooldown_max and not self.is_attacking and self.is_on_screen():
            if random.random() < 0.2: 
                self._choose_random_skill()
                return
        
        # Normal combat AI (full screen range - always active)
        if not self.is_attacking and self.player:
            self._update_combat_ai()
        
        # Idle behavior (blinking and jumping)
        if self.state == BossState.IDLE and not self.is_jumping:
            self._update_idle_behavior()
    
    def _update_animation(self):
        """Update animation frame based on current state."""
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        
        # Handle DYING animation (play once, hold last frame)
        if self.state == BossState.DYING:
            if not self.death_animation_complete:
                self.frame_counter += self.animation_speed
                
                if self.frame_counter >= 1.0:
                    self.frame_counter = 0
                    self.current_frame += 1
                    
                    if self.current_frame >= sprite_data['frames']:
                        self.current_frame = sprite_data['frames'] - 1
                        self.death_animation_complete = True
            return
        
        # Handle HURT animation (play once)
        if self.state == BossState.HURT:
            if not self.hurt_animation_complete:
                self.frame_counter += self.animation_speed
                
                if self.frame_counter >= 1.0:
                    self.frame_counter = 0
                    self.current_frame += 1
                    
                    if self.current_frame >= sprite_data['frames']:
                        self.current_frame = sprite_data['frames'] - 1
                        self.hurt_animation_complete = True
            return
        
        # Handle ATTACKING animation (play once, then return to idle)
        if self.state == BossState.ATTACKING:
            self.frame_counter += self.animation_speed
            
            # Check for hit frame to deliver damage
            if not self.attack_hit_delivered and self.current_frame == self.melee_hit_frame:
                if self.attack_type == 'melee':
                    self._deliver_melee_damage()
                elif self.attack_type == 'ranged':
                    self._fire_ranged_projectile()
                self.attack_hit_delivered = True
            
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                self.current_frame += 1
                
                if self.current_frame >= sprite_data['frames']:
                    # Attack animation complete, return to idle
                    self.state = BossState.IDLE
                    self.current_frame = 0
                    self.frame_counter = 0
            return
        
        # Handle CASTING animation (play once, controlled by skill system)
        if self.state == BossState.CASTING:
            # Skill system controls when to advance frames
            return
        
        # Handle IDLE_BLINK animation (play once, then return to idle)
        if self.state == BossState.IDLE_BLINK:
            self.frame_counter += self.animation_speed
            
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                self.current_frame += 1
                
                if self.current_frame >= sprite_data['frames']:
                    # Blink complete, return to idle
                    self.state = BossState.IDLE
                    self.current_frame = 0
                    self.frame_counter = 0
                    self.idle_blink_cooldown = self.min_blink_cooldown
            return
        
        # Normal looping animation for IDLE and WALKING
        self.frame_counter += self.animation_speed
        
        if self.frame_counter >= 1.0:
            self.frame_counter = 0
            self.current_frame = (self.current_frame + 1) % sprite_data['frames']
    
    def _update_combat_ai(self):
        """
        Update boss combat AI - attack player based on distance.
        
        Boss behavior during normal combat:
        - Stands still at current position (no horizontal movement)
        - Can jump in place during ranged attacks
        - Faces the player
        - Uses melee attack if player is within melee range
        - Uses ranged attack if player is beyond melee range
        - ONLY attacks when visible on screen
        """
        if not self.player or self.attack_cooldown > 0:
            return
        
        # Boss only attacks when visible on screen
        if not self.is_on_screen():
            return
        
        # Calculate distance to player
        player_center_x = self.player.x + self.player.width / 2
        boss_center_x = self.x + self.width / 2
        distance_to_player = abs(boss_center_x - player_center_x)
        
        # Face player (no horizontal movement, only direction change)
        if player_center_x > boss_center_x:
            self.direction = Direction.RIGHT
        else:
            self.direction = Direction.LEFT
        
        # Choose attack type based on distance
        if distance_to_player <= self.melee_range:
            # Player is close - use melee attack
            self._start_melee_attack()
        else:
            # Player is far - use ranged attack
            self._start_ranged_attack()
    
    def _start_melee_attack(self):
        """Start melee attack."""
        self.state = BossState.ATTACKING
        self.current_frame = 0
        self.frame_counter = 0
        self.is_attacking = True
        self.attack_type = 'melee'
        self.attack_cooldown = self.melee_cooldown
        self.attack_hit_delivered = False
    
    def _start_ranged_attack(self):
        """Start ranged attack."""
        self.state = BossState.ATTACKING
        self.current_frame = 0
        self.frame_counter = 0
        self.is_attacking = True
        self.attack_type = 'ranged'
        self.attack_cooldown = self.ranged_cooldown
        self.attack_hit_delivered = False
        
        # Boss can jump while performing ranged attack
        if not self.is_jumping and random.random() < 0.3:  # 30% chance to jump
            self._start_jump()
    
    def _deliver_melee_damage(self):
        """Spawn melee attack effect projectile."""
        if not self.projectile_manager:
            return
        
        # Play melee attack sound
        if self.sound_manager:
            self.sound_manager.play_sound("boss_melee")
        
        # Spawn melee effect at boss center position
        boss_center_x = self.x + self.width / 2
        boss_center_y = self.y + self.height / 2
        
        # Spawn melee effect projectile
        self.projectile_manager.spawn_boss_melee_effect(
            boss_center_x, boss_center_y, 
            self.direction.value, self, self.melee_damage
        )
        
    def _fire_ranged_projectile(self):
        """Fire ranged projectile toward player."""
        if not self.projectile_manager or not self.player:
            return
        
        # Calculate projectile spawn position (center of boss)
        spawn_x = self.x + self.width / 2
        spawn_y = self.y + self.height / 2
        
        # Calculate direction to player
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        
        dx = player_center_x - spawn_x
        dy = player_center_y - spawn_y
        
        # Normalize direction
        distance = (dx**2 + dy**2) ** 0.5
        if distance > 0:
            velocity_x = (dx / distance) * self.projectile_speed
            velocity_y = (dy / distance) * self.projectile_speed
        else:
            velocity_x = self.projectile_speed if self.direction == Direction.RIGHT else -self.projectile_speed
            velocity_y = 0
        
        # Play flame projectile sound
        if self.sound_manager:
            self.sound_manager.play_sound("boss_flame")
        
        # Spawn flame projectile
        self.projectile_manager.spawn_boss_flame_projectile(
            spawn_x, spawn_y, velocity_x, velocity_y, 
            self.direction.value, self, self.ranged_damage
        )
    
    def _check_meteor_thresholds(self):
        """
        Check HP thresholds and trigger meteor skill at specific HP percentages.
        
        Meteor skill is ONLY triggered at:
        - 75% HP (first meteor)
        - 50% HP (second meteor)
        - 25% HP (third meteor)
        
        This skill is NOT part of random skill selection.
        """
        hp_percent = (self.health / self.max_health) * 100
        
        if hp_percent <= 75 and not self.meteor_triggered_75:
            self.meteor_triggered_75 = True
            self._start_meteor_skill()
        elif hp_percent <= 50 and not self.meteor_triggered_50:
            self.meteor_triggered_50 = True
            self._start_meteor_skill()
        elif hp_percent <= 25 and not self.meteor_triggered_25:
            self.meteor_triggered_25 = True
            self._start_meteor_skill()
    
    def _choose_random_skill(self):
        """
        Randomly choose and start a special skill from the available skill pool.
        
        Random skill pool includes:
        - Circular Shooting: Boss fires fireballs in circular patterns
        - Kamehameha: Boss fires a stationary laser beam
        - Summon Minions: Boss summons 2-5 minions based on HP
        
        Meteor skill is NOT included in random selection - it's HP threshold-based only.
        """
        skills = [
            # SkillType.CIRCULAR_SHOOTING,
            SkillType.KAMEHAMEHA,
            # SkillType.SUMMON_MINIONS
        ]
        
        chosen_skill = random.choice(skills)
        
        if chosen_skill == SkillType.CIRCULAR_SHOOTING:
            self._start_circular_shooting_skill()
        elif chosen_skill == SkillType.KAMEHAMEHA:
            self._start_kamehameha_skill()
        elif chosen_skill == SkillType.SUMMON_MINIONS:
            self._start_summon_minions_skill()
    
    def _start_circular_shooting_skill(self):
        """Start circular shooting skill - move to center, charge, shoot, return."""
        self.current_skill = SkillType.CIRCULAR_SHOOTING
        self.skill_phase = 0
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        # Play casting spell sound
        if self.sound_manager:
            self.sound_manager.play_sound("boss_casting")
        
        # Create and start skill instance
        self.circular_shooting_skill = CircularShootingSkill(self)
        self.circular_shooting_skill.start()
    
    def _start_meteor_skill(self):
        """Start meteor skill - meteors fall diagonally from sky."""
        self.current_skill = SkillType.METEOR
        self.skill_phase = 0
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        # Play meteor sound
        if self.sound_manager:
            self.sound_manager.play_sound("boss_meteor")
        
        # Create and start skill instance
        self.meteor_skill = MeteorSkill(self)
        self.meteor_skill.start()
    
    def _start_kamehameha_skill(self):
        """Start kamehameha skill - charge then fire laser beam."""
        self.current_skill = SkillType.KAMEHAMEHA
        self.skill_phase = 0  # 0: charge, 1: fire laser
        self.skill_timer = 0
        self.skill_cooldown = 0
        self._kamehameha_fired = False  # Reset flag to ensure laser fires exactly once
        
        self.state = BossState.CASTING
        self.current_frame = 0
        self.frame_counter = 0
    
    def _start_summon_minions_skill(self):
        """Start summon minions skill - summon minions based on HP."""
        self.current_skill = SkillType.SUMMON_MINIONS
        self.skill_phase = 0
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        # Play casting spell sound
        if self.sound_manager:
            self.sound_manager.play_sound("boss_casting")
        
        # Create and start skill instance
        self.summon_minions_skill = SummonMinionsSkill(self)
        self.summon_minions_skill.start()
    
    def _update_skill(self):
        """Update current skill execution."""
        if self.current_skill == SkillType.CIRCULAR_SHOOTING:
            self._update_circular_shooting()
        elif self.current_skill == SkillType.METEOR:
            self._update_meteor()
        elif self.current_skill == SkillType.KAMEHAMEHA:
            self._update_kamehameha()
        elif self.current_skill == SkillType.SUMMON_MINIONS:
            self._update_summon_minions()
    
    def _update_circular_shooting(self):
        """Update circular shooting skill phases."""
        if self.circular_shooting_skill:
            # Delegate to skill instance
            skill_complete = self.circular_shooting_skill.update()
            
            if skill_complete:
                # Skill finished, clean up
                self._end_skill()
                self.circular_shooting_skill = None
    
    def _update_meteor(self):
        """Update meteor skill phases."""
        if self.meteor_skill:
            # Delegate to skill instance
            skill_complete = self.meteor_skill.update()
            
            if skill_complete:
                # Skill finished, clean up
                self._end_skill()
                self.meteor_skill = None
    
    def _update_kamehameha(self):
        """Update kamehameha skill phases."""
        if self.skill_phase == 0:
            # Phase 0: Charging and firing
            self.skill_timer += 1
            
            # Advance casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            # Fire laser once during charging (at 0.5 seconds)
            if self.skill_timer == 30 and not getattr(self, '_kamehameha_fired', False):
                self._kamehameha_fired = True
                if self.sound_manager:
                    self.sound_manager.play_sound("boss_kamehameha")
                self._fire_kamehameha()
            
            if self.skill_timer >= 100:
                # Skill complete
                self._kamehameha_fired = False  # Reset for next use
                self._end_skill()
    
    def _fire_kamehameha(self):
        """Fire kamehameha laser beam."""
        if not self.projectile_manager:
            return
        
        # Face player
        if self.player:
            player_center_x = self.player.x + self.player.width / 2
            boss_center_x = self.x + self.width / 2
            if player_center_x > boss_center_x:
                self.direction = Direction.RIGHT
            else:
                self.direction = Direction.LEFT
        
        # Spawn laser beam projectile
        spawn_x = self.x + self.width / 2
        spawn_y = self.y + self.height / 2
        
        direction = self.direction.value
        
        # Spawn kamehameha laser beam (stationary, attached to boss)
        laser = self.projectile_manager.spawn_boss_kamehameha(
            spawn_x, spawn_y, direction, self, self.laser_damage
        )
    
    def _update_summon_minions(self):
        """Update summon minions skill phases."""
        if self.summon_minions_skill:
            # Delegate to skill instance
            skill_complete = self.summon_minions_skill.update()
            
            if skill_complete:
                # Skill finished, clean up
                self._end_skill()
                self.summon_minions_skill = None
    
    def _end_skill(self):
        """End current skill and return to idle."""
        self.current_skill = None
        self.skill_phase = 0
        self.skill_timer = 0
        # Do NOT reset skill_cooldown - let it regenerate naturally to prevent rapid skill spam
        self.state = BossState.IDLE
        self.current_frame = 0
        self.frame_counter = 0
    
    def _update_skill_movement(self):
        """Update boss movement during skills (moving to center or returning)."""
        threshold = 5  # Consider arrived if within 5 pixels
        
        if self.is_moving_to_center:
            # Move toward center
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = (dx**2 + dy**2) ** 0.5
            
            if distance <= threshold:
                # Arrived at center
                self.x = self.target_x
                self.y = self.target_y
                self.is_moving_to_center = False
                self.velocity_x = 0
                self.velocity_y = 0
                return
            
            # Move toward target
            if distance > 0:
                self.velocity_x = (dx / distance) * self.speed
                self.velocity_y = (dy / distance) * self.speed
            
            # Update direction for sprite flipping
            if self.velocity_x > 0:
                self.direction = Direction.RIGHT
            elif self.velocity_x < 0:
                self.direction = Direction.LEFT
            
            self.x += self.velocity_x
            self.y += self.velocity_y
        
        elif self.is_returning_from_center:
            # Move back to spawn
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = (dx**2 + dy**2) ** 0.5
            
            if distance <= threshold:
                # Arrived at spawn
                self.x = self.target_x
                self.y = self.target_y
                self.is_returning_from_center = False
                self.velocity_x = 0
                self.velocity_y = 0
                return
            
            # Move toward target
            if distance > 0:
                self.velocity_x = (dx / distance) * self.speed
                self.velocity_y = (dy / distance) * self.speed
            
            # Update direction for sprite flipping
            if self.velocity_x > 0:
                self.direction = Direction.RIGHT
            elif self.velocity_x < 0:
                self.direction = Direction.LEFT
            
            self.x += self.velocity_x
            self.y += self.velocity_y
    
    def _update_idle_behavior(self):
        """Update idle behavior - random blinking."""
        if self.idle_blink_cooldown <= 0:
            if random.random() < self.idle_blink_chance:
                self.state = BossState.IDLE_BLINK
                self.current_frame = 0
                self.frame_counter = 0
    
    def _start_jump(self):
        """Start a jump."""
        if self.is_jumping or self.jump_cooldown > 0:
            return
        
        self.is_jumping = True
        self.vel_y = self.jump_force
        self.jump_cooldown = self.min_jump_cooldown
    
    def _update_jump(self):
        """Update jumping physics."""
        self.vel_y += self.gravity
        self.y += self.vel_y
        
        # Check if landed
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vel_y = 0
            self.is_jumping = False
    
    def _update_minions(self):
        """Update all summoned minions."""
        for minion in self.minions[:]:
            minion.update()
            # Remove dead minions
            if minion.ready_for_removal:
                self.minions.remove(minion)
                minion.cleanup()
    
    def spawn_minion(self, x, y):
        """Spawn a minion at the specified position."""
        minion = BossMinion(x, y, self.sprite_factory, self.renderer, self.projectile_manager, self.minion_textures_preloaded)
        minion.set_player(self.player)
        
        # Set death callback for minion (if boss has one configured)
        if hasattr(self, 'minion_death_callback'):
            minion.on_death_callback = self.minion_death_callback
        
        self.minions.append(minion)
        return minion
    
    def take_damage(self, amount):
        """
        Apply damage to boss with poise/break bar system.
        
        Poise System:
        - Boss has virtual armor (poise). Normal attacks do not stagger.
        - Each hit reduces poise by poise_damage_per_hit.
        - If poise > 0: Boss flashes red but continues attacking (super armor).
        - If poise <= 0: Boss enters HURT state (stunned), poise resets.
        - EXCEPTION: During skill execution, boss has complete super armor (never staggers).
        
        Args:
            amount: Damage amount
        """
        if self.state == BossState.DYING:
            return
        
        # Apply health damage
        self.health -= amount
        
        if self.health > 0:
            # Check if boss is currently executing a skill - complete super armor during skills
            if self.current_skill is not None:
                # Boss is casting/executing a skill - has complete super armor
                # Take damage but do NOT stagger, do NOT cancel skill
                self.damage_flash_timer = self.damage_flash_duration
                # Poise still decreases but doesn't cause stagger during skill
                self.poise = max(0, self.poise - self.poise_damage_per_hit)
                
                # Play on_hit sound (taking damage without stagger)
                if self.sound_manager:
                    self.sound_manager.play_sound("boss_on_hit")
                
                return
            
            # Normal poise system (not during skill execution)
            # Reduce poise
            self.poise -= self.poise_damage_per_hit
            
            # Check if poise is broken
            if self.poise <= 0:
                # Poise broken - Enter HURT state (stun/stagger)
                self.state = BossState.HURT
                self.current_frame = 0
                self.frame_counter = 0
                self.hurt_animation_complete = False
                self.velocity_x = 0
                self.velocity_y = 0
                
                # Play hurt sound (staggered)
                if self.sound_manager:
                    self.sound_manager.play_sound("boss_hurt")
                
                # Reset poise
                self.poise = self.max_poise
            else:
                # Poise still active - Super armor (no stagger)
                # Show red flash effect but continue attacking/moving
                self.damage_flash_timer = self.damage_flash_duration
                
                # Play on_hit sound (taking damage without stagger)
                if self.sound_manager:
                    self.sound_manager.play_sound("boss_on_hit")
        else:
            # Boss defeated
            self.health = 0
            self.state = BossState.DYING
            self.current_frame = 0
            self.death_animation_complete = False
            self.velocity_x = 0
            self.velocity_y = 0
    
    def render(self, camera_x=0, camera_y=0):
        """
        Render boss sprite to screen using PySDL2.
        
        Args:
            camera_x: Camera x offset
            camera_y: Camera y offset
        """
        # Render minions first (behind boss)
        for minion in self.minions:
            minion.render(camera_x, camera_y)
        
        if self.state not in self.sprites:
            return
        
        sprite_data = self.sprites[self.state]
        
        # Get current frame texture
        if self.current_frame >= len(sprite_data['textures']):
            self.current_frame = 0
        
        texture = sprite_data['textures'][self.current_frame]
        
        # Source rect (entire texture since each frame is a separate file)
        src_rect = sdl2.SDL_Rect(
            0,
            0,
            sprite_data['width'],
            sprite_data['height']
        )
        
        # Destination rect (apply camera offset)
        dest_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        
        # Flip sprite based on direction
        flip = sdl2.SDL_FLIP_NONE
        if self.direction == Direction.LEFT:
            flip = sdl2.SDL_FLIP_HORIZONTAL
        
        # Apply red flash effect when taking damage without stagger (super armor)
        if self.damage_flash_timer > 0:
            sdl2.SDL_SetTextureColorMod(texture, 255, 100, 100)  # Red tint
        
        # Render
        sdl2.SDL_RenderCopyEx(
            self.renderer,
            texture,
            src_rect,
            dest_rect,
            0,
            None,
            flip
        )
        
        # Reset texture color mod after rendering
        if self.damage_flash_timer > 0:
            sdl2.SDL_SetTextureColorMod(texture, 255, 255, 255)  # Reset to normal
        
        # Render health bar above boss
        self._render_health_bar(camera_x, camera_y)
    
    def _render_health_bar(self, camera_x=0, camera_y=0):
        """
        Render health bar above the boss's head.
        
        Args:
            camera_x: Camera x offset
            camera_y: Camera y offset
        """
        bar_width = 200
        bar_height = 16
        bar_x = int(self.x + (self.width - bar_width) / 2 - camera_x)
        bar_y = int(self.y - 30 - camera_y)
        
        # Border
        border_thickness = 2
        border_rect = sdl2.SDL_Rect(
            bar_x - border_thickness,
            bar_y - border_thickness,
            bar_width + (border_thickness * 2),
            bar_height + (border_thickness * 2)
        )
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderFillRect(self.renderer, border_rect)
        
        # Background (dark red)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 60, 0, 0, 255)
        bg_rect = sdl2.SDL_Rect(bar_x, bar_y, bar_width, bar_height)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Foreground (health - color changes based on percentage)
        health_percent = max(0.0, min(1.0, self.health / self.max_health))
        fg_width = int(bar_width * health_percent)
        
        if fg_width > 0:
            if health_percent > 0.5:
                # Green
                sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 220, 0, 255)
            elif health_percent > 0.25:
                # Yellow
                sdl2.SDL_SetRenderDrawColor(self.renderer, 220, 220, 0, 255)
            else:
                # Red
                sdl2.SDL_SetRenderDrawColor(self.renderer, 220, 0, 0, 255)
            
            fg_rect = sdl2.SDL_Rect(bar_x, bar_y, fg_width, bar_height)
            sdl2.SDL_RenderFillRect(self.renderer, fg_rect)
    
    def get_bounds(self):
        """
        Get bounding box for collision detection.
        
        Returns:
            tuple: (x, y, width, height)
        """
        return (self.x, self.y, self.width, self.height)
    
    def is_alive(self):
        """Check if boss is still alive."""
        return self.health > 0
    
    def cleanup(self):
        """Clean up loaded textures and minions."""
        # Clean up minions (don't destroy their textures, they're shared)
        for minion in self.minions:
            minion.cleanup_shared()
        self.minions.clear()
        
        # Clean up preloaded minion textures
        if self.minion_textures_preloaded:
            for state_data in self.minion_textures_preloaded.values():
                for texture in state_data.get('textures', []):
                    if texture:
                        sdl2.SDL_DestroyTexture(texture)
            self.minion_textures_preloaded = None
        
        # Clean up boss textures
        for state, sprite_data in self.sprites.items():
            for texture in sprite_data.get('textures', []):
                if texture:
                    sdl2.SDL_DestroyTexture(texture)
        self.sprites.clear()


class BossManager:
    """
    Manager class for handling Boss entities.
    
    Manages boss spawning, updates, rendering, and cleanup.
    Similar to NPCManager but for Boss entities.
    """
    
    def __init__(self, sprite_factory, texture_factory, renderer, projectile_manager=None, sound_manager=None, camera=None):
        """
        Initialize Boss Manager.
        
        Args:
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            projectile_manager: ProjectileManager instance for boss projectiles (optional)
            sound_manager: SoundManager instance for audio (optional)
            camera: Camera instance for boss positioning (optional)
        """
        self.bosses = []
        self.sprite_factory = sprite_factory
        self.texture_factory = texture_factory
        self.renderer = renderer
        self.projectile_manager = projectile_manager
        self.sound_manager = sound_manager
        self.camera = camera
    
    def spawn_boss(self, x, y):
        """
        Spawn a new Boss.
        
        Args:
            x: Spawn x position
            y: Spawn y position (ground level)
            
        Returns:
            Boss: The spawned Boss instance
        """
        boss = Boss(x, y, self.sprite_factory, self.texture_factory,
                   self.renderer, self.projectile_manager, self.sound_manager, self.camera)
        self.bosses.append(boss)
        return boss
    
    def update_all(self, delta_time=1, game_map=None):
        """
        Update all bosses and clean up those marked for removal.
        
        Args:
            delta_time: Time delta for frame-independent movement
            game_map: Game map instance for collision detection (optional, not currently used)
        """
        for boss in self.bosses:
            boss.update(delta_time)
        
        # Remove bosses that are ready for removal (death animation complete)
        bosses_to_remove = [boss for boss in self.bosses if boss.ready_for_removal]
        for boss in bosses_to_remove:
            boss.cleanup()  # Clean up textures and resources before removal
        
        # Keep only bosses not marked for removal
        self.bosses = [boss for boss in self.bosses if not boss.ready_for_removal]
    
    def render_all(self, camera_x=0, camera_y=0):
        """
        Render all bosses.
        
        Args:
            camera_x: Camera x offset (world to screen conversion)
            camera_y: Camera y offset (world to screen conversion)
        """
        for boss in self.bosses:
            boss.render(camera_x, camera_y)
    
    def set_player_for_all(self, player):
        """
        Set the player reference for all bosses.
        
        Args:
            player: Player entity instance
        """
        for boss in self.bosses:
            boss.set_player(player)
    
    def get_alive_bosses(self):
        """
        Get list of all alive bosses.
        
        Returns:
            list: List of alive Boss instances
        """
        return [boss for boss in self.bosses if boss.is_alive()]
    
    def cleanup(self):
        """Clean up all bosses and their resources."""
        for boss in self.bosses:
            boss.cleanup()
        self.bosses.clear()
