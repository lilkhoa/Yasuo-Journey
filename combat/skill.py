import sdl2.ext
import time

class Skill:
    def __init__(self, owner, cooldown_time):
        self.owner = owner
        self.cooldown_time = cooldown_time
        self.last_cast_time = 0
        self.active = False
    
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