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

# CONFIG ANIMATION SHOP
SHOP_FRAME_WIDTH = 118
SHOP_FRAME_HEIGHT = 128
SHOP_TOTAL_FRAMES = 6   # number of sprite in the sheet 
SHOP_ANIM_SPEED = 150   # change frame speed (ms). frame / 1000 (ms)=> 150 ms / frame

FENCE_SCALE = 3
GRASS_SCALE = 4
LAMP_SCALE = 4
ROCK_SCALE = 4
SIGN_SCALE = 4
SHOP_SCALE = 4

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
            return

        factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
        
        # 1. create repository SPRITE (IMPORTANT: for Python does not remove it)
        self.sprites = {} 
        self.textures = {}

        try:
            
            # Helper function to safety load
            def load(name, filename):
                full_path = os.path.join(DECO_DIR, filename)
                # store Sprite into self.sprites to keep it "live"
                sprite = factory.from_image(full_path)
                self.sprites[name] = sprite
                # store texture
                self.textures[name] = sprite.texture

            load('FENCE_1', "fence_1.png")
            load('FENCE_2', "fence_2.png")
            load('GRASS_1', "grass_1.png")
            load('GRASS_2', "grass_2.png")
            load('GRASS_3', "grass_3.png")
            load('LAMP',    "lamp.png")
            load('ROCK_1',  "rock_1.png")
            load('ROCK_2',  "rock_2.png")
            load('ROCK_3',  "rock_3.png")
            load('SIGN',    "sign.png")
            load('SHOP',    "shop_anim.png")
            
            print("DEBUG: Decorations loaded successfully!")

        except Exception as E:
            print(f"Loading image error: {E}")
            return

        # Define original size (w, h, scale_factor) for each one
        self.DECO_INFO = {
            'FENCE_1'   : (73, 19, FENCE_SCALE),
            'FENCE_2'   : (72, 19, FENCE_SCALE),
            'GRASS_1'   : (8, 3, GRASS_SCALE),
            'GRASS_2'   : (10, 5, GRASS_SCALE),
            'GRASS_3'   : (9, 4, GRASS_SCALE),
            'LAMP'      : (23, 57, LAMP_SCALE),
            'ROCK_1'    : (20, 11, ROCK_SCALE),
            'ROCK_2'    : (27, 12, ROCK_SCALE),
            'ROCK_3'    : (45, 18, ROCK_SCALE),
            'SIGN'      : (22, 31, SIGN_SCALE),
            'SHOP'      : (SHOP_FRAME_WIDTH, SHOP_FRAME_HEIGHT, SHOP_SCALE)      
        }
        
    def render(self, renderer, char_code: str, grid_x, grid_y, camera: Camera):
        """
            Render decoration based on Grid Coordinate
        """
        if char_code not in DECO_DEFINITIONS: return

        name = DECO_DEFINITIONS[char_code]
        w, h, scale_factor = self.DECO_INFO[name]
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
        dst_w = int(w * scale_factor)
        dst_h = int(h * scale_factor)

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

        
        
    


