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

    # --- SỬA ĐỔI Ở ĐÂY ---
    # Thêm *args và **kwargs để nhận các tham số lạ (như skill_surface)
    def cast(self, world_entities, factory, renderer, *args, **kwargs):
        if self.is_ready():
            self.last_cast_time = time.time()
            self.active = True
            # Truyền tiếp *args và **kwargs xuống hàm execute của con (SkillQ, SkillW...)
            return self.execute(world_entities, factory, renderer, *args, **kwargs)
        return None

    def execute(self, world_entities, factory, renderer, *args, **kwargs):
        # Hàm này sẽ được ghi đè bởi các skill con
        pass

    def update(self, dt):
        pass