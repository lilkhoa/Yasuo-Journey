"""
Boss Visual Testing
Interactive testing for Boss with all states, attacks, and special skills using PySDL2.
"""
import sys
import os
import sdl2
import sdl2.ext
import math
try:
    from sdl2 import sdlimage
except ImportError:
    sdlimage = None

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from entities.boss import Boss, BossState, SkillType
from entities.projectile import ProjectileManager


# Window constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60


class Player:
    """Simple player representation as a controllable rectangle."""
    
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 100
        self.speed = 5
        self.health = 200
        self.max_health = 200
        
        # Movement state
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
    
    def update(self):
        """Update player position based on input."""
        if self.move_left:
            self.x -= self.speed
        if self.move_right:
            self.x += self.speed
        if self.move_up:
            self.y -= self.speed
        if self.move_down:
            self.y += self.speed
        
        # Keep player in bounds
        self.x = max(0, min(WINDOW_WIDTH - self.width, self.x))
        self.y = max(0, min(WINDOW_HEIGHT - self.height, self.y))
    
    def render(self, renderer):
        """Render player as a blue rectangle."""
        sdl2.SDL_SetRenderDrawColor(renderer, 50, 100, 255, 255)
        rect = sdl2.SDL_Rect(int(self.x), int(self.y), self.width, self.height)
        sdl2.SDL_RenderFillRect(renderer, rect)
        
        # Draw border
        sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(renderer, rect)
    
    def take_damage(self, amount):
        """Take damage from boss."""
        self.health = max(0, self.health - amount)
        print(f"[Player] Took {amount} damage! Health: {self.health}/{self.max_health}")
    
    def get_bounds(self):
        """Get bounding box for collision detection."""
        return (self.x, self.y, self.width, self.height)


