import time
from combat.refactored_skill import BaseSkill
from settings import SKILL_W_BUFF_DURATION, SKILL_W_COST


class SkillW(BaseSkill):
    """
    Toxin Enhancement Buff Skill.
    
    Activates an instant buff that modifies the character's normal attacks:
    - Duration: SKILL_W_BUFF_DURATION seconds (default 5.0s)
    - Normal attacks alternate: Poison (damage) → Plant (root) → Poison → ...
    - NO casting animation - buff activates instantly
    
    The buff is tracked via owner.w_buff_active flag and owner.w_buff_timer.
    Projectile spawning logic is in LeafRanger.spawn_attack_projectile().
    """
    
    def __init__(self, owner):
        """
        Initialize W skill (Toxin Enhancement).
        
        Args:
            owner: LeafRanger character instance
        """
        super().__init__(
            owner=owner,
            name="Toxin Enhancement",
            base_cooldown=0.1,  # Cooldown managed by owner.cooldowns
            stamina_cost=SKILL_W_COST
        )
        
        # Buff state (managed by this skill)
        self.buff_duration = SKILL_W_BUFF_DURATION
        self.buff_start_time = 0
    
    def execute(self, world=None, factory=None, renderer=None, **kwargs):
        """
        Activate the Toxin Enhancement buff instantly.
        
        This is called when W is pressed (via LeafRanger.spawn_w_buff()).
        Sets owner.w_buff_active = True and starts the timer.
        NO casting animation plays - buff activates immediately.
        
        Args:
            world: Unused (for signature compatibility)
            factory: Unused (for signature compatibility)
            renderer: Unused (for signature compatibility)
            **kwargs: Additional parameters (unused)
            
        Returns:
            None (buff skill, no projectile/object spawned)
        """
        # Activate buff
        self.owner.w_buff_active = True
        self.owner.w_buff_timer = time.time()
        self.buff_start_time = time.time()
        
        # Reset toggle state (start with Poison on first attack)
        self.owner.w_attack_toggle = False
        
        print(f"[SkillW] Toxin Enhancement activated! Duration: {self.buff_duration}s")
        
        # Return None (buff doesn't spawn a visible object)
        return None
    
    def update_buff(self, dt):
        """
        Update buff duration and deactivate when expired.
        
        Called by LeafRanger.update() every frame while buff is active.
        
        Args:
            dt: Delta time (seconds elapsed since last frame)
        """
        if not self.owner.w_buff_active:
            return
        
        # Check if buff has expired
        elapsed = time.time() - self.buff_start_time
        
        if elapsed >= self.buff_duration:
            # Buff expired - deactivate
            self.owner.w_buff_active = False
            self.owner.w_buff_timer = 0
            self.owner.w_attack_toggle = False
            
            print(f"[SkillW] Toxin Enhancement expired after {elapsed:.2f}s")
    
    def get_remaining_time(self):
        """
        Get remaining buff duration.
        
        Returns:
            float: Seconds remaining, or 0 if buff inactive
        """
        if not self.owner.w_buff_active:
            return 0.0
        
        elapsed = time.time() - self.buff_start_time
        remaining = max(0.0, self.buff_duration - elapsed)
        return remaining
    
    def is_active(self):
        """
        Check if buff is currently active.
        
        Returns:
            bool: True if buff is active
        """
        return self.owner.w_buff_active


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS (Optional - for network sync if needed)
# ─────────────────────────────────────────────────────────────────────────────

def sync_buff_activation(owner, network_ctx=None):
    """
    Send network event when W buff is activated (optional).
    
    Args:
        owner: LeafRanger instance
        network_ctx: Network context tuple (is_multi, is_host, game_client)
    """
    if not network_ctx:
        return
    
    is_multi, is_host, game_client = network_ctx
    
    if is_multi and game_client and game_client.is_connected():
        try:
            # Send buff activation event for visual sync
            game_client.send_skill_event(
                skill_type='w_buff_start',
                direction=1 if owner.facing_right else -1,
                x=owner.x,
                y=owner.y
            )
        except Exception as e:
            print(f"[SkillW] Network sync error: {e}")


def sync_buff_deactivation(owner, network_ctx=None):
    """
    Send network event when W buff expires (optional).
    
    Args:
        owner: LeafRanger instance
        network_ctx: Network context tuple (is_multi, is_host, game_client)
    """
    if not network_ctx:
        return
    
    is_multi, is_host, game_client = network_ctx
    
    if is_multi and game_client and game_client.is_connected():
        try:
            # Send buff expiration event for visual sync
            game_client.send_skill_event(
                skill_type='w_buff_end',
                direction=1 if owner.facing_right else -1,
                x=owner.x,
                y=owner.y
            )
        except Exception as e:
            print(f"[SkillW] Network sync error: {e}")
