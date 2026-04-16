"""
Skill W - Leaf Ranger Class

This module contains the implementation of the W skill for the Leaf Ranger character,
including logic for activating and managing the skill.
"""

from settings import SKILL_W_BUFF_DURATION, SKILL_W_COST

class SkillW:
    def __init__(self, character):
        self.character = character
        self.active = False
        self.buff_duration = SKILL_W_BUFF_DURATION
        self.cost = SKILL_W_COST

    def execute(self):
        """
        Activate the W skill, applying the buff to the character.
        """
        if self.character.stamina < self.cost:
            print("Not enough stamina to activate W skill.")
            return
        
        self.character.stamina -= self.cost
        self.active = True
        self.character.w_buff_active = True
        self.character.w_buff_timer = self.character.current_time()  # Assuming a method to get current time
        print("W skill activated: Toxin Enhancement buff applied.")

    def update_buff(self, dt):
        """
        Update the buff state, checking if it should expire.
        """
        if self.active:
            elapsed_time = self.character.current_time() - self.character.w_buff_timer
            if elapsed_time >= self.buff_duration:
                self.expire()

    def expire(self):
        """
        Expire the buff, resetting the character's state.
        """
        self.active = False
        self.character.w_buff_active = False
        print("W skill expired: Toxin Enhancement buff removed.")
"""