"""
Boss Skills Module
Implements special boss skills including circular shooting, meteor rain, kamehameha, and summon minions.
"""
import math
import random
from enum import Enum
from settings import (
    CIRCULAR_CHARGE_DURATION,
    CIRCULAR_SHOOT_DURATION,
    CIRCULAR_PROJECTILES_PER_STREAM,
    CIRCULAR_VELOCITY_MULTIPLIER,
    METEOR_CHARGE_DURATION,
    METEOR_DURATION,
    METEOR_SPAWN_INTERVAL,
    METEOR_VELOCITY_X_MIN,
    METEOR_VELOCITY_X_MAX,
    METEOR_VELOCITY_Y_MIN,
    METEOR_VELOCITY_Y_MAX,
    WINDOW_WIDTH,
    SUMMON_CHARGE_DURATION,
    SUMMON_WAIT_DURATION,
)


class SkillPhase(Enum):
    """Enumeration for skill execution phases."""
    DASH_TO_CENTER = 0
    CHARGING = 1
    EXECUTING = 2
    RETURNING = 3
    COMPLETE = 4


class CircularShootingSkill:
    """
    Circular Shooting Skill: Boss dashes to screen center and fires circular barrages.
    
    Phases:
    0 - DASH_TO_CENTER: Boss moves to screen center
    1 - CHARGING: Boss charges up (casting animation)
    2 - EXECUTING: Boss fires circular projectile streams
    3 - RETURNING: Boss returns to original position
    4 - COMPLETE: Skill finished
    """
    
    def __init__(self, boss):
        """
        Initialize circular shooting skill.
        
        Args:
            boss: Reference to Boss instance
        """
        self.boss = boss
        self.phase = SkillPhase.DASH_TO_CENTER
        self.timer = 0
        
        # Skill parameters
        self.charge_duration = CIRCULAR_CHARGE_DURATION
        self.shoot_duration = CIRCULAR_SHOOT_DURATION
        self.volley_interval = 60  # Fire every 60 frames (3 volleys per second)
        self.projectiles_per_stream = CIRCULAR_PROJECTILES_PER_STREAM
        self.num_streams = 2  # 2 simultaneous streams
        
        # Store original position for return
        self.original_x = boss.x
        self.original_y = boss.y
    
    def start(self):
        """Start the skill execution."""
        from entities.boss import BossState
        
        self.phase = SkillPhase.DASH_TO_CENTER
        self.timer = 0
        
        # Store original position
        self.original_x = self.boss.x
        self.original_y = self.boss.y
        
        # Set movement to center
        self.boss.target_x = self.boss.center_x
        self.boss.target_y = self.boss.ground_y
        self.boss.is_moving_to_center = True
        self.boss.state = BossState.WALKING
    
    def update(self):
        """
        Update skill execution.
        
        Returns:
            bool: True if skill is complete, False otherwise
        """
        from entities.boss import BossState
        
        if self.phase == SkillPhase.DASH_TO_CENTER:
            # Phase 0: Moving to center (handled by boss._update_skill_movement)
            if not self.boss.is_moving_to_center:
                # Arrived at center, start charging
                self.phase = SkillPhase.CHARGING
                self.timer = self.charge_duration
                self.boss.state = BossState.CASTING
                self.boss.current_frame = 0
                self.boss.frame_counter = 0
        
        elif self.phase == SkillPhase.CHARGING:
            # Phase 1: Charging
            self.timer -= 1
            
            # Advance casting animation
            self.boss.frame_counter += self.boss.animation_speed
            if self.boss.frame_counter >= 1.0:
                self.boss.frame_counter = 0
                sprite_data = self.boss.sprites[BossState.CASTING]
                self.boss.current_frame = (self.boss.current_frame + 1) % sprite_data['frames']
            
            if self.timer <= 0:
                # Charge complete, start shooting
                self.phase = SkillPhase.EXECUTING
                self.timer = self.shoot_duration
                self._fire_volleys()
        
        elif self.phase == SkillPhase.EXECUTING:
            # Phase 2: Shooting circular projectiles
            self.timer -= 1
            
            # Fire volleys at intervals
            if self.timer % self.volley_interval == 0 and self.timer > 0:
                self._fire_volleys()
            
            # Continue casting animation
            self.boss.frame_counter += self.boss.animation_speed
            if self.boss.frame_counter >= 1.0:
                self.boss.frame_counter = 0
                sprite_data = self.boss.sprites[BossState.CASTING]
                self.boss.current_frame = (self.boss.current_frame + 1) % sprite_data['frames']
            
            if self.timer <= 0:
                # Shooting complete, return to original position
                self.phase = SkillPhase.RETURNING
                self.boss.target_x = self.original_x
                self.boss.target_y = self.original_y
                self.boss.is_returning_from_center = True
                self.boss.state = BossState.WALKING
        
        elif self.phase == SkillPhase.RETURNING:
            # Phase 3: Returning to original position (handled by boss._update_skill_movement)
            if not self.boss.is_returning_from_center:
                # Returned, skill complete
                self.phase = SkillPhase.COMPLETE
                return True
        
        return False
    
    def _fire_volleys(self):
        """Fire two circular volleys of projectiles simultaneously."""
        if not self.boss.projectile_manager:
            return
        
        # Calculate spawn position (boss center)
        spawn_x = self.boss.x + self.boss.width / 2
        spawn_y = self.boss.y + self.boss.height / 2
        
        # Fire two streams with offset angles for visual variety
        angle_offset_stream2 = 360 / (self.projectiles_per_stream * 2)  # Offset second stream by half-angle
        
        for stream in range(self.num_streams):
            angle_offset = angle_offset_stream2 * stream
            
            for i in range(self.projectiles_per_stream):
                # Calculate angle (evenly distributed in 360 degrees)
                angle = (360 / self.projectiles_per_stream) * i + angle_offset
                angle_rad = math.radians(angle)
                
                # Calculate velocity
                velocity_x = math.cos(angle_rad) * self.boss.projectile_speed * CIRCULAR_VELOCITY_MULTIPLIER
                velocity_y = math.sin(angle_rad) * self.boss.projectile_speed * CIRCULAR_VELOCITY_MULTIPLIER
                
                # Determine direction for sprite flipping
                direction = 1 if velocity_x >= 0 else -1
                
                # Spawn circular flame projectile
                self.boss.projectile_manager.spawn_boss_circular_flame(
                    spawn_x, spawn_y,
                    velocity_x, velocity_y,
                    self.boss.ranged_damage,
                    direction,
                    self.boss
                )

