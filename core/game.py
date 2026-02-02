import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sdl2
import sdl2.ext
from settings import *
from world.map import GameMap
from world.decoration import Decoration
from sdl2 import SDL_Rect, SDL_RenderCopy
from camera import Camera

# Long test map to test camera scroll: TERRAIN
TEST_LEVEL = [
    "                                                  ",  
    "                                                  ", 
    "                                                  ", 
    "  2233                    2233                    ", 
    "          (- - 8 8 8 8 8 8        (- - 8 8 8 8 8 8", 
    "      [== 78 8 0 0 0 0 0 0    [== 78 8 0 0 0 0 0 0", 
    "-5= =5- - - 68 0 0 0 0 0 0-5= =5- - - 68 0 0 0 0 0", 
    "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ", 
]

# DECO MAP (Mask Map)
# Lưu ý: the length must be compatible
DECO_MAP = [
    "                                                  ", 
    "    ff                                            ", 
    "                                                  ", 
    "                          S                       ", # f: hàng rào, S: Shop
    "          g g              l      g g             ", # g: cỏ, l: đèn
    "      r   r                       r               ", # r: đá
    "                                                  ", 
    "                                                  ", 
]

# Fake player class to simulate Player to test Camera
class FakePlayer:
    def __init__(self):
        self.rect = SDL_Rect(100, 400, 50, 100) # x, y, w, h
    def move(self, keys, map_width):
        if keys[sdl2.SDL_SCANCODE_RIGHT]:
            self.rect.x += 10
        if keys[sdl2.SDL_SCANCODE_LEFT]:
            self.rect.x -= 10
        # Limit
        self.rect.x = max(0, min(self.rect.x, map_width - 50))

def draw_bg(renderer, texture, camera_x, speed_factor):
    """
        speed_factor:
            0.0 -> do not move
            0.5 -> move to opposite direction, with speed = 1/2 player
            1.0 -> equal to player
    """
    bg_width = WINDOW_WIDTH

    relative_x = (camera_x * speed_factor) % bg_width

    src_rect = SDL_Rect(0, 0, 320, 180)
    dst_rect1 = SDL_Rect(int(-relative_x), 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    SDL_RenderCopy(renderer, texture, src_rect, dst_rect1)

    if relative_x > 0:
        dst_rect2 = SDL_Rect(int(-relative_x + bg_width), 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        SDL_RenderCopy(renderer, texture, src_rect, dst_rect2)

def run():
    sdl2.ext.init()
    window = sdl2.ext.Window("Project Game Demo", size=(WINDOW_WIDTH, WINDOW_HEIGHT))
    window.show()
    renderer = sdl2.ext.Renderer(window, flags=sdl2.SDL_RENDERER_PRESENTVSYNC)
    factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
    
    try:
        tileset_sprite = factory.from_image("assets/Map/oak_woods_tileset.png")
        tileset_texture = tileset_sprite.texture

        # Load 3 Background layers (far to near order)
        bg1_sprite = factory.from_image("assets/Map/background/background_layer_1.png") # sky
        bg1_tex = bg1_sprite.texture
        
        bg2_sprite = factory.from_image("assets/Map/background/background_layer_2.png") # far forest
        bg2_tex = bg2_sprite.texture

        bg3_sprite = factory.from_image("assets/Map/background/background_layer_3.png") # near forest
        bg3_tex = bg3_sprite.texture

    except Exception as e:
        print(f"Load sprite error: {e}")
        return

    # 1. init Map and decoration handler
    my_map = GameMap(TEST_LEVEL, DECO_MAP)
    deco_mgr = Decoration(renderer)

    # 2. init Camera
    camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)

    # 3. simulate Player
    player = FakePlayer()

    # 4.  game loop
    running = True
    while running:
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
        
        # Update Logic
        keys = sdl2.SDL_GetKeyboardState(None)
        player.move(keys, my_map.width_pixel)
        
        # update Camera theo Player
        camera.update(player.rect, my_map.width_pixel)

        # Render
        renderer.clear()
        sdl_renderer = renderer.sdlrenderer

        # RENDER BACKGROUND PARALLAX
        # Layer 1 (Sky): Move extremely slow (0.1) or do not move (0)
        draw_bg(sdl_renderer, bg1_tex, camera.camera.x, 0.1) 
        
        # Layer 2 (far forest): move with medium speed (0.4)
        draw_bg(sdl_renderer, bg2_tex, camera.camera.x, 0.4) 
        
        # Layer 3 (near forest): move faster (0.7),
        draw_bg(sdl_renderer, bg3_tex, camera.camera.x, 0.7)

        # render Map move with speed 1.0
        my_map.render(sdl_renderer, tileset_texture, deco_mgr, camera)
        
        # Vẽ Player (Màu đỏ) để biết nó đang ở đâu
        # Cần tính vị trí player trên màn hình (Apply Camera)
        player_screen_rect = camera.apply(player.rect)
        sdl2.SDL_SetRenderDrawColor(sdl_renderer, 255, 0, 0, 255)
        sdl2.SDL_RenderFillRect(sdl_renderer, player_screen_rect)

        renderer.present()

    sdl2.ext.quit()

if __name__ == "__main__":
    run()