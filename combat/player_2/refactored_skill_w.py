import sdl2
import sdl2.ext
import time
from combat.refactored_skill import BaseSkill
from settings import SKILL_W_BUFF_DURATION

# ─────────────────────────────────────────────────────────────────────────────
# SKILL W - TOXIN ENHANCEMENT
# ─────────────────────────────────────────────────────────────────────────────

class SkillW(BaseSkill):
    """
    W Skill: Toxin Enhancement Buff
    Toggles a buff that lasts for SKILL_W_BUFF_DURATION seconds.
    """

    def __init__(self, owner):
        super().__init__(owner, name="Toxin Enhancement", base_cooldown=0.1)
        self.buff_active_time = 0
        
    def execute(self, world=None, factory=None, renderer=None, **kwargs):
        if not hasattr(self.owner, 'w_buff_active'): self.owner.w_buff_active = False
        if not hasattr(self.owner, 'w_buff_timer'): self.owner.w_buff_timer = 0
        if not hasattr(self.owner, 'w_attack_toggle'): self.owner.w_attack_toggle = False 
        if not hasattr(self.owner, 'w_poison_applied'): self.owner.w_poison_applied = {} 

        self.owner.w_buff_active = True
        self.owner.w_buff_timer = time.time()
        self.owner.w_attack_toggle = False 
        
        if hasattr(self.owner, 'sound_manager') and self.owner.sound_manager:
            try: self.owner.sound_manager.play_sound("skill_w")
            except: pass
        
        return self 

    def update_buff(self, dt):
        """Called from LeafRanger update() to manage buff duration."""
        if not hasattr(self.owner, 'w_buff_active') or not self.owner.w_buff_active: return
        
        elapsed = time.time() - self.owner.w_buff_timer
        
        if elapsed >= SKILL_W_BUFF_DURATION:
            self.owner.w_buff_active = False
            self.owner.w_attack_toggle = False
            self.owner.w_poison_applied.clear()