class MeteorSkill:
    """
    Meteor Skill: Boss stands still and summons meteors from the sky.
    
    Phases:
    0 - CHARGING: Boss charges up (casting animation)
    1 - EXECUTING: Meteors fall diagonally from sky, explode on impact
    2 - COMPLETE: Skill finished
    """
    
    def __init__(self, boss):
        """
        Initialize meteor skill.
        
        Args:
            boss: Reference to Boss instance
        """
        self.boss = boss
        self.phase = 0  # 0: charging, 1: executing, 2: complete
        self.timer = 0
        
        # Skill parameters
        self.charge_duration = METEOR_CHARGE_DURATION
        self.meteor_duration = METEOR_DURATION
        self.spawn_interval = METEOR_SPAWN_INTERVAL
    
    def start(self):
        """Start the skill execution."""
        from entities.boss import BossState
        
        self.phase = 0
        self.timer = 0
        
        # Boss stands still in CASTING state
        self.boss.state = BossState.CASTING
        self.boss.current_frame = 0
        self.boss.frame_counter = 0
        self.boss.velocity_x = 0
        self.boss.velocity_y = 0
    
    def update(self):
        """
        Update skill execution.
        
        Returns:
            bool: True if skill is complete, False otherwise
        """
        from entities.boss import BossState
        
        if self.phase == 0:
            # Phase 0: Charging
            self.timer += 1
            
            # Advance casting animation
            self.boss.frame_counter += self.boss.animation_speed
            if self.boss.frame_counter >= 1.0:
                self.boss.frame_counter = 0
                sprite_data = self.boss.sprites[BossState.CASTING]
                self.boss.current_frame = (self.boss.current_frame + 1) % sprite_data['frames']
            
            if self.timer >= self.charge_duration:
                # Charge complete, start meteors
                self.phase = 1
                self.timer = 0
        
        elif self.phase == 1:
            # Phase 1: Meteors falling
            self.timer += 1
            
            # Continue casting animation
            self.boss.frame_counter += self.boss.animation_speed
            if self.boss.frame_counter >= 1.0:
                self.boss.frame_counter = 0
                sprite_data = self.boss.sprites[BossState.CASTING]
                self.boss.current_frame = (self.boss.current_frame + 1) % sprite_data['frames']
            
            # Spawn meteors at intervals
            if self.timer % self.spawn_interval == 0:
                self._spawn_meteor()
            
            if self.timer >= self.meteor_duration:
                # Meteor skill complete
                self.phase = 2
                return True
        
        return False
    
    def _spawn_meteor(self):
        """Spawn a meteor that falls diagonally from the sky."""
        if not self.boss.projectile_manager:
            return
        
        # Random X position across screen width
        spawn_x = random.uniform(0, WINDOW_WIDTH)
        spawn_y = -100  # Spawn above screen
        
        # Diagonal velocity (right-to-left = negative X, top-to-bottom = positive Y)
        velocity_x = random.uniform(METEOR_VELOCITY_X_MIN, METEOR_VELOCITY_X_MAX)  # Always negative
        velocity_y = random.uniform(METEOR_VELOCITY_Y_MIN, METEOR_VELOCITY_Y_MAX)  # Always positive
        
        # Spawn meteor projectile
        self.boss.projectile_manager.spawn_boss_meteor(
            spawn_x, spawn_y,
            velocity_x, velocity_y,
            self.boss.meteor_damage,
            self.boss
        )


