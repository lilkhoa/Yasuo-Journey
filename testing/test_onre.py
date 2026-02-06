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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from entities.npc import Onre, NPCState
from entities.projectile import ProjectileManager
from core.sound import get_sound_manager


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


class OnreTest:
    """Ghost NPC chase behavior testing application."""
    
    def __init__(self):
        """Initialize testing application."""
        # Initialize SDL2
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO) != 0:
            print(f"SDL2 initialization failed: {sdl2.SDL_GetError()}")
            sys.exit(1)
        
        # Initialize SDL2_image
        if sdlimage:
            img_flags = sdlimage.IMG_INIT_PNG
            if not sdlimage.IMG_Init(img_flags):
                print(f"SDL2_image initialization failed: {sdlimage.IMG_GetError()}")
        else:
            print("Warning: SDL2_image not available")
        
        # Initialize centralized SoundManager
        self.sound_manager = get_sound_manager()
        self.sound_manager.initialize()
        print("SoundManager initialized successfully")

        # Create window
        self.window = sdl2.SDL_CreateWindow(
            b"Onre NPC Chase Test - Use Arrow Keys to Move Player",
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
        
        # Initialize projectile manager
        self.projectile_manager = ProjectileManager(self.renderer)
        
        # Create player
        self.player = Player(40, 300)
        
        # Spawn Onre NPC with patrol and chase behavior
        self.onre = Onre(600, 300, self.sprite_factory, None, self.renderer, self.sound_manager)
        # Patrol bounds are automatically calculated from spawn position and patrol_radius in NPC class
        self.onre.set_player(self.player)  # Enable chase behavior
        self.onre.start_patrol()
        
        self._print_instructions()
    
    def _print_instructions(self):
        """Print control instructions."""
        print("\n" + "="*70)
        print("Onre NPC Melee Attack Test")
        print("="*70)
        print("\nCONTROLS:")
        print("  Left/Right Arrow - Move player (blue rectangle)")
        print("  ESC              - Exit")
        print("\nBEHAVIOR:")
        print("  - Onre patrols automatically between yellow boundaries")
        print("  - When player enters orange detection range, Onre chases")
        print("  - When player is in melee range, Onre attacks with blade")
        print("  - RED HITBOX shows blade collision area during dangerous frames")
        print("  - When player leaves detection area, Onre returns to patrol")
        print("  - Red marker shows Onre spawn position")
        print("="*70 + "\n")
    
    def handle_events(self):
        """Process SDL2 events."""
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                
                # Exit
                if key == sdl2.SDLK_ESCAPE:
                    self.running = False
                
                # Player movement
                elif key == sdl2.SDLK_LEFT:
                    self.player.move_left = True
                elif key == sdl2.SDLK_RIGHT:
                    self.player.move_right = True
            
            elif event.type == sdl2.SDL_KEYUP:
                key = event.key.keysym.sym
                
                # Player movement
                if key == sdl2.SDLK_LEFT:
                    self.player.move_left = False
                elif key == sdl2.SDLK_RIGHT:
                    self.player.move_right = False
    
    def update(self):
        """Update game state."""
        # Update player
        self.player.update()
        
        # Update Onre NPC (includes chase and melee logic)
        self.onre.update()
        
        # Update projectiles and check collisions with player
        self.projectile_manager.update_all()
        for projectile in self.projectile_manager.projectiles[:]:
            if projectile.check_collision(self.player):
                self.player.take_damage(projectile.damage)
                self.projectile_manager.projectiles.remove(projectile)
    
    def render(self):
        """Render everything."""
        # Clear screen (dark gray)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 255)
        sdl2.SDL_RenderClear(self.renderer)
        
        # Render player
        self.player.render(self.renderer)
        
        # Render Onre
        self.onre.render()
        
        # Draw melee hitbox visualization (during attack)
        self._draw_melee_hitbox()
        
        # Render projectiles
        self.projectile_manager.render_all()
        
        # Draw health bars
        self._draw_health_bar(self.player)
        self._draw_health_bar(self.onre)
        
        # Draw UI info
        self._draw_ui()
        
        # Present
        sdl2.SDL_RenderPresent(self.renderer)
    
    def _draw_patrol_bounds(self):
        """Draw patrol boundary lines."""
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 100, 0, 255)
        
        # Left bound
        for y in range(0, WINDOW_HEIGHT, 20):
            sdl2.SDL_RenderDrawLine(self.renderer, 
                                   int(self.onre.patrol_left_bound), y,
                                   int(self.onre.patrol_left_bound), y + 10)
        
        # Right bound
        for y in range(0, WINDOW_HEIGHT, 20):
            sdl2.SDL_RenderDrawLine(self.renderer,
                                   int(self.onre.patrol_right_bound), y,
                                   int(self.onre.patrol_right_bound), y + 10)
    
    def _draw_detection_range(self):
        """Draw detection range boundaries."""
        sdl2.SDL_SetRenderDrawColor(self.renderer, 200, 100, 0, 100)
        
        detection_left = int(self.onre.spawn_x - self.onre.detection_range)
        detection_right = int(self.onre.spawn_x + self.onre.detection_range)
        
        # Left detection bound
        for y in range(0, WINDOW_HEIGHT, 15):
            sdl2.SDL_RenderDrawLine(self.renderer, detection_left, y,
                                   detection_left, y + 8)
        
        # Right detection bound
        for y in range(0, WINDOW_HEIGHT, 15):
            sdl2.SDL_RenderDrawLine(self.renderer, detection_right, y,
                                   detection_right, y + 8)
    
    def _draw_spawn_marker(self):
        """Draw spawn position marker."""
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 0, 0, 255)
        spawn_x = int(self.onre.spawn_x)
        spawn_y = int(self.onre.spawn_y)
        
        # Draw cross marker
        sdl2.SDL_RenderDrawLine(self.renderer, spawn_x - 10, spawn_y, spawn_x + 10, spawn_y)
        sdl2.SDL_RenderDrawLine(self.renderer, spawn_x, spawn_y - 10, spawn_x, spawn_y + 10)
        
        # Draw circle
        for angle in range(0, 360, 10):
            x1 = spawn_x + int(15 * math.cos(math.radians(angle)))
            y1 = spawn_y + int(15 * math.sin(math.radians(angle)))
            x2 = spawn_x + int(15 * math.cos(math.radians(angle + 10)))
            y2 = spawn_y + int(15 * math.sin(math.radians(angle + 10)))
            sdl2.SDL_RenderDrawLine(self.renderer, x1, y1, x2, y2)    
    def _draw_melee_hitbox(self):
        """Visualize the melee attack hitbox during dangerous frames."""
        
        # Only draw during attack states
        if self.onre.state not in [NPCState.ATTACK_1, NPCState.ATTACK_2, NPCState.ATTACK_3]:
            return
        
        # Calculate hitbox using NPC's method
        hitbox_rect = self.onre._calculate_melee_hitbox()
        
        # Check if current frame is dangerous
        current_dangerous = self.onre.dangerous_frames_map.get(self.onre.state, [])
        is_dangerous = self.onre.current_frame in current_dangerous
        
        # Draw hitbox based on frame
        if is_dangerous:
            # DANGEROUS FRAME - Draw solid red (blade is swinging)
            sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 0, 0, 180)
            sdl2.SDL_RenderFillRect(self.renderer, hitbox_rect)
            
            # Border in bright red
            sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 0, 0, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, hitbox_rect)
            
            # Draw "HIT" indicator
            center_x = hitbox_rect.x + hitbox_rect.w // 2
            center_y = hitbox_rect.y + hitbox_rect.h // 2
            # Draw cross pattern
            sdl2.SDL_RenderDrawLine(self.renderer, center_x - 10, center_y, center_x + 10, center_y)
            sdl2.SDL_RenderDrawLine(self.renderer, center_x, center_y - 10, center_x, center_y + 10)
        else:
            # NON-DANGEROUS FRAME - Draw outline only (blade not active)
            sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 100, 100, 100)
            sdl2.SDL_RenderDrawRect(self.renderer, hitbox_rect)    
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
        """Draw UI information."""
        # Draw status text background
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 180)
        info_rect = sdl2.SDL_Rect(10, 10, 250, 100)
        sdl2.SDL_RenderFillRect(self.renderer, info_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, info_rect)
        
        # State indicator color
        state_colors = {
            "Idle": (100, 100, 100),
            "Walk": (100, 200, 100),
            "Chase": (255, 100, 100),
            "Run": (100, 100, 200),
            "Attack_1": (255, 0, 0),
            "Attack_2": (255, 50, 0),
            "Attack_3": (255, 100, 0)
        }
        
        color = state_colors.get(self.onre.state.value, (200, 200, 200))
        sdl2.SDL_SetRenderDrawColor(self.renderer, *color, 255)
        state_rect = sdl2.SDL_Rect(20, 20, 230, 25)
        sdl2.SDL_RenderFillRect(self.renderer, state_rect)
    
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
        self.onre.cleanup()
        
        # Clean up projectiles
        self.projectile_manager.cleanup()
        
        # Clean up SDL2
        sdl2.SDL_DestroyRenderer(self.renderer)
        sdl2.SDL_DestroyWindow(self.window)
        
        # Clean up SoundManager
        self.sound_manager.cleanup()
        
        if sdlimage:
            sdlimage.IMG_Quit()
        
        sdl2.SDL_Quit()
        
        print("[CLEANUP] Done!")


def main():
    """Entry point."""
    test = OnreTest()
    test.run()


if __name__ == "__main__":
    main()
