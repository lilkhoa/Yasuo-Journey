import sdl2
import sdl2.ext
import time
from combat.skill import Skill
from settings import SKILL_W_BUFF_DURATION

# ─────────────────────────────────────────────────────────────────────────────
# SKILL W - TOXIN ENHANCEMENT
# ─────────────────────────────────────────────────────────────────────────────

class SkillW(Skill):
    """
    W Skill: Toxin Enhancement Buff
    
    Toggles a buff that lasts for SKILL_W_BUFF_DURATION seconds.
    While active, normal attacks alternate between:
    - Poison shot: Damage + optional DoT
    - Plant shot: Roots the first NPC hit
    - Healing dust: Spawned from jump+attack, heals allies
    
    This is a toggle-based buff, not a projectile-spawning skill like Q/E.
    """

    def __init__(self, owner):
        super().__init__(owner, cooldown_time=0.1)
        self.buff_active_time = 0  # When buff was activated
        
    def execute(self, world, factory, renderer):
        """
        Activate the W buff on the owner.
        
        Sets flags on the player:
        - w_buff_active: Boolean flag indicating buff is active
        - w_buff_timer: Activation timestamp
        - w_attack_toggle: Track which shot type (poison vs. plant)
        """
        print("Casting W: Toxin Enhancement activated!")
        
        # Set buff flags on owner
        if not hasattr(self.owner, 'w_buff_active'):
            self.owner.w_buff_active = False
        if not hasattr(self.owner, 'w_buff_timer'):
            self.owner.w_buff_timer = 0
        if not hasattr(self.owner, 'w_attack_toggle'):
            self.owner.w_attack_toggle = False  # False = poison, True = plant
        if not hasattr(self.owner, 'w_poison_applied'):
            self.owner.w_poison_applied = {}  # Track poison targets

        # Activate buff
        self.owner.w_buff_active = True
        self.owner.w_buff_timer = time.time()
        self.owner.w_attack_toggle = False  # Start with poison
        
        # Optional: Play sound effect (if sound_manager available)
        if hasattr(self.owner, 'sound_manager') and self.owner.sound_manager:
            try:
                self.owner.sound_manager.play_sound("skill_w")
            except:
                pass  # Sound not available
        
        return self  # Return self to indicate skill was cast

    def update_buff(self, dt):
        """
        Called from Player update() to manage buff duration.
        Deactivates buff after SKILL_W_BUFF_DURATION expires.
        
        Args:
            dt: Delta time since last frame
        """
        if not self.owner.w_buff_active:
            return
        
        elapsed = time.time() - self.owner.w_buff_timer
        
        if elapsed >= SKILL_W_BUFF_DURATION:
            self.owner.w_buff_active = False
            self.owner.w_attack_toggle = False
            self.owner.w_poison_applied.clear()
            print(f"W Buff expired! (Duration: {SKILL_W_BUFF_DURATION}s)")
