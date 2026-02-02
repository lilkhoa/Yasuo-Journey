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

class Decoration:
    def __init__(self, renderer):
        '''
            Intialize some decorations in assets/Map/decorations/*.png
        '''
        if not renderer:
            print(f"Renderer must be existed before create decorations!")
            return

        factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)

        try:
            self.FENCE_1 = factory.from_image(os.path.join(DECO_DIR, "fence_1.png")).texture
            self.FENCE_2 = factory.from_image(os.path.join(DECO_DIR, "fence_2.png")).texture
            self.GRASS_1 = factory.from_image(os.path.join(DECO_DIR, "grass_1.png")).texture
            self.GRASS_2 = factory.from_image(os.path.join(DECO_DIR, "grass_2.png")).texture
            self.GRASS_3 = factory.from_image(os.path.join(DECO_DIR, "grass_3.png")).texture
            self.LAMP = factory.from_image(os.path.join(DECO_DIR, "lamp.png")).texture
            self.ROCK_1 = factory.from_image(os.path.join(DECO_DIR, "rock_1.png")).texture
            self.ROCK_2 = factory.from_image(os.path.join(DECO_DIR, "rock_2.png")).texture
            self.ROCK_3 = factory.from_image(os.path.join(DECO_DIR, "rock_2.png")).texture
            self.SIGN = factory.from_image(os.path.join(DECO_DIR, "sign.png")).texture

            self.SHOP_ANIM_SPRITE_SHEET = factory.from_image(SHOP_ANIM_PATH).texture

        except Exception as E:
            print(f"Loading image error {E}!")
            return

        self.DECO_ITEMS = {
            'FENCE_1'   : (73, 19, self.FENCE_1),
            'FENCE_2'   : (72, 19, self.FENCE_2),
            'GRASS_1'   : (8, 3, self.GRASS_1),
            'GRASS_2'   : (10, 5, self.GRASS_2),
            'GRASS_3'   : (9, 4, self.GRASS_3),
            'LAMP'      : (23, 57, self.LAMP),
            'ROCK_1'    : (20, 11, self.ROCK_1),
            'ROCK_2'    : (27, 12, self.ROCK_2),
            'ROCK_3'    : (45, 18, self.ROCK_3),
            'SIGN'      : (22, 31, self.SIGN)      
        }
        
    def render_deco(self, renderer, name: str, world_x, world_y, scale_factor, camera: Camera):
        # adding camera to deco go along to the map
        if not name in self.DECO_ITEMS:
            return

        # tuple extraction
        w, h, texture = self.DECO_ITEMS[name] # Unpack tuple

        src_rect = SDL_Rect(0, 0, w, h)
        
        # calculate current postion
        dst_w = w * scale_factor
        dst_h = h * scale_factor
        
        # apply camera
        dst_x = world_x - camera.camera.x
        dst_y = world_y # deco does not move along the y-axis
        
        dst_rect = SDL_Rect(dst_x, dst_y, dst_w, dst_h)

        # pass parameter to render function
        SDL_RenderCopy(renderer, texture, src_rect, dst_rect)
        
    def render_shop_anim(self, renderer, world_x, world_y, scale_factor, camera: Camera):
        """
            render animation shop
        """
        # 1. calculate currentframe based on time
        current_time = SDL_GetTicks()
        # formula: (current time / time per frame) => mod number of frames
        current_frame_index = (current_time // SHOP_ANIM_SPEED) % SHOP_TOTAL_FRAMES

        # 2. cutting position on sprite sheet (src_rect)
        src_x = current_frame_index * SHOP_FRAME_WIDTH
        src_rect = SDL_Rect(src_x, 0, SHOP_FRAME_WIDTH, SHOP_FRAME_HEIGHT)

        # 3. calculate the postition to render on screen (dst_rect) - with camera
        dst_x = int(world_x - camera.camera.x)
        dst_y = int(world_y - camera.camera.y)
        dst_w = int(SHOP_FRAME_WIDTH * scale_factor)
        dst_h = int(SHOP_FRAME_HEIGHT * scale_factor)

        dst_rect = SDL_Rect(dst_x, dst_y, dst_w, dst_h)

        # 4. Render
        SDL_RenderCopy(renderer, self.SHOP_ANIM_SPRITE_SHEET, src_rect, dst_rect)