class SummonMinionsSkill:
    """
    Summon Minions Skill: Boss summons minions based on current HP.
    
    Phases:
    0 - CHARGING: Boss charges up (casting animation)
    1 - COMPLETE: Skill finished
    
    Minion count based on boss HP:
    - 75-100% HP: 2 minions
    - 50-75% HP: 3 minions
    - 25-50% HP: 4 minions
    - 0-25% HP: 5 minions
    """
    
    def __init__(self, boss):
        """
        Initialize summon minions skill.
        
        Args:
            boss: Reference to Boss instance
        """
        self.boss = boss
        self.phase = 0  # 0: charging, 1: complete
        self.timer = 0
        
        # Skill parameters
        self.charge_duration = SUMMON_CHARGE_DURATION
        self.wait_duration = SUMMON_WAIT_DURATION
    
    def start(self):
        """Start the skill execution."""
        from entities.boss import BossState
        
        self.phase = 0
        self.timer = 0
        
        # Boss stands still in CASTING state
        self.boss.state = BossState.CASTING
        self.boss.current_frame = 0
        self.boss.frame_counter = 0
        self.boss.velocity_x = 0
        self.boss.velocity_y = 0
    
    def update(self):
        """
        Update skill execution.
        
        Returns:
            bool: True if skill is complete, False otherwise
        """
        from entities.boss import BossState
        
        if self.phase == 0:
            # Phase 0: Charging
            self.timer += 1
            
            # Advance casting animation
            self.boss.frame_counter += self.boss.animation_speed
            if self.boss.frame_counter >= 1.0:
                self.boss.frame_counter = 0
                sprite_data = self.boss.sprites[BossState.CASTING]
                self.boss.current_frame = (self.boss.current_frame + 1) % sprite_data['frames']
            
            if self.timer >= self.charge_duration:
                # Charge complete, spawn minions
                self.phase = 1
                self.timer = 0
                self._spawn_minions()
                return True
        
        return False
    
    def _spawn_minions(self):
        """Spawn minions based on boss HP."""
        # Determine number of minions based on boss HP
        hp_percent = (self.boss.health / self.boss.max_health) * 100
        
        if hp_percent >= 75:
            num_minions = 2
        elif hp_percent >= 50:
            num_minions = 3
        elif hp_percent >= 25:
            num_minions = 4
        else:
            num_minions = 5
        
        # Calculate spawn positions around boss
        boss_center_x = self.boss.x + self.boss.width / 2
        boss_center_y = self.boss.y + self.boss.height / 2
        
        # Spawn minions in a circle around boss with radius 150
        spawn_radius = 150
        
        for i in range(num_minions):
            angle = (360 / num_minions) * i
            angle_rad = math.radians(angle)
            
            spawn_x = boss_center_x + math.cos(angle_rad) * spawn_radius - 48  # Center minion (96/2)
            spawn_y = boss_center_y + math.sin(angle_rad) * spawn_radius - 48
            
            # Spawn minion directly via boss
            self.boss.spawn_minion(spawn_x, spawn_y)
