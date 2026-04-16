class PoisonProjectile:
    def __init__(self, x, y, direction, owner, renderer, damage_multiplier=1.0):
        self.x = x
        self.y = y
        self.direction = direction
        self.owner = owner
        self.renderer = renderer
        self.damage_multiplier = damage_multiplier
        self.active = True

    def update(self, dt):
        self.x += self.direction * 10 * dt  # Move projectile
        if self.x < 0 or self.x > 800:  # Example screen bounds
            self.active = False

class PlantProjectile:
    def __init__(self, x, y, direction, owner, renderer):
        self.x = x
        self.y = y
        self.direction = direction
        self.owner = owner
        self.renderer = renderer
        self.active = True

    def update(self, dt):
        self.x += self.direction * 5 * dt  # Move projectile
        if self.x < 0 or self.x > 800:  # Example screen bounds
            self.active = False

class HealDustProjectile:
    def __init__(self, x, y, direction, owner, renderer):
        self.x = x
        self.y = y
        self.direction = direction
        self.owner = owner
        self.renderer = renderer
        self.active = True

    def update(self, dt):
        self.x += self.direction * 3 * dt  # Move projectile
        if self.x < 0 or self.x > 800:  # Example screen bounds
            self.active = False

class NormalArrowProjectile:
    def __init__(self, x, y, direction, owner, renderer):
        self.x = x
        self.y = y
        self.direction = direction
        self.owner = owner
        self.renderer = renderer
        self.active = True

    def update(self, dt):
        self.x += self.direction * 7 * dt  # Move projectile
        if self.x < 0 or self.x > 800:  # Example screen bounds
            self.active = False