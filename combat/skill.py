import sdl2.ext
import time

class Skill:
    def __init__(self, owner, cooldown_time):
        self.owner = owner
        self.cooldown_time = cooldown_time
        self.last_cast_time = 0
        self.active = False
        self.level = 0
        self.base_cooldown = cooldown_time
        self.damage_multiplier = 1.0

    def update_stats(self, level):
        """Update stats based on level"""
        if level > self.level:
            # Calculate new stats
            # Cooldown usually handled by Player CooldownManager for Q/W/E
            # But internal CD needs update too
            from settings import SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN, SKILL_DAMAGE_GROWTH
            
            # Growth formula: Base * (Growth ^ Level)
            self.damage_multiplier = SKILL_DAMAGE_GROWTH ** level
            
            # Cooldown formula: Iterative reduction
            current_cd = self.base_cooldown
            for _ in range(level):
                reduction = max(current_cd * SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN)
                current_cd -= reduction
            
            self.cooldown_time = max(0.1, current_cd) # Keep 0.1s minimum for internal logic
            
            self.level = level
            print(f"Skill upgraded to Level {level}. Dmg Mul: {self.damage_multiplier:.2f}, CD: {self.cooldown_time:.2f}s")
    
    def is_ready(self):
        return (time.time() - self.last_cast_time) >= self.cooldown_time


    def cast(self, world_entities, factory, renderer, *args, **kwargs):
        if self.is_ready():
            self.last_cast_time = time.time()
            self.active = True
            return self.execute(world_entities, factory, renderer, *args, **kwargs)
        return None

    def execute(self, world_entities, factory, renderer, *args, **kwargs):
        pass

    def update(self, dt):
        pass