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
    
    def __init__(self, x, y, sprite_factory, texture_factory, renderer, projectile_manager=None):
        """
        Initialize Boss.
        
        Args:
            x: Initial x position
            y: Initial y position (ground level)
            sprite_factory: PySDL2 sprite factory
            texture_factory: PySDL2 texture factory
            renderer: PySDL2 renderer
            projectile_manager: ProjectileManager for spawning projectiles
        """
        # Position and dimensions
        self.x = x
        self.y = y
        self.spawn_x = x
        self.spawn_y = y
        self.width = 256
        self.height = 256
        
        # Screen center for circular shooting skill
        self.center_x = WINDOW_WIDTH // 2 - self.width // 2
        self.center_y = WINDOW_HEIGHT // 2 - self.height // 2
        
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
        
        # Load boss sprites
        self._load_sprites()
    
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
        
        # Check HP thresholds for meteor skill (priority)
        self._check_meteor_thresholds()
        
        # Update skill execution if active
        if self.current_skill is not None:
            self._update_skill()
            return
        
        # Update movement if moving for skill
        if self.is_moving_to_center or self.is_returning_from_center:
            self._update_skill_movement()
            return
        
        # Update jumping physics
        if self.is_jumping:
            self._update_jump()
        
        # Random skill usage (if cooldown ready and not attacking)
        if self.skill_cooldown >= self.skill_cooldown_max and not self.is_attacking:
            if random.random() < 0.01:  # 1% chance per frame to use skill
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
        """Update boss combat AI - attack player based on distance."""
        if not self.player or self.attack_cooldown > 0:
            return
        
        # Calculate distance to player
        player_center_x = self.player.x + self.player.width / 2
        boss_center_x = self.x + self.width / 2
        distance_to_player = abs(boss_center_x - player_center_x)
        
        # Face player
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
        """Deliver melee damage to player if in range."""
        if not self.player:
            return
        
        player_center_x = self.player.x + self.player.width / 2
        boss_center_x = self.x + self.width / 2
        distance = abs(boss_center_x - player_center_x)
        
        if distance <= self.melee_range:
            # Player is in range, deal damage
            if hasattr(self.player, 'take_damage'):
                self.player.take_damage(self.melee_damage)
    
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
        
        # Spawn projectile (will be implemented with projectile system)
        # self.projectile_manager.spawn_boss_projectile(
        #     spawn_x, spawn_y, velocity_x, velocity_y, 
        #     self.ranged_damage, self.direction.value
        # )
    
    def _check_meteor_thresholds(self):
        """Check HP thresholds and trigger meteor skill."""
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
        """Randomly choose and start a special skill."""
        skills = [
            SkillType.CIRCULAR_SHOOTING,
            SkillType.KAMEHAMEHA,
            SkillType.SUMMON_MINIONS
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
        self.skill_phase = 0  # 0: move to center, 1: charge, 2: shoot, 3: return
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        # Set movement to center
        self.target_x = self.center_x
        self.target_y = self.ground_y  # Stay on ground
        self.is_moving_to_center = True
        self.state = BossState.WALKING
    
    def _start_meteor_skill(self):
        """Start meteor skill - meteors fall diagonally from sky."""
        self.current_skill = SkillType.METEOR
        self.skill_phase = 0  # 0: charge, 1: meteors falling
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        self.state = BossState.CASTING
        self.current_frame = 0
        self.frame_counter = 0
    
    def _start_kamehameha_skill(self):
        """Start kamehameha skill - charge then fire laser beam."""
        self.current_skill = SkillType.KAMEHAMEHA
        self.skill_phase = 0  # 0: charge, 1: fire laser
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        self.state = BossState.CASTING
        self.current_frame = 0
        self.frame_counter = 0
    
    def _start_summon_minions_skill(self):
        """Start summon minions skill - summon shooter NPCs."""
        self.current_skill = SkillType.SUMMON_MINIONS
        self.skill_phase = 0  # 0: charge, 1: summon
        self.skill_timer = 0
        self.skill_cooldown = 0
        
        self.state = BossState.CASTING
        self.current_frame = 0
        self.frame_counter = 0
    
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
        if self.skill_phase == 0:
            # Phase 0: Moving to center (handled by _update_skill_movement)
            if not self.is_moving_to_center:
                # Arrived at center, start charging
                self.skill_phase = 1
                self.skill_timer = 60  # 1 second charge
                self.state = BossState.CASTING
                self.current_frame = 0
                self.frame_counter = 0
        
        elif self.skill_phase == 1:
            # Phase 1: Charging
            self.skill_timer -= 1
            
            # Advance casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            if self.skill_timer <= 0:
                # Charge complete, start shooting
                self.skill_phase = 2
                self.skill_timer = 120  # 2 seconds of shooting
                self._fire_circular_projectiles()
        
        elif self.skill_phase == 2:
            # Phase 2: Shooting circular projectiles
            self.skill_timer -= 1
            
            # Fire projectiles every 20 frames
            if self.skill_timer % 20 == 0:
                self._fire_circular_projectiles()
            
            # Continue casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            if self.skill_timer <= 0:
                # Shooting complete, return to spawn
                self.skill_phase = 3
                self.target_x = self.spawn_x
                self.target_y = self.spawn_y
                self.is_returning_from_center = True
                self.state = BossState.WALKING
        
        elif self.skill_phase == 3:
            # Phase 3: Returning to spawn (handled by _update_skill_movement)
            if not self.is_returning_from_center:
                # Returned to spawn, skill complete
                self._end_skill()
    
    def _fire_circular_projectiles(self):
        """Fire projectiles in a circular pattern."""
        if not self.projectile_manager:
            return
        
        # Fire 8 projectiles in a circle (45 degrees apart)
        num_projectiles = 8
        spawn_x = self.x + self.width / 2
        spawn_y = self.y + self.height / 2
        
        import math
        for i in range(num_projectiles):
            angle = (360 / num_projectiles) * i
            angle_rad = math.radians(angle)
            
            velocity_x = math.cos(angle_rad) * self.projectile_speed
            velocity_y = math.sin(angle_rad) * self.projectile_speed
            
            # Spawn projectile (will be implemented with projectile system)
            # self.projectile_manager.spawn_boss_circular_projectile(
            #     spawn_x, spawn_y, velocity_x, velocity_y, self.ranged_damage
            # )
    
    def _update_meteor(self):
        """Update meteor skill phases."""
        if self.skill_phase == 0:
            # Phase 0: Charging
            self.skill_timer += 1
            
            # Advance casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            if self.skill_timer >= 60:  # 1 second charge
                # Charge complete, start meteors
                self.skill_phase = 1
                self.skill_timer = 0
        
        elif self.skill_phase == 1:
            # Phase 1: Meteors falling
            self.skill_timer += 1
            
            # Continue casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            # Spawn meteors every 15 frames
            if self.skill_timer % 15 == 0:
                self._spawn_meteor()
            
            if self.skill_timer >= 180:  # 3 seconds of meteors
                # Meteor skill complete
                self._end_skill()
    
    def _spawn_meteor(self):
        """Spawn a meteor that falls diagonally."""
        if not self.projectile_manager:
            return
        
        # Random X position at top of screen
        spawn_x = random.randint(0, WINDOW_WIDTH)
        spawn_y = -50
        
        # Diagonal velocity (falling down and slightly sideways)
        velocity_x = random.uniform(-3, 3)
        velocity_y = random.uniform(8, 12)  # Falling down
        
        # Spawn meteor projectile (will be implemented with projectile system)
        # self.projectile_manager.spawn_boss_meteor(
        #     spawn_x, spawn_y, velocity_x, velocity_y, self.meteor_damage
        # )
    
    def _update_kamehameha(self):
        """Update kamehameha skill phases."""
        if self.skill_phase == 0:
            # Phase 0: Charging
            self.skill_timer += 1
            
            # Advance casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            if self.skill_timer >= 90:  # 1.5 second charge
                # Charge complete, fire laser
                self.skill_phase = 1
                self.skill_timer = 0
                self._fire_kamehameha()
        
        elif self.skill_phase == 1:
            # Phase 1: Laser active
            self.skill_timer += 1
            
            # Continue casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            if self.skill_timer >= 120:  # 2 second laser duration
                # Laser complete
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
        
        velocity_x = self.projectile_speed * 2 * self.direction.value
        velocity_y = 0
        
        # Spawn kamehameha projectile (will be implemented with projectile system)
        # self.projectile_manager.spawn_boss_kamehameha(
        #     spawn_x, spawn_y, velocity_x, velocity_y, self.laser_damage, self.direction.value
        # )
    
    def _update_summon_minions(self):
        """Update summon minions skill phases."""
        if self.skill_phase == 0:
            # Phase 0: Charging
            self.skill_timer += 1
            
            # Advance casting animation
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1.0:
                self.frame_counter = 0
                sprite_data = self.sprites[BossState.CASTING]
                self.current_frame = (self.current_frame + 1) % sprite_data['frames']
            
            if self.skill_timer >= 60:  # 1 second charge
                # Charge complete, summon minions
                self.skill_phase = 1
                self.skill_timer = 0
                self._summon_shooter_minions()
        
        elif self.skill_phase == 1:
            # Phase 1: Summon complete, wait a bit
            self.skill_timer += 1
            
            if self.skill_timer >= 30:  # 0.5 second wait
                # Summon complete
                self._end_skill()
    
    def _summon_shooter_minions(self):
        """Summon 2-3 shooter minions at random positions."""
        # This will need to interface with the game's NPC spawning system
        # For now, just log the summon
        num_minions = random.randint(2, 3)
       
        # Minions would be spawned by the game manager
        # game_manager.spawn_boss_minion(x, y, "shooter")
    
    def _end_skill(self):
        """End current skill and return to idle."""
        self.current_skill = None
        self.skill_phase = 0
        self.skill_timer = 0
        self.skill_cooldown = 0
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
    
    def take_damage(self, amount):
        """
        Apply damage to boss.
        
        Args:
            amount: Damage amount
        """
        if self.state == BossState.DYING:
            return
        
        self.health -= amount
        
        if self.health > 0:
            # Enter hurt state (brief stun)
            self.state = BossState.HURT
            self.current_frame = 0
            self.frame_counter = 0
            self.hurt_animation_complete = False
            self.velocity_x = 0
            self.velocity_y = 0
            
            # Cancel current skill if any
            if self.current_skill is not None:
                self.current_skill = None
                self.skill_phase = 0
                self.skill_timer = 0
                self.is_moving_to_center = False
                self.is_returning_from_center = False
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
        """Clean up loaded textures."""
        for state, sprite_data in self.sprites.items():
            for texture in sprite_data.get('textures', []):
                if texture:
                    sdl2.SDL_DestroyTexture(texture)
        self.sprites.clear()
