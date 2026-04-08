"""
Player 2 Class - Enhanced character with Toxin Enhancement W skill
Inherits from Player and overrides W skill to be a buff that modifies normal attacks
"""

import sys
import os
import sdl2
import sdl2.ext
import time

# Add root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)  # .../A3_Yasuo
if root_dir not in sys.path:
    sys.path.append(root_dir)

from entities.player import Player
from entities.player_2_projectile import PoisonProjectile, PlantProjectile, HealDustProjectile
from combat.player_2.skill_w import SkillW
from settings import SKILL_W_BUFF_DURATION, SKILL_W_COST


class Player2(Player):
    """
    Player 2 - The new character with enhanced W skill (Toxin Enhancement).
    
    Inherits all base mechanics from Player.
    Overrides W skill to be a buff that modifies normal attacks:
    - Ground attacks alternate between Poison and Plant projectiles
    - Air attacks spawn healing dust for allies
    - Buff lasts 5 seconds with toggle tracking
    """
    
    def __init__(self, world, factory, x, y, sound_manager=None, renderer_ptr=None):
        """
        Initialize Player2.
        
        Args:
            world: SDL2 entity world
            factory: Sprite factory
            x, y: Starting position
            sound_manager: Sound manager instance
            renderer_ptr: SDL2 renderer pointer
        """
        super().__init__(world, factory, x, y, sound_manager, renderer_ptr)
        
        # W Skill buff state management
        self.w_buff_active = False
        self.w_buff_timer = 0  # Timestamp when buff was activated
        self.w_attack_toggle = False  # False = Poison, True = Plant
        
        # Create W skill instance (replaces parent's SkillW)
        self.skill_w = SkillW(self)
        
        # Poison tracking (optional DoT management)
        self.w_poison_applied = {}  # target_id -> timestamp of last poison application
    
    def start_w(self, direction=0):
        """
        Override: Activate Toxin Enhancement buff instead of spawning a wall.
        
        Args:
            direction: Direction input (used for facing)
        """
        # Check cooldown and stamina (same as parent)
        if self.stamina < SKILL_W_COST or not self.cooldowns.is_ready("skill_w"):
            return
        
        # Only cast from valid states
        if self.state not in ['idle', 'jumping']:
            return
        
        # Spend stamina and set cooldown
        self.stamina -= SKILL_W_COST
        cd = self.get_skill_cooldown('w')
        self.cooldowns.start_cooldown("skill_w", cd)
        
        # Update facing direction
        if direction:
            self.facing_right = (direction > 0)
        
        # Set state to casting animation
        self.state = 'casting_w'
        self.frame_index = 0
        
        # Play sound
        if self.sound_manager:
            try:
                self.sound_manager.play_sound("player_w1")
            except:
                pass
    
    def spawn_w_buff(self):
        """
        Called when W casting animation completes.
        Activates the Toxin Enhancement buff.
        """
        # Execute the skill (activates buff)
        self.skill_w.execute(None, None, None)  # No projectile spawning
        
        print(f"Player2: Toxin Enhancement activated for {SKILL_W_BUFF_DURATION}s!")
    
    def update(self, dt, world, factory, renderer, active_list_q, active_list_w, 
               game_map=None, boxes=None):
        """
        Override: Call parent update AND manage W buff duration.
        
        Args:
            dt: Delta time
            world: Entity world
            factory: Sprite factory
            renderer: Renderer
            active_list_q: List for Q skill effects
            active_list_w: List for W skill effects
            game_map: Game map for collision
            boxes: Obstacle boxes
        """
        # Call parent update (handles movement, animation, conditions, etc.)
        super().update(dt, world, factory, renderer, active_list_q, active_list_w, 
                      game_map, boxes)
        
        # Manage W buff duration
        if self.w_buff_active:
            self.skill_w.update_buff(dt)
            
            # Check if buff expired
            if not self.w_buff_active:
                self.w_attack_toggle = False  # Reset toggle on expiration
                self.w_poison_applied.clear()  # Clear poison tracking
    
    def attack(self):
        """
        Override: Modified normal attack that respects W buff state.
        
        If W buff is active, this spawns special projectiles.
        Otherwise, uses parent's normal attack.
        """
        # Only attack from valid states
        if self.state not in ['idle', 'run', 'walk'] or self.is_blocking:
            return
        
        # Check attack cooldown
        if not self.cooldowns.is_ready("attack"):
            return
        
        # Set state and cooldown
        self.state = 'attacking'
        self.frame_index = 0
        cd = self.get_skill_cooldown('a')
        self.cooldowns.start_cooldown("attack", cd)
        
        # If W buff is active, we'll spawn special projectiles
        # This will be handled in the game loop when animation completes
        # by checking self.w_buff_active in a new spawn_attack_projectile() method
    
    def spawn_attack_projectile(self, renderer, projectile_manager, network_ctx=None):
        """
        Called from game loop when attack animation completes.
        Spawns appropriate projectile based on W buff state.
        
        Args:
            renderer: SDL2 renderer
            projectile_manager: Projectile manager to add projectiles
            network_ctx: Network context tuple (is_multi, is_host, game_client)
        """
        # Projectile spawn position (slightly forward of character)
        direction = 1 if self.facing_right else -1
        proj_x = self.sprite.x + (50 * direction)
        proj_y = self.sprite.y + 20
        
        # If W buff is active, spawn special projectiles
        if self.w_buff_active:
            # Air attack (jumping) → Heal Dust
            if self.velocity_y != 0:
                projectile = HealDustProjectile(proj_x, proj_y, direction, self, renderer)
                projectile_manager.add_projectile(projectile)
                
                # Network sync
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        try:
                            game_client.send_skill_event(
                                'attack_w_heal',
                                direction,
                                proj_x,
                                proj_y
                            )
                        except:
                            pass
                
                print("Player2: Heal Dust spawned from air attack")
            
            # Ground attack → Alternate Poison/Plant
            else:
                if not self.w_attack_toggle:  # False = Poison
                    projectile = PoisonProjectile(
                        proj_x, proj_y, direction, self, renderer,
                        damage_multiplier=self.damage_multiplier
                    )
                    action = 'attack_w_poison'
                    print("Player2: Poison projectile spawned")
                
                else:  # True = Plant
                    projectile = PlantProjectile(proj_x, proj_y, direction, self, renderer)
                    action = 'attack_w_plant'
                    print("Player2: Plant projectile spawned")
                
                projectile_manager.add_projectile(projectile)
                
                # Toggle for next shot
                self.w_attack_toggle = not self.w_attack_toggle
                
                # Network sync
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        try:
                            game_client.send_skill_event(action, direction, proj_x, proj_y)
                        except:
                            pass
        
        else:
            # No W buff → Use normal attack (create simple damage hitbox)
            # For now, we'll just log that normal attack occurred
            print("Player2: Normal attack (no W buff active)")
            
            # Optional: Call parent attack logic or spawn normal projectile
            # This would need additional implementation based on how
            # normal attacks are handled in the base Player class
    
    def apply_poison_damage(self, target, damage, tick_rate, duration):
        """
        Optional: Apply poison DoT effect to target.
        
        Called by poison projectile hit logic.
        
        Args:
            target: Enemy/Boss to poison
            damage: Damage per tick
            tick_rate: Seconds between damage ticks
            duration: Total poison duration
        """
        # Track poison application per target
        target_id = getattr(target, 'net_id', id(target))
        current_time = time.time()
        
        # Debounce: only apply poison once per target
        if target_id not in self.w_poison_applied:
            self.w_poison_applied[target_id] = current_time
            
            # Apply poison status if target supports it
            if hasattr(target, 'apply_poison'):
                target.apply_poison(duration, tick_rate, damage)
            
            # Schedule cleanup
            def cleanup_poison(tid):
                if tid in self.w_poison_applied:
                    del self.w_poison_applied[tid]
            
            # Note: Cleanup happens when poison animation finishes on target
    
    def on_hit_enemy(self, damage):
        """
        Override: Grant stamina reward on hit (same as parent).
        
        Called when player hits an enemy (for lifesteal, stamina gain).
        
        Args:
            damage: Damage dealt
        """
        super().on_hit_enemy(damage)
    
    def die(self):
        """Override: Die and clean up buff state."""
        self.w_buff_active = False
        self.w_poison_applied.clear()
        super().die()
