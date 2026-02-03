"""
Ghost NPC Damage and Death Test
Test Ghost NPC taking damage, losing health, dying, and recovery behavior.
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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from entities.npc import Ghost, NPCState
from entities.projectile import ProjectileManager


# Window constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60


class Player:
    """Simple player representation as a controllable rectangle."""
    
    def __init__(self, x, y):
        """Initialize player."""
        self.x = x
        self.y = y
        self.width = 50
        self.height = 100
        self.speed = 5
        self.health = 100
        self.max_health = 100
        
        # Movement state
        self.move_left = False
        self.move_right = False
    
    def update(self):
        """Update player position based on input."""
        if self.move_left:
            self.x -= self.speed
        if self.move_right:
            self.x += self.speed
        
        # Keep player in bounds (horizontal only)
        self.x = max(0, min(WINDOW_WIDTH - self.width, self.x))
    
    def render(self, renderer):
        """Render player as a blue rectangle."""
        sdl2.SDL_SetRenderDrawColor(renderer, 50, 100, 255, 255)
        rect = sdl2.SDL_Rect(int(self.x), int(self.y), self.width, self.height)
        sdl2.SDL_RenderFillRect(renderer, rect)
        
        # Draw border
        sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(renderer, rect)
    
    def take_damage(self, amount):
        """Take damage from NPC."""
        self.health = max(0, self.health - amount)
    
    def get_bounds(self):
        """Get bounding box for collision detection."""
        return (self.x, self.y, self.width, self.height)


class GhostDamageTest:
    """Ghost NPC damage and death testing application."""
    
    def __init__(self):
        """Initialize testing application."""
        # Initialize SDL2
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
            print(f"SDL2 initialization failed: {sdl2.SDL_GetError()}")
            sys.exit(1)
        
        # Initialize SDL_image
        if sdlimage:
            img_flags = sdlimage.IMG_INIT_PNG
            if not (sdlimage.IMG_Init(img_flags) & img_flags):
                print(f"SDL_image initialization failed: {sdlimage.IMG_GetError()}")
                sdl2.SDL_Quit()
                sys.exit(1)
        
        # Create window
        self.window = sdl2.SDL_CreateWindow(
            b"Ghost NPC - Damage and Death Test",
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            sdl2.SDL_WINDOW_SHOWN
        )
        
        if not self.window:
            print(f"Window creation failed: {sdl2.SDL_GetError()}")
            sdl2.SDL_Quit()
            sys.exit(1)
        
        # Create renderer
        self.renderer = sdl2.SDL_CreateRenderer(
            self.window,
            -1,
            sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
        )
        
        if not self.renderer:
            print(f"Renderer creation failed: {sdl2.SDL_GetError()}")
            sdl2.SDL_DestroyWindow(self.window)
            sdl2.SDL_Quit()
            sys.exit(1)

        self.sprite_factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=self.renderer)
        self.projectile_manager = ProjectileManager(self.renderer)
        
        # Create player (controllable blue rectangle)
        self.player = Player(WINDOW_WIDTH // 2 + 200, WINDOW_HEIGHT // 2 - 48)
        
        # Create Ghost NPC at center of screen
        self.ghost = Ghost(
            x=WINDOW_WIDTH // 2 - 48,
            y=WINDOW_HEIGHT // 2 - 48,
            sprite_factory=self.sprite_factory,
            texture_factory=None,
            renderer=self.renderer,
            projectile_manager=self.projectile_manager
        )
        
        # Enable chase behavior
        self.ghost.set_player(self.player)
        
        # Damage control
        self.damage_amount = 10
        self.damage_cooldown = 0
        self.damage_cooldown_max = 30  # Frames between damage applications
        
        # Running state
        self.running = True
        self.clock = sdl2.SDL_GetTicks()
    
    def handle_events(self):
        """Handle SDL2 events."""
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(event):
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                # Press SPACE to damage the Ghost
                if event.key.keysym.sym == sdl2.SDLK_SPACE:
                    if self.damage_cooldown <= 0 and self.ghost.is_alive():
                        self.ghost.take_damage(self.damage_amount)
                        self.damage_cooldown = self.damage_cooldown_max
                        print(f"Ghost took {self.damage_amount} damage! Health: {self.ghost.health}/{self.ghost.max_health}")
                
                # Press R to reset Ghost
                elif event.key.keysym.sym == sdl2.SDLK_r:
                    self.ghost.health = self.ghost.max_health
                    self.ghost.state = NPCState.IDLE
                    self.ghost.current_frame = 0
                    self.ghost.hurt_animation_complete = False
                    self.ghost.death_animation_complete = False
                    print(f"Ghost reset! Health: {self.ghost.health}/{self.ghost.max_health}")
                
                # Press P to toggle patrol
                elif event.key.keysym.sym == sdl2.SDLK_p:
                    if self.ghost.is_patrolling:
                        self.ghost.stop_patrol()
                        print("Ghost patrol: DISABLED")
                    else:
                        self.ghost.start_patrol()
                        print("Ghost patrol: ENABLED")
                
                # Player movement - Arrow keys
                elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.player.move_left = True
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.player.move_right = True
                
                # Press ESC to quit
                elif event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    self.running = False
            
            elif event.type == sdl2.SDL_KEYUP:
                # Player movement - Arrow keys
                if event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.player.move_left = False
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.player.move_right = False
    
    def update(self):
        """Update game state."""
        # Update damage cooldown
        if self.damage_cooldown > 0:
            self.damage_cooldown -= 1
        
        # Update player
        self.player.update()
        
        # Update Ghost NPC
        self.ghost.update()
        
        # Update projectiles and check collisions with player
        self.projectile_manager.update_all()
        for projectile in self.projectile_manager.projectiles[:]:
            if projectile.check_collision(self.player):
                self.player.take_damage(projectile.damage)
                projectile.on_hit()
                print(f"Player took {projectile.damage} damage! Health: {self.player.health}/{self.player.max_health}")
    
    def render(self):
        """Render everything to screen."""
        # Clear screen with dark background
        sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 30, 40, 255)
        sdl2.SDL_RenderClear(self.renderer)
        
        # Draw ground line
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 100, 100, 255)
        ground_y = WINDOW_HEIGHT // 2 + 50
        sdl2.SDL_RenderDrawLine(self.renderer, 0, ground_y, WINDOW_WIDTH, ground_y)
        
        # Render player (blue rectangle)
        self.player.render(self.renderer)
        
        # Render Ghost NPC
        self.ghost.render()
        
        # Render projectiles
        self.projectile_manager.render_all()
        
        # Draw health bars
        self.render_health_bar(self.ghost, "Ghost")
        self.render_health_bar(self.player, "Player")
        
        # Draw instructions
        self.render_instructions()
        
        # Present
        sdl2.SDL_RenderPresent(self.renderer)
    
    def render_health_bar(self, entity, label):
        """Render health bar above entity."""
        bar_width = 100
        bar_height = 10
        bar_x = int(entity.x + entity.width // 2 - bar_width // 2)
        bar_y = int(entity.y - 20)
        
        # Background (red)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 200, 50, 50, 255)
        bg_rect = sdl2.SDL_Rect(bar_x, bar_y, bar_width, bar_height)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Health (green)
        health_ratio = entity.health / entity.max_health
        health_width = int(bar_width * health_ratio)
        if health_width > 0:
            sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 200, 50, 255)
            health_rect = sdl2.SDL_Rect(bar_x, bar_y, health_width, bar_height)
            sdl2.SDL_RenderFillRect(self.renderer, health_rect)
        
        # Border (white)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
    
    def render_instructions(self):
        """Render instruction text (using simple rectangles as placeholders)."""
        # Draw instruction panel
        panel_height = 120
        sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 50, 60, 200)
        panel_rect = sdl2.SDL_Rect(10, 10, 400, panel_height)
        sdl2.SDL_RenderFillRect(self.renderer, panel_rect)
        
        # Draw border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 150, 150, 150, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, panel_rect)
        
        # Note: Text rendering would require SDL_ttf
        # For now, print instructions to console at startup
    
    def print_instructions(self):
        """Print instructions to console."""
        print("\n" + "="*60)
        print("Ghost NPC - Damage, Chase, and Death Test")
        print("="*60)
        print("Controls:")
        print("  LEFT/RIGHT ARROW - Move player (blue rectangle)")
        print("  SPACE            - Deal 10 damage to Ghost")
        print("  P                - Toggle Ghost patrol mode")
        print("  R                - Reset Ghost to full health")
        print("  ESC              - Quit")
        print()
        print("Test Behaviors:")
        print("  - Ghost patrols when patrol mode is enabled")
        print("  - Ghost chases player when in detection range")
        print("  - Ghost attacks player when in attack range")
        print("  - Ghost returns to patrol/chase after taking damage")
        print()
        print(f"Ghost Health: {self.ghost.health}/{self.ghost.max_health}")
        print(f"Ghost State: {self.ghost.state.name}")
        print(f"Patrol Mode: {'ENABLED' if self.ghost.is_patrolling else 'DISABLED'}")
        print("="*60 + "\n")
    
    def run(self):
        """Main game loop."""
        self.print_instructions()
        
        # Enable patrol for testing
        self.ghost.start_patrol()
        
        frame_delay = 1000 // FPS
        
        while self.running:
            frame_start = sdl2.SDL_GetTicks()
            
            self.handle_events()
            self.update()
            self.render()
            
            # Cap frame rate
            frame_time = sdl2.SDL_GetTicks() - frame_start
            if frame_time < frame_delay:
                sdl2.SDL_Delay(frame_delay - frame_time)
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'ghost'):
            self.ghost.cleanup()
        if hasattr(self, 'projectile_manager'):
            self.projectile_manager.cleanup()
        if hasattr(self, 'renderer'):
            sdl2.SDL_DestroyRenderer(self.renderer)
        if hasattr(self, 'window'):
            sdl2.SDL_DestroyWindow(self.window)
        if sdlimage:
            sdlimage.IMG_Quit()
        sdl2.SDL_Quit()


def main():
    """Entry point."""
    test = GhostDamageTest()
    try:
        test.run()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.cleanup()


if __name__ == "__main__":
    main()
