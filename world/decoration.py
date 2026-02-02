import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sdl2
import sdl2.ext 
from sdl2 import SDL_RenderCopy, SDL_Rect, SDL_GetTicks
from enum import Enum
from settings import *
from core.camera import Camera

DECO_DIR = "assets/Map/decorations"
SHOP_ANIM_PATH = "assets/Map/decorations/shop_anim.png" 

# CONFIG ANIMATION SHOP
SHOP_FRAME_WIDTH = 118
SHOP_FRAME_HEIGHT = 128
SHOP_TOTAL_FRAMES = 6   # number of sprite in the sheet 
SHOP_ANIM_SPEED = 150   # change frame speed (ms). frame / 1000 (ms)=> 150 ms / frame

DECO_DEFINITIONS = {
    'f': 'FENCE_1',      
    'F': 'FENCE_2',   
    'g': 'GRASS_1',     
    'G': 'GRASS_2',      
    'h': 'GRASS_3',    
    'l': 'LAMP',    
    'r': 'ROCK_1',    
    'R': 'ROCK_2',    
    'B': 'ROCK_3',
    'i': 'SIGN',
    'S': 'SHOP'     
}

class Decoration:
    def __init__(self, renderer):
        '''
            Intialize some decorations in assets/Map/decorations/*.png
        '''
        if not renderer:
            print(f"Renderer must be existed before create decorations!")

        factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)

        try:
            # Load textures
            self.textures = {
                'FENCE_1': factory.from_image(os.path.join(DECO_DIR, "fence_1.png")).texture,
                'FENCE_2': factory.from_image(os.path.join(DECO_DIR, "fence_2.png")).texture,
                'GRASS_1': factory.from_image(os.path.join(DECO_DIR, "grass_1.png")).texture,
                'GRASS_2': factory.from_image(os.path.join(DECO_DIR, "grass_2.png")).texture,
                'GRASS_3': factory.from_image(os.path.join(DECO_DIR, "grass_3.png")).texture,
                'LAMP':    factory.from_image(os.path.join(DECO_DIR, "lamp.png")).texture,
                'ROCK_1':  factory.from_image(os.path.join(DECO_DIR, "rock_1.png")).texture,
                'ROCK_2':  factory.from_image(os.path.join(DECO_DIR, "rock_2.png")).texture,
                'ROCK_3':  factory.from_image(os.path.join(DECO_DIR, "rock_3.png")).texture, # Lưu ý check lại file rock_3
                'SIGN':    factory.from_image(os.path.join(DECO_DIR, "sign.png")).texture,
                'SHOP':    factory.from_image(SHOP_ANIM_PATH).texture
            }
        except Exception as E:
            print(f"Loading image error {E}!")
            return

        # Define original size (w, h) for each one
        self.DECO_INFO = {
            'FENCE_1'   : (73, 19),
            'FENCE_2'   : (72, 19),
            'GRASS_1'   : (8, 3),
            'GRASS_2'   : (10, 5),
            'GRASS_3'   : (9, 4),
            'LAMP'      : (23, 57),
            'ROCK_1'    : (20, 11),
            'ROCK_2'    : (27, 12),
            'ROCK_3'    : (45, 18),
            'SIGN'      : (22, 31),
            'SHOP'      : (SHOP_FRAME_WIDTH, SHOP_FRAME_HEIGHT)      
        }
        
    def render(self, renderer, char_code: str, grid_x, grid_y, camera: Camera):
        """
            Render decoration based on Grid Coordinate
        """
        if char_code not in DECO_DEFINITIONS: return

        name = DECO_DEFINITIONS[char_code]
        w, h = self.DECO_INFO[name]
        texture = self.textures[name]

        # process shop animation
        src_rect = SDL_Rect(0, 0, w, h)
        if name == 'SHOP':
            current_time = SDL_GetTicks()
            current_frame = (current_time // SHOP_ANIM_SPEED) % SHOP_TOTAL_FRAMES
            src_rect.x = current_frame * SHOP_FRAME_WIDTH

        # --- setup render position
        # 1. calculate the real world position for this grid cell
        world_x = grid_x * TILE_SIZE
        world_y = grid_y * TILE_SIZE
        
        # 2. alignment for bottom edge of deco == bottom of grid cell
        # => this make we place the fence or grass properly on the block
        dst_w = int(w * SCALE_FACTOR)
        dst_h = int(h * SCALE_FACTOR)

        # offset y for bottom of deco texture touch the bottom of the grid cell
        # render y = (Bottom of grid cell) - (height of texture)
        final_world_y = (world_y + TILE_SIZE) - dst_h

        # offset x (optional if want to left, right or center align)
        # default: left align
        final_world_x = world_x

        # 3. Apply camera
        dst_x = int(final_world_x - camera.camera.x)
        dst_y = int(final_world_y - camera.camera.y)

        # DEBUG: Print coordinate to check if it's off-screen
        # if name == 'FENCE_1' and grid_x < 10: 
        #    print(f"DEBUG: Rendering {name} at Screen({dst_x}, {dst_y}) Size({dst_w}, {dst_h})")

        dst_rect = SDL_Rect(dst_x, dst_y, dst_w, dst_h)
        SDL_RenderCopy(renderer, texture, src_rect, dst_rect)

        
        
    


