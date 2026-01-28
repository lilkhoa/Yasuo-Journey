"""
NPC Visual Testing
Interactive testing for Ghost and Shooter NPCs with movement, attacks, and animations using PySDL2.
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

from entities.npc import Ghost, Shooter, Onre, NPCManager, NPCState, Direction


# Window constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60


class NPCTest:
    """Interactive NPC testing application for Ghost and Shooter."""
    
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
            b"NPC Testing - Ghost & Shooter Demo",
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
        
        # Initialize NPC manager
        self.npc_manager = NPCManager(self.sprite_factory, None, self.renderer)
        
        # Spawn test NPCs
        self.test_ghost = self.npc_manager.spawn_ghost(300, 400)
        self.test_ghost.patrol_left_bound = 150
        self.test_ghost.patrol_right_bound = 600
        
        self.test_shooter = self.npc_manager.spawn_shooter(800, 400)
        self.test_shooter.patrol_left_bound = 650
        self.test_shooter.patrol_right_bound = 1100
        
        self.test_onre = self.npc_manager.spawn_onre(500, 400)
        self.test_onre.patrol_left_bound = 350
        self.test_onre.patrol_right_bound = 750
        
        # Test mode
        self.test_mode = "patrol"  # patrol, manual, combat
        self.selected_npc = self.test_ghost
        self.npc_type = "Ghost"  # Ghost, Shooter, or Onre
        
        print("\n" + "="*70)
        print("NPC Testing - Ghost & Shooter Interactive Demo")
        print("="*70)
        print("\nGLOBAL CONTROLS:")
        print("  ESC           - Exit")
        print("  TAB           - Switch selected NPC (Ghost/Shooter/Onre)")
        print("  G             - Spawn new Ghost")
        print("  H             - Spawn new Shooter")
        print("  J             - Spawn new Onre")
        print("  1             - Switch to Patrol Mode (auto)")
        print("  2             - Switch to Manual Control Mode")
        print("  3             - Switch to Combat Test Mode")
        print("\nMANUAL CONTROL (Mode 2):")
        print("  LEFT ARROW    - Move left")
        print("  RIGHT ARROW   - Move right")
        print("  UP ARROW      - Stop")
        print("\nCOMBAT TESTING (Mode 3):")
        print("  Ghost: E (Attack 3), R (Attack 4)")
        print("  Shooter: Q (Attack 1), W (Attack 2)")
        print("  Onre: Z (Attack 1), X (Attack 2), C (Attack 3)")
        print("  T             - Damage NPC (-20 HP)")
        print("  Y             - Heal NPC (+20 HP)")
        print("  U             - Kill NPC (0 HP)")
        print("\nSTATE CHANGES:")
        print("  O             - Change to Walk state")
        print("  P             - Change to Run state")
        print("="*70)
        print(f"\nCurrent Mode: {self.test_mode.upper()}")
        print(f"Selected NPC: {self.npc_type}")
        print(f"Position: ({int(self.selected_npc.x)}, {int(self.selected_npc.y)})")
        print(f"Health: {self.selected_npc.health}/{self.selected_npc.max_health}")
        print("="*70 + "\n")
    
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
                
                elif key == sdl2.SDLK_TAB:
                    # Switch between Ghost, Shooter, and Onre
                    if self.selected_npc == self.test_ghost:
                        self.selected_npc = self.test_shooter
                        self.npc_type = "Shooter"
                    elif self.selected_npc == self.test_shooter:
                        self.selected_npc = self.test_onre
                        self.npc_type = "Onre"
                    else:
                        self.selected_npc = self.test_ghost
                        self.npc_type = "Ghost"
                    print(f"\n→ Switched to {self.npc_type}")
                    print(f"  Position: ({int(self.selected_npc.x)}, {int(self.selected_npc.y)})")
                    print(f"  Health: {self.selected_npc.health}/{self.selected_npc.max_health}")
                
                elif key == sdl2.SDLK_g:
                    # Spawn new ghost
                    import random
                    x = random.randint(100, WINDOW_WIDTH - 200)
                    y = random.randint(300, 450)
                    new_ghost = self.npc_manager.spawn_ghost(x, y)
                    new_ghost.patrol_left_bound = x - 150
                    new_ghost.patrol_right_bound = x + 150
                    print(f"✓ Spawned new Ghost at ({x}, {y})")
                
                elif key == sdl2.SDLK_h:
                    # Spawn new shooter
                    import random
                    x = random.randint(100, WINDOW_WIDTH - 200)
                    y = random.randint(300, 450)
                    new_shooter = self.npc_manager.spawn_shooter(x, y)
                    new_shooter.patrol_left_bound = x - 150
                    new_shooter.patrol_right_bound = x + 150
                    print(f"✓ Spawned new Shooter at ({x}, {y})")
                
                elif key == sdl2.SDLK_j:
                    # Spawn new onre
                    import random
                    x = random.randint(100, WINDOW_WIDTH - 200)
                    y = random.randint(300, 450)
                    new_onre = self.npc_manager.spawn_onre(x, y)
                    new_onre.patrol_left_bound = x - 150
                    new_onre.patrol_right_bound = x + 150
                    print(f"✓ Spawned new Onre at ({x}, {y})")
                
                # Mode switching
                elif key == sdl2.SDLK_1:
                    self.test_mode = "patrol"
                    self.selected_npc.state = NPCState.WALK
                    print(f"\n→ PATROL MODE: {self.npc_type} patrols automatically")
                
                elif key == sdl2.SDLK_2:
                    self.test_mode = "manual"
                    self.selected_npc.stop()
                    print(f"\n→ MANUAL MODE: Use arrow keys to control {self.npc_type}")
                
                elif key == sdl2.SDLK_3:
                    self.test_mode = "combat"
                    self.selected_npc.stop()
                    print(f"\n→ COMBAT MODE: Test attacks and damage for {self.npc_type}")
                
                # Manual controls (Mode 2)
                if self.test_mode == "manual":
                    if key == sdl2.SDLK_LEFT:
                        self.selected_npc.move_left()
                        print(f"← Moving left (pos: {int(self.selected_npc.x)})")
                    
                    elif key == sdl2.SDLK_RIGHT:
                        self.selected_npc.move_right()
                        print(f"→ Moving right (pos: {int(self.selected_npc.x)})")
                    
                    elif key == sdl2.SDLK_UP:
                        self.selected_npc.stop()
                        print("■ Stopped")
                
                # Combat controls (Mode 3)
                if self.test_mode == "combat":
                    # Ghost attacks
                    if isinstance(self.selected_npc, Ghost):
                        if key == sdl2.SDLK_e:
                            self.selected_npc.attack(3)
                            print("⚔ Ghost Attack Type 3 (Energy Cast)!")
                        
                        elif key == sdl2.SDLK_r:
                            self.selected_npc.attack(4)
                            print("⚔ Ghost Attack Type 4 (Energy Cast)!")
                    
                    # Shooter attacks
                    elif isinstance(self.selected_npc, Shooter):
                        if key == sdl2.SDLK_q:
                            self.selected_npc.attack(1)
                            print("⚔ Shooter Attack Type 1!")
                        
                        elif key == sdl2.SDLK_w:
                            self.selected_npc.attack(2)
                            print("⚔ Shooter Attack Type 2!")
                    
                    # Onre attacks
                    elif isinstance(self.selected_npc, Onre):
                        if key == sdl2.SDLK_z:
                            self.selected_npc.attack(1)
                            print("⚔ Onre Attack Type 1!")
                        
                        elif key == sdl2.SDLK_x:
                            self.selected_npc.attack(2)
                            print("⚔ Onre Attack Type 2!")
                        
                        elif key == sdl2.SDLK_c:
                            self.selected_npc.attack(3)
                            print("⚔ Onre Attack Type 3!")
                    
                    # Common combat controls
                    if key == sdl2.SDLK_t:
                        self.selected_npc.take_damage(20)
                        print(f"✗ Damaged! Health: {self.selected_npc.health}/{self.selected_npc.max_health}")
                    
                    elif key == sdl2.SDLK_y:
                        self.selected_npc.health = min(self.selected_npc.health + 20, 
                                                        self.selected_npc.max_health)
                        print(f"✓ Healed! Health: {self.selected_npc.health}/{self.selected_npc.max_health}")
                    
                    elif key == sdl2.SDLK_u:
                        self.selected_npc.take_damage(self.selected_npc.health)
                        print(f"☠ {self.npc_type} killed! Health: {self.selected_npc.health}")
                
                # State changes (all modes)
                if key == sdl2.SDLK_o:
                    self.selected_npc.state = NPCState.WALK
                    self.selected_npc.current_frame = 0
                    print("→ State: WALK")
                
                elif key == sdl2.SDLK_p:
                    self.selected_npc.state = NPCState.RUN
                    self.selected_npc.current_frame = 0
                    print("→ State: RUN")
    
    def update(self):
        """Update game state."""
        # Calculate delta time
        current_time = sdl2.SDL_GetTicks()
        delta_time = (current_time - self.clock) / 1000.0
        self.clock = current_time
        
        # Update NPCs based on mode
        if self.test_mode == "patrol":
            self.npc_manager.update_all(delta_time)
        elif self.test_mode == "manual":
            # Only update animations and cooldowns, not auto-movement
            for npc in self.npc_manager.npcs:
                npc._update_animation()
                if npc.attack_cooldown > 0:
                    npc.attack_cooldown -= 1
                if npc.state in [NPCState.WALK, NPCState.RUN]:
                    npc._update_movement()
        elif self.test_mode == "combat":
            # Update animations and cooldowns
            for npc in self.npc_manager.npcs:
                npc._update_animation()
                if npc.attack_cooldown > 0:
                    npc.attack_cooldown -= 1
                if npc.health <= 0 and npc.state != NPCState.DEAD:
                    npc.state = NPCState.DEAD
                    npc.current_frame = 0
    
    def render(self):
        """Render game objects."""
        # Clear screen with dark background
        sdl2.SDL_SetRenderDrawColor(self.renderer, 20, 20, 40, 255)
        sdl2.SDL_RenderClear(self.renderer)
        
        # Draw ground line
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 100, 120, 255)
        sdl2.SDL_RenderDrawLine(self.renderer, 0, WINDOW_HEIGHT - 150, 
                               WINDOW_WIDTH, WINDOW_HEIGHT - 150)
        
        # Draw patrol boundaries for selected NPC
        if self.selected_npc:
            # Left boundary
            sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 0, 0, 128)
            sdl2.SDL_RenderDrawLine(self.renderer, 
                                   int(self.selected_npc.patrol_left_bound), 0,
                                   int(self.selected_npc.patrol_left_bound), WINDOW_HEIGHT)
            # Right boundary
            sdl2.SDL_RenderDrawLine(self.renderer, 
                                   int(self.selected_npc.patrol_right_bound), 0,
                                   int(self.selected_npc.patrol_right_bound), WINDOW_HEIGHT)
        
        # Render all NPCs
        self.npc_manager.render_all()
        
        # Draw health bar for selected NPC
        if self.selected_npc and self.selected_npc.is_alive():
            self._draw_health_bar(self.selected_npc)
        
        # Draw NPC type indicator
        self._draw_npc_indicator()
        
        # Draw info text
        self._draw_info_text()
        
        # Present renderer
        sdl2.SDL_RenderPresent(self.renderer)
    
    def _draw_health_bar(self, npc):
        """Draw health bar above NPC."""
        bar_width = 60
        bar_height = 6
        bar_x = int(npc.x)
        bar_y = int(npc.y) - 15
        
        # Background (red)
        bg_rect = sdl2.SDL_Rect(bar_x, bar_y, bar_width, bar_height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 200, 0, 0, 255)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Health (green)
        health_width = int(bar_width * (npc.health / npc.max_health))
        health_rect = sdl2.SDL_Rect(bar_x, bar_y, health_width, bar_height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 200, 0, 255)
        sdl2.SDL_RenderFillRect(self.renderer, health_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
    
    def _draw_npc_indicator(self):
        """Draw indicator box around selected NPC."""
        if not self.selected_npc:
            return
        
        # Draw yellow box around selected NPC
        indicator_rect = sdl2.SDL_Rect(
            int(self.selected_npc.x) - 5,
            int(self.selected_npc.y) - 5,
            self.selected_npc.width + 10,
            self.selected_npc.height + 10
        )
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 0, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, indicator_rect)
    
    def _draw_info_text(self):
        """Draw information text on screen."""
        # This is a simple implementation without text rendering
        # In a full game, you would use SDL_ttf for text
        pass
    
    def run(self):
        """Main test loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            
            # Cap frame rate
            sdl2.SDL_Delay(1000 // FPS)
    
    def cleanup(self):
        """Clean up resources."""
        print("\n" + "="*70)
        print("Cleaning up NPC test...")
        print("="*70)
        
        self.npc_manager.cleanup()
        
        if self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
        
        if sdlimage:
            sdlimage.IMG_Quit()
        sdl2.SDL_Quit()
        
        print("Test completed successfully!")


def main():
    """Entry point for NPC testing."""
    try:
        test = NPCTest()
        test.run()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'test' in locals():
            test.cleanup()


if __name__ == "__main__":
    main()
