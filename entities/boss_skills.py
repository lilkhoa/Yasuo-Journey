"""
Boss Skills Module
Implements special boss skills including circular shooting, meteor rain, kamehameha, and summon minions.
"""
import math
from enum import Enum


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
        self.charge_duration = 60  # 1 second
        self.shoot_duration = 180  # 3 seconds
        self.volley_interval = 60  # Fire every 60 frames (3 volleys per second)
        self.projectiles_per_stream = 12  # 8 directions
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
        
        print(f"[CircularShootingSkill] Started - Dashing to center from ({self.original_x:.0f}, {self.original_y:.0f})")
    
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
                print(f"[CircularShootingSkill] Phase 1: Charging at center ({self.boss.x:.0f}, {self.boss.y:.0f})")
        
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
                print(f"[CircularShootingSkill] Phase 2: Executing - Firing circular barrages")
        
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
                print(f"[CircularShootingSkill] Phase 3: Returning to original position ({self.original_x:.0f}, {self.original_y:.0f})")
        
        elif self.phase == SkillPhase.RETURNING:
            # Phase 3: Returning to original position (handled by boss._update_skill_movement)
            if not self.boss.is_returning_from_center:
                # Returned, skill complete
                self.phase = SkillPhase.COMPLETE
                print(f"[CircularShootingSkill] Phase 4: Complete")
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
                velocity_x = math.cos(angle_rad) * self.boss.projectile_speed * 0.6  # Slightly slower for dodge-ability
                velocity_y = math.sin(angle_rad) * self.boss.projectile_speed * 0.6
                
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
        
        print(f"[CircularShootingSkill] Fired {self.num_streams * self.projectiles_per_stream} projectiles in circular pattern")
