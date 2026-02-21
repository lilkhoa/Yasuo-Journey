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
        """Update stats based on level and player's attack damage"""
        if level > self.level:
            from settings import SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN, SKILL_DAMAGE_GROWTH, SKILL_AD_RATIO
            
            # Level scaling: Base * (Growth ^ Level)
            level_scaling = SKILL_DAMAGE_GROWTH ** level
            
            # AD scaling: player's current AD relative to base AD
            if hasattr(self.owner, 'attack_damage') and hasattr(self.owner, 'base_attack_damage'):
                ad_scaling = (self.owner.attack_damage / self.owner.base_attack_damage) * SKILL_AD_RATIO
            else:
                ad_scaling = 1.0
            
            # Combined damage multiplier: level scaling * AD scaling
            self.damage_multiplier = level_scaling * ad_scaling
            
            # Cooldown formula: Iterative reduction
            current_cd = self.base_cooldown
            for _ in range(level):
                reduction = max(current_cd * SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN)
                current_cd -= reduction
            
            self.cooldown_time = max(0.1, current_cd) # Keep 0.1s minimum for internal logic
            
            self.level = level
            print(f"Skill upgraded to Level {level}. Dmg Mul: {self.damage_multiplier:.2f} (Level: {level_scaling:.2f} × AD: {ad_scaling:.2f}), CD: {self.cooldown_time:.2f}s")
    
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