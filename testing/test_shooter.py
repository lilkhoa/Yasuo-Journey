"""
Shooter NPC Visual Testing with Projectiles
Interactive testing for Shooter NPC with movement, attacks, animations, and projectile shooting.
"""
import sys
import os
import sdl2
import sdl2.ext
try:
    from sdl2 import sdlimage
except ImportError:
    sdlimage = None

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from entities.npc import Shooter, NPCState, Direction
from entities.projectile import ProjectileManager


# Window constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60


class ShooterTest:
    """Interactive Shooter NPC testing application with projectiles."""
    
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
            print("Warning: SDL2_image not available, image loading may fail")
        
        # Create window
        self.window = sdl2.SDL_CreateWindow(
            b"Shooter NPC Testing - Movement, Combat & Projectiles",
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
        self.clock = sdl2.SDL_GetTicks()
        
        # Initialize projectile manager
        self.projectile_manager = ProjectileManager(self.renderer)
        
        # Spawn test Shooter with projectile manager integration
        self.shooter = Shooter(400, 300, self.sprite_factory, None, self.renderer, self.projectile_manager)
        self.shooter.patrol_left_bound = 200
        self.shooter.patrol_right_bound = 900
        self.shooter.start_patrol()  # Enable patrol mode with random idle stops
        
        # Test mode
        self.test_mode = "patrol"  # patrol, manual, combat
        self.auto_shoot = False  # Auto-shoot projectiles in combat mode
        
        # Create a dummy target for projectile testing
        self.target = Shooter(900, 300, self.sprite_factory, None, self.renderer, self.projectile_manager)
        self.target.velocity_x = 0  # Make target stationary
        self.target.state = NPCState.IDLE
        
        # Stats tracking
        self.projectiles_fired = 0
        self.hits_landed = 0
        
        self._print_instructions()
    
    def _print_instructions(self):
        """Print control instructions."""
        print("\n" + "="*70)
        print("Shooter NPC Testing - Interactive Demo with Projectiles")
        print("="*70)
        print("\nGLOBAL CONTROLS:")
        print("  ESC           - Exit")
        print("  1             - Patrol Mode (auto movement)")
        print("  2             - Manual Control Mode")
        print("  3             - Combat Test Mode (with target)")
        print("  R             - Reset Shooter position")
        print("  SPACE         - Toggle Auto-Shoot (in combat mode)")
        print("\nMANUAL CONTROL (Mode 2):")
        print("  LEFT ARROW    - Move left")
        print("  RIGHT ARROW   - Move right")
        print("  UP ARROW      - Stop movement")
        print("\nCOMBAT TESTING (Mode 3):")
        print("  Q             - Attack 1 (auto-fires projectile)")
        print("  W             - Attack 2 (auto-fires projectile)")
        print("  E             - Manual fire projectile (no animation)")
        print("\nSTATE CHANGES:")
        print("  O             - Set to Walk state")
        print("  P             - Set to Run state")
        print("  I             - Set to Idle state")
        print("\nDAMAGE TESTING:")
        print("  T             - Damage Shooter (-20 HP)")
        print("  Y             - Heal Shooter (+20 HP)")
        print("  U             - Kill Shooter (0 HP)")
        print("  H             - Heal to full health")
        print("\nTARGET TESTING:")
        print("  G             - Damage Target (-20 HP)")
        print("  J             - Reset Target health")
        print("="*70)
        self._update_status()
    
    def _update_status(self):
        """Update and print current status."""
        print(f"\n{'='*70}")
        print(f"Mode: {self.test_mode.upper()}")
        print(f"Shooter Position: ({int(self.shooter.x)}, {int(self.shooter.y)})")
        print(f"Shooter Health: {self.shooter.health}/{self.shooter.max_health}")
        print(f"Shooter State: {self.shooter.state.value}")
        print(f"Shooter Direction: {'RIGHT' if self.shooter.direction == Direction.RIGHT else 'LEFT'}")
        print(f"Active Projectiles: {len(self.projectile_manager.projectiles)}")
        print(f"Projectiles Fired: {self.projectiles_fired}")
        print(f"Hits Landed: {self.hits_landed}")
        print(f"Auto-Shoot: {'ON' if self.auto_shoot else 'OFF'}")
        if self.test_mode == "combat":
            print(f"Target Health: {self.target.health}/{self.target.max_health}")
        print(f"{'='*70}\n")
    
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
                
                # Mode switching
                elif key == sdl2.SDLK_1:
                    self.test_mode = "patrol"
                    self.shooter.start_patrol()
                    print("\n[MODE] Switched to PATROL mode")
                    self._update_status()
                
                elif key == sdl2.SDLK_2:
                    self.test_mode = "manual"
                    self.shooter.stop_patrol()
                    self.shooter.velocity_x = 0
                    print("\n[MODE] Switched to MANUAL CONTROL mode")
                    self._update_status()
                
                elif key == sdl2.SDLK_3:
                    self.test_mode = "combat"
                    self.shooter.stop_patrol()
                    self.shooter.velocity_x = 0
                    self.shooter.x = 400
                    self.target.x = 900
                    self.target.health = self.target.max_health
                    print("\n[MODE] Switched to COMBAT TEST mode")
                    self._update_status()
                
                elif key == sdl2.SDLK_r:
                    self.shooter.x = 400
                    self.shooter.y = 300
                    self.shooter.velocity_x = 0
                    self.shooter.state = NPCState.IDLE
                    print("\n[RESET] Shooter position reset")
                    self._update_status()
                
                elif key == sdl2.SDLK_SPACE:
                    self.auto_shoot = not self.auto_shoot
                    print(f"\n[AUTO-SHOOT] {'Enabled' if self.auto_shoot else 'Disabled'}")
                    self._update_status()
                
                # Manual control
                elif key == sdl2.SDLK_LEFT and self.test_mode == "manual":
                    self.shooter.move_left()
                    print("[CONTROL] Moving left")
                
                elif key == sdl2.SDLK_RIGHT and self.test_mode == "manual":
                    self.shooter.move_right()
                    print("[CONTROL] Moving right")
                
                elif key == sdl2.SDLK_UP and self.test_mode == "manual":
                    self.shooter.stop()
                    self.shooter.state = NPCState.IDLE
                    print("[CONTROL] Stopped")
                
                # Combat testing
                elif key == sdl2.SDLK_q:
                    self.shooter.attack(1)
                    print("[COMBAT] Attack 1 (projectile will auto-fire)")
                    self._update_status()
                
                elif key == sdl2.SDLK_w:
                    self.shooter.attack(2)
                    print("[COMBAT] Attack 2 (projectile will auto-fire)")
                    self._update_status()
                
                elif key == sdl2.SDLK_e:
                    self._fire_projectile(1)
                    print("[COMBAT] Manual projectile fired (no animation)")
                    self._update_status()
                
                # State changes
                elif key == sdl2.SDLK_o:
                    self.shooter.state = NPCState.WALK
                    print("[STATE] Changed to WALK")
                
                elif key == sdl2.SDLK_p:
                    self.shooter.state = NPCState.RUN
                    print("[STATE] Changed to RUN")
                
                elif key == sdl2.SDLK_i:
                    self.shooter.state = NPCState.IDLE
                    print("[STATE] Changed to IDLE")
                
                # Damage testing
                elif key == sdl2.SDLK_t:
                    self.shooter.take_damage(20)
                    print(f"[DAMAGE] Shooter took 20 damage. Health: {self.shooter.health}/{self.shooter.max_health}")
                    self._update_status()
                
                elif key == sdl2.SDLK_y:
                    self.shooter.health = min(self.shooter.health + 20, self.shooter.max_health)
                    print(f"[HEAL] Shooter healed 20 HP. Health: {self.shooter.health}/{self.shooter.max_health}")
                    self._update_status()
                
                elif key == sdl2.SDLK_u:
                    self.shooter.take_damage(self.shooter.health)
                    print("[KILL] Shooter killed")
                    self._update_status()
                
                elif key == sdl2.SDLK_h:
                    self.shooter.health = self.shooter.max_health
                    if self.shooter.state == NPCState.DEAD:
                        self.shooter.state = NPCState.IDLE
                    print(f"[HEAL] Shooter fully healed. Health: {self.shooter.health}/{self.shooter.max_health}")
                    self._update_status()
                
                # Target testing
                elif key == sdl2.SDLK_g and self.test_mode == "combat":
                    self.target.take_damage(20)
                    print(f"[TARGET] Target damaged. Health: {self.target.health}/{self.target.max_health}")
                    self._update_status()
                
                elif key == sdl2.SDLK_j and self.test_mode == "combat":
                    self.target.health = self.target.max_health
                    if self.target.state == NPCState.DEAD:
                        self.target.state = NPCState.IDLE
                    print(f"[TARGET] Target reset. Health: {self.target.health}/{self.target.max_health}")
                    self._update_status()
    
    def _fire_projectile(self, attack_type):
        """
        Fire a projectile from the Shooter.
        
        Args:
            attack_type: 1 for Attack_1, 2 for Attack_2
        """
        # Calculate projectile spawn position (in front of Shooter)
        offset_x = 45 if self.shooter.direction == Direction.RIGHT else -45
        proj_x = self.shooter.x + offset_x
        proj_y = self.shooter.y + 15
        
        direction = 1 if self.shooter.direction == Direction.RIGHT else -1
        
        self.projectile_manager.spawn_shooter_projectile(
            proj_x, proj_y, direction, self.shooter, attack_type
        )
        self.projectiles_fired += 1
    
    def update(self):
        """Update game state."""
        # Update Shooter based on mode (projectiles auto-fire during attacks)
        if self.test_mode == "patrol":
            self.shooter.update()
        elif self.test_mode == "manual":
            self.shooter.update()
        elif self.test_mode == "combat":
            self.shooter.update()
            self.target.update()
            
            # Auto-shoot in combat mode (projectiles fire automatically with attack)
            if self.auto_shoot and self.shooter.attack_cooldown == 0 and not self.shooter.is_attacking:
                # Randomly choose between Attack 1 and Attack 2
                import random
                attack_type = random.choice([1, 2])
                self.shooter.attack(attack_type)
                # No need to manually fire projectile - it fires automatically!
        
        # Update projectiles
        self.projectile_manager.update_all()
        
        # Check projectile collisions with target
        if self.test_mode == "combat":
            hits = self.projectile_manager.check_collisions([self.target])
            for projectile, target in hits:
                target.take_damage(projectile.damage)
                self.hits_landed += 1
                print(f"[HIT] Projectile hit target! Damage: {projectile.damage}, Target Health: {target.health}")
    
    def render(self):
        """Render everything."""
        # Clear screen with dark background
        sdl2.SDL_SetRenderDrawColor(self.renderer, 20, 20, 30, 255)
        sdl2.SDL_RenderClear(self.renderer)
        
        # Draw ground line
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 100, 100, 255)
        ground_y = 350
        sdl2.SDL_RenderDrawLine(self.renderer, 0, ground_y, WINDOW_WIDTH, ground_y)
        
        # Draw patrol bounds in patrol mode
        if self.test_mode == "patrol":
            sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 150, 50, 255)
            sdl2.SDL_RenderDrawLine(self.renderer, int(self.shooter.patrol_left_bound), 0, 
                                   int(self.shooter.patrol_left_bound), WINDOW_HEIGHT)
            sdl2.SDL_RenderDrawLine(self.renderer, int(self.shooter.patrol_right_bound), 0, 
                                   int(self.shooter.patrol_right_bound), WINDOW_HEIGHT)
        
        # Render target in combat mode
        if self.test_mode == "combat":
            self.target.render()
            
            # Draw target health bar
            self._draw_health_bar(self.target)
        
        # Render Shooter
        self.shooter.render()
        
        # Draw Shooter health bar
        self._draw_health_bar(self.shooter)
        
        # Render projectiles
        self.projectile_manager.render_all()
        
        # Draw UI info
        self._draw_ui()
        
        # Present
        sdl2.SDL_RenderPresent(self.renderer)
    
    def _draw_health_bar(self, entity):
        """Draw health bar above entity."""
        bar_width = 60
        bar_height = 6
        bar_x = int(entity.x + (entity.width - bar_width) / 2)
        bar_y = int(entity.y - 15)
        
        # Background (red)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 150, 0, 0, 255)
        bg_rect = sdl2.SDL_Rect(bar_x, bar_y, bar_width, bar_height)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Foreground (green)
        health_percent = entity.health / entity.max_health
        fg_width = int(bar_width * health_percent)
        if fg_width > 0:
            sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 200, 0, 255)
            fg_rect = sdl2.SDL_Rect(bar_x, bar_y, fg_width, bar_height)
            sdl2.SDL_RenderFillRect(self.renderer, fg_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
    
    def _draw_ui(self):
        """Draw UI information (simple text representation with rectangles)."""
        # Draw mode indicator
        mode_color = {
            "patrol": (50, 200, 50, 255),
            "manual": (50, 50, 200, 255),
            "combat": (200, 50, 50, 255)
        }
        
        color = mode_color.get(self.test_mode, (200, 200, 200, 255))
        sdl2.SDL_SetRenderDrawColor(self.renderer, *color)
        
        # Mode indicator box
        mode_rect = sdl2.SDL_Rect(10, 10, 120, 30)
        sdl2.SDL_RenderFillRect(self.renderer, mode_rect)
        
        # Stats display (simple boxes)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 50, 50, 200)
        stats_rect = sdl2.SDL_Rect(10, 50, 200, 80)
        sdl2.SDL_RenderFillRect(self.renderer, stats_rect)
    
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
        self.shooter.cleanup()
        self.target.cleanup()
        
        # Clean up projectiles
        self.projectile_manager.cleanup()
        
        # Clean up SDL2
        sdl2.SDL_DestroyRenderer(self.renderer)
        sdl2.SDL_DestroyWindow(self.window)
        
        if sdlimage:
            sdlimage.IMG_Quit()
        
        sdl2.SDL_Quit()
        
        print("[CLEANUP] Done!")
        print(f"\nFinal Stats:")
        print(f"  Projectiles Fired: {self.projectiles_fired}")
        print(f"  Hits Landed: {self.hits_landed}")
        print(f"  Hit Rate: {(self.hits_landed/self.projectiles_fired*100 if self.projectiles_fired > 0 else 0):.1f}%")


def main():
    """Entry point."""
    test = ShooterTest()
    test.run()


if __name__ == "__main__":
    main()
