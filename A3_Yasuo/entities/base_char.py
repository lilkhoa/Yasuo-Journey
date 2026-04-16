"""
BaseChar Class - Base class for character entities in the game.

This class includes common properties and methods shared by all characters,
such as health, stamina, movement, and basic attack logic.
"""

import time

class BaseChar:
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        self.world = world
        self.factory = factory
        self.x = x
        self.y = y
        self.sound_manager = sound_manager
        self.renderer_ptr = renderer_ptr
        
        self.health = 100
        self.stamina = 100
        self.state = 'idle'
        self.facing_right = True
        self.cooldowns = {}
        self.frame_index = 0

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def attack(self):
        if self.cooldowns.get("attack", 0) <= 0:
            self.state = 'attacking'
            self.cooldowns["attack"] = 1.0  # Example cooldown duration
            print(f"{self.__class__.__name__} attacks!")

    def update(self, dt):
        # Update cooldowns
        for skill in self.cooldowns:
            self.cooldowns[skill] -= dt
            if self.cooldowns[skill] < 0:
                self.cooldowns[skill] = 0

    def die(self):
        self.state = 'dead'
        print(f"{self.__class__.__name__} has died.")

    def on_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.die()

    def is_alive(self):
        return self.health > 0
