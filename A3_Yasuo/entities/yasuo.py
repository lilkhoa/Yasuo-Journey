"""
Yasuo Class - Character specific logic and skills for Yasuo
Inherits from BaseChar and implements unique abilities and behaviors.
"""

import sys
import os
import sdl2
import sdl2.ext
from entities.base_char import BaseChar
from combat.player_2.skill_q import SkillQLaser
from combat.player_2.skill_w import SkillW
from combat.player_2.skill_e import SkillE
from settings import SKILL_W_COST, SKILL_E_2_COST

class Yasuo(BaseChar):
    """
    Yasuo - Character with unique skills and abilities.
    
    Inherits from BaseChar and implements specific logic for Yasuo.
    """

    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        """
        Initialize Yasuo.
        
        Args:
            world: SDL2 entity world
            factory: Sprite factory
            x, y: Starting position
            sound_manager: Sound manager instance
            renderer_ptr: SDL2 renderer pointer
        """
        super().__init__(world, factory, x, y, sound_manager, renderer_ptr)

        # Initialize Yasuo specific skills
        self.skill_q = SkillQLaser(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)

        # Additional Yasuo specific attributes
        self.active_lasers = []

    def update(self, dt, world, factory, renderer, game_map=None, boxes=None):
        """
        Update method for Yasuo.
        
        Args:
            dt: Delta time
            world: Entity world
            factory: Sprite factory
            renderer: Renderer
            game_map: Game map for collision
            boxes: Obstacle boxes
        """
        super().update(dt, world, factory, renderer, game_map, boxes)
        # Additional update logic for Yasuo can be added here

    def attack(self):
        """
        Override: Yasuo's attack logic.
        """
        super().attack()
        # Additional attack logic specific to Yasuo can be added here

    # Additional methods specific to Yasuo can be added here