class BossTest:
    """Boss testing application."""
    
    def __init__(self):
        """Initialize testing application."""
        # Initialize SDL2
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
            print(f"SDL2 initialization failed: {sdl2.SDL_GetError()}")
            sys.exit(1)
        
        # Initialize SDL2_image
        if sdlimage:
            img_flags = sdlimage.IMG_INIT_PNG
            if not sdlimage.IMG_Init(img_flags):
                print(f"SDL2_image initialization failed: {sdlimage.IMG_GetError()}")
        else:
            print("Warning: SDL2_image not available")
        
        # Create window
        self.window = sdl2.SDL_CreateWindow(
            b"Boss Test - Use Arrow Keys to Move Player",
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            sdl2.SDL_WINDOW_SHOWN
        )
        
        if not self.window:
            print(f"Window creation failed: {sdl2.SDL_GetError()}")
            sys.exit(1)
        
        # Create renderer
        self.renderer = sdl2.SDL_CreateRenderer(
            self.window,
            -1,
            sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
        )
        
        if not self.renderer:
            print(f"Renderer creation failed: {sdl2.SDL_GetError()}")
            sys.exit(1)
        
        # Create sprite factory
        self.sprite_factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=self.renderer)
        
        # Game state
        self.running = True
        self.paused = False
        self.manual_control = False
        
        # Initialize projectile manager
        self.projectile_manager = ProjectileManager(self.renderer)
        
        # Create player
        self.player = Player(640, 500)
        
        # Spawn Boss
        boss_x = 1000
        boss_y = 300
        self.boss = Boss(boss_x, boss_y, self.sprite_factory, None, self.renderer, self.projectile_manager)
        self.boss.set_player(self.player)
        
        # Test control flags
        self.show_debug = True
        self.ai_enabled = True
        
        self._print_instructions()
    
    def _print_instructions(self):
        """Print control instructions."""
        print("\n" + "="*80)
        print("Boss Visual Testing - Interactive Demo")
        print("="*80)
        print("\nCONTROLS:")
        print("  Arrow Keys       - Move player (blue rectangle)")
        print("  SPACE            - Pause/Resume")
        print("  D                - Toggle debug info")
        print("  A                - Toggle AI (enable/disable boss AI)")
        print("  M                - Toggle manual control mode")
        print("  ESC              - Exit")
        print("\nMANUAL STATE TESTING (when AI disabled):")
        print("  1 - IDLE state")
        print("  2 - IDLE_BLINK state")
        print("  3 - WALKING state")
        print("  4 - ATTACKING state (melee)")
        print("  5 - ATTACKING state (ranged)")
        print("  6 - CASTING state")
        print("  7 - HURT state")
        print("\nSKILL TESTING (when AI disabled):")
        print("  Q - Trigger Circular Shooting skill")
        print("  W - Trigger Meteor skill")
        print("  E - Trigger Kamehameha skill")
        print("  R - Trigger Summon Minions skill")
        print("\nCOMBAT TESTING:")
        print("  T - Damage boss (-100 HP)")
        print("  Y - Damage boss to 75% HP threshold")
        print("  U - Damage boss to 50% HP threshold")
        print("  I - Damage boss to 25% HP threshold")
        print("  H - Heal boss (+200 HP)")
        print("  K - Kill boss (0 HP)")
        print("\nINFO:")
        print("  - Boss automatically attacks player when AI enabled")
        print("  - Boss uses melee attack when player is close")
        print("  - Boss uses ranged attack when player is far")
        print("  - Boss randomly uses special skills")
        print("  - Meteor skill auto-triggers at HP thresholds (75%, 50%, 25%)")
        print("="*80 + "\n")
    
    def handle_events(self):
        """Process SDL2 events."""
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                
                # Global controls
                if key == sdl2.SDLK_ESCAPE:
                    self.running = False
                elif key == sdl2.SDLK_SPACE:
                    self.paused = not self.paused
                    print(f"[Test] {'PAUSED' if self.paused else 'RESUMED'}")
                elif key == sdl2.SDLK_d:
                    self.show_debug = not self.show_debug
                    print(f"[Test] Debug info: {'ON' if self.show_debug else 'OFF'}")
                elif key == sdl2.SDLK_a:
                    self.ai_enabled = not self.ai_enabled
                    print(f"[Test] AI: {'ENABLED' if self.ai_enabled else 'DISABLED'}")
                elif key == sdl2.SDLK_m:
                    self.manual_control = not self.manual_control
                    print(f"[Test] Manual control: {'ON' if self.manual_control else 'OFF'}")
                
                # Player movement
                elif key == sdl2.SDLK_LEFT:
                    self.player.move_left = True
                elif key == sdl2.SDLK_RIGHT:
                    self.player.move_right = True
                elif key == sdl2.SDLK_UP:
                    self.player.move_up = True
                elif key == sdl2.SDLK_DOWN:
                    self.player.move_down = True
                
                # Manual state testing (when AI disabled)
                elif key == sdl2.SDLK_1 and not self.ai_enabled:
                    self._set_boss_state(BossState.IDLE)
                elif key == sdl2.SDLK_2 and not self.ai_enabled:
                    self._set_boss_state(BossState.IDLE_BLINK)
                elif key == sdl2.SDLK_3 and not self.ai_enabled:
                    self._set_boss_state(BossState.WALKING)
                elif key == sdl2.SDLK_4 and not self.ai_enabled:
                    self._trigger_melee_attack()
                elif key == sdl2.SDLK_5 and not self.ai_enabled:
                    self._trigger_ranged_attack()
                elif key == sdl2.SDLK_6 and not self.ai_enabled:
                    self._set_boss_state(BossState.CASTING)
                elif key == sdl2.SDLK_7 and not self.ai_enabled:
                    self._set_boss_state(BossState.HURT)
                
                # Skill testing (when AI disabled)
                elif key == sdl2.SDLK_q and not self.ai_enabled:
                    self.boss._start_circular_shooting_skill()
                    print("[Test] Triggered Circular Shooting skill")
                elif key == sdl2.SDLK_w and not self.ai_enabled:
                    self.boss._start_meteor_skill()
                    print("[Test] Triggered Meteor skill")
                elif key == sdl2.SDLK_e and not self.ai_enabled:
                    self.boss._start_kamehameha_skill()
                    print("[Test] Triggered Kamehameha skill")
                elif key == sdl2.SDLK_r and not self.ai_enabled:
                    self.boss._start_summon_minions_skill()
                    print("[Test] Triggered Summon Minions skill")
                
                # Combat testing
                elif key == sdl2.SDLK_t:
                    self.boss.take_damage(100)
                    print(f"[Test] Damaged boss -100 HP")
                elif key == sdl2.SDLK_y:
                    target_hp = int(self.boss.max_health * 0.75)
                    if self.boss.health > target_hp:
                        damage = self.boss.health - target_hp
                        self.boss.take_damage(damage)
                        print(f"[Test] Damaged boss to 75% HP threshold")
                elif key == sdl2.SDLK_u:
                    target_hp = int(self.boss.max_health * 0.50)
                    if self.boss.health > target_hp:
                        damage = self.boss.health - target_hp
                        self.boss.take_damage(damage)
                        print(f"[Test] Damaged boss to 50% HP threshold")
                elif key == sdl2.SDLK_i:
                    target_hp = int(self.boss.max_health * 0.25)
                    if self.boss.health > target_hp:
                        damage = self.boss.health - target_hp
                        self.boss.take_damage(damage)
                        print(f"[Test] Damaged boss to 25% HP threshold")
                elif key == sdl2.SDLK_h:
                    self.boss.health = min(self.boss.max_health, self.boss.health + 200)
                    print(f"[Test] Healed boss +200 HP")
                elif key == sdl2.SDLK_k:
                    self.boss.take_damage(self.boss.health)
                    print(f"[Test] Killed boss")
            
            elif event.type == sdl2.SDL_KEYUP:
                key = event.key.keysym.sym
                
                # Player movement
                if key == sdl2.SDLK_LEFT:
                    self.player.move_left = False
                elif key == sdl2.SDLK_RIGHT:
                    self.player.move_right = False
                elif key == sdl2.SDLK_UP:
                    self.player.move_up = False
                elif key == sdl2.SDLK_DOWN:
                    self.player.move_down = False
    
    def _set_boss_state(self, state):
        """Manually set boss state for testing."""
        self.boss.state = state
        self.boss.current_frame = 0
        self.boss.frame_counter = 0
        print(f"[Test] Set boss state to {state.value}")
    
    def _trigger_melee_attack(self):
        """Trigger melee attack manually."""
        self.boss._start_melee_attack()
        print(f"[Test] Triggered melee attack")
    
    def _trigger_ranged_attack(self):
        """Trigger ranged attack manually."""
        self.boss._start_ranged_attack()
        print(f"[Test] Triggered ranged attack")
    
    def update(self):
        """Update game state."""
        if self.paused:
            return
        
        # Update player
        self.player.update()
        
        # Update Boss (with or without AI)
        if self.ai_enabled:
            self.boss.update()
        else:
            # Only update animations when AI disabled
            self.boss._update_animation()
            
            # Still update skill movement if in progress
            if self.boss.is_moving_to_center or self.boss.is_returning_from_center:
                self.boss._update_skill_movement()
            
            # Update skill phases if active
            if self.boss.current_skill is not None:
                self.boss._update_skill()
            
            # Update jumping if active
            if self.boss.is_jumping:
                self.boss._update_jump()
        
        # Update projectiles
        self.projectile_manager.update_all()
        
        # Check projectile collisions with player
        for projectile in self.projectile_manager.projectiles[:]:
            if projectile.check_collision(self.player):
                self.player.take_damage(projectile.damage)
                self.projectile_manager.projectiles.remove(projectile)
    
    def render(self):
        """Render everything."""
        # Clear screen (dark background)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 30, 40, 255)
        sdl2.SDL_RenderClear(self.renderer)
        
        # Draw ground line
        self._draw_ground()
        
        # Draw boss spawn marker
        if self.show_debug:
            self._draw_spawn_marker()
            self._draw_ranges()
        
        # Render player
        self.player.render(self.renderer)
        
        # Render Boss
        self.boss.render()
        
        # Render projectiles
        self.projectile_manager.render_all()
        
        # Draw health bars
        self._draw_health_bar(self.player, "Player")
        self._draw_health_bar(self.boss, "Boss")
        
        # Draw UI info
        if self.show_debug:
            self._draw_debug_ui()
        
        self._draw_status_ui()
        
        # Present
        sdl2.SDL_RenderPresent(self.renderer)
    
    def _draw_ground(self):
        """Draw ground line."""
        ground_y = int(self.boss.ground_y + self.boss.height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 100, 100, 255)
        sdl2.SDL_RenderDrawLine(self.renderer, 0, ground_y, WINDOW_WIDTH, ground_y)
    
    def _draw_spawn_marker(self):
        """Draw boss spawn position marker."""
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 0, 0, 255)
        spawn_x = int(self.boss.spawn_x + self.boss.width // 2)
        spawn_y = int(self.boss.spawn_y + self.boss.height // 2)
        
        # Draw cross marker
        sdl2.SDL_RenderDrawLine(self.renderer, spawn_x - 15, spawn_y, spawn_x + 15, spawn_y)
        sdl2.SDL_RenderDrawLine(self.renderer, spawn_x, spawn_y - 15, spawn_x, spawn_y + 15)
        
        # Draw circle
        for angle in range(0, 360, 10):
            x1 = spawn_x + int(20 * math.cos(math.radians(angle)))
            y1 = spawn_y + int(20 * math.sin(math.radians(angle)))
            x2 = spawn_x + int(20 * math.cos(math.radians(angle + 10)))
            y2 = spawn_y + int(20 * math.sin(math.radians(angle + 10)))
            sdl2.SDL_RenderDrawLine(self.renderer, x1, y1, x2, y2)
    
    def _draw_ranges(self):
        """Draw attack ranges."""
        boss_center_x = int(self.boss.x + self.boss.width // 2)
        boss_center_y = int(self.boss.y + self.boss.height // 2)
        
        # Melee range (red circle)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 0, 0, 100)
        for angle in range(0, 360, 5):
            x1 = boss_center_x + int(self.boss.melee_range * math.cos(math.radians(angle)))
            y1 = boss_center_y + int(self.boss.melee_range * math.sin(math.radians(angle)))
            x2 = boss_center_x + int(self.boss.melee_range * math.cos(math.radians(angle + 5)))
            y2 = boss_center_y + int(self.boss.melee_range * math.sin(math.radians(angle + 5)))
            sdl2.SDL_RenderDrawLine(self.renderer, x1, y1, x2, y2)
        
        # Screen center marker for circular shooting
        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 255, 255, 150)
        sdl2.SDL_RenderDrawLine(self.renderer, center_x - 10, center_y, center_x + 10, center_y)
        sdl2.SDL_RenderDrawLine(self.renderer, center_x, center_y - 10, center_x, center_y + 10)
    
    def _draw_health_bar(self, entity, label):
        """Draw health bar above entity."""
        bar_width = 100
        bar_height = 8
        bar_x = int(entity.x + (entity.width - bar_width) / 2)
        bar_y = int(entity.y - 20)
        
        # Background (dark red)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 0, 0, 255)
        bg_rect = sdl2.SDL_Rect(bar_x, bar_y, bar_width, bar_height)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Foreground (green to red gradient based on health)
        health_percent = entity.health / entity.max_health
        fg_width = int(bar_width * health_percent)
        if fg_width > 0:
            if health_percent > 0.5:
                # Green
                sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 200, 0, 255)
            elif health_percent > 0.25:
                # Yellow
                sdl2.SDL_SetRenderDrawColor(self.renderer, 200, 200, 0, 255)
            else:
                # Red
                sdl2.SDL_SetRenderDrawColor(self.renderer, 200, 0, 0, 255)
            
            fg_rect = sdl2.SDL_Rect(bar_x, bar_y, fg_width, bar_height)
            sdl2.SDL_RenderFillRect(self.renderer, fg_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
    
    def _draw_debug_ui(self):
        """Draw debug information."""
        # Draw debug info background
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 200)
        info_rect = sdl2.SDL_Rect(10, 10, 350, 180)
        sdl2.SDL_RenderFillRect(self.renderer, info_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, info_rect)
        
        # State indicator color box
        state_colors = {
            "Idle": (100, 100, 100),
            "Idle_Blink": (150, 150, 150),
            "Walking": (100, 200, 100),
            "Attacking": (255, 0, 0),
            "Casting_Spells": (255, 100, 255),
            "Hurt": (255, 200, 0),
            "Dying": (150, 0, 0)
        }
        
        color = state_colors.get(self.boss.state.value, (200, 200, 200))
        sdl2.SDL_SetRenderDrawColor(self.renderer, *color, 255)
        state_rect = sdl2.SDL_Rect(20, 20, 330, 30)
        sdl2.SDL_RenderFillRect(self.renderer, state_rect)
    
    def _draw_status_ui(self):
        """Draw status information."""
        # Status panel
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 200)
        status_rect = sdl2.SDL_Rect(WINDOW_WIDTH - 260, 10, 250, 150)
        sdl2.SDL_RenderFillRect(self.renderer, status_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, status_rect)
        
        # Skill indicator
        if self.boss.current_skill is not None:
            skill_colors = {
                "circular_shooting": (0, 200, 255),
                "meteor": (255, 100, 0),
                "kamehameha": (255, 255, 0),
                "summon_minions": (150, 0, 255)
            }
            color = skill_colors.get(self.boss.current_skill.value, (200, 200, 200))
            sdl2.SDL_SetRenderDrawColor(self.renderer, *color, 255)
            skill_rect = sdl2.SDL_Rect(WINDOW_WIDTH - 250, 20, 230, 25)
            sdl2.SDL_RenderFillRect(self.renderer, skill_rect)
    
    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            
            # Cap frame rate
            sdl2.SDL_Delay(1000 // FPS)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        print("\n[CLEANUP] Shutting down...")
        
        # Clean up entities
        self.boss.cleanup()
        
        # Clean up projectiles
        self.projectile_manager.cleanup()
        
        # Clean up SDL2
        sdl2.SDL_DestroyRenderer(self.renderer)
        sdl2.SDL_DestroyWindow(self.window)
        
        if sdlimage:
            sdlimage.IMG_Quit()
        
        sdl2.SDL_Quit()
        
        print("[CLEANUP] Done!")


def main():
    """Entry point."""
    test = BossTest()
    test.run()


if __name__ == "__main__":
    main()
