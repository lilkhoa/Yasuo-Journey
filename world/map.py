import os
import ctypes
import sdl2
import sdl2.ext
from sdl2 import SDL_Rect, SDL_RenderCopy
from enum import Enum
from settings import *

# Define the cut coordinates in file tileset (Source Rect)
# Base on the data we have take from the tileset: x = top_left_x, y = top_left_y, w = bottom_right_x - top_left_x, h = bottom_right_y - top_left_y
TILE_DEFINITIONS = {
    '1': (120, 216, 71,23),
    '2': (240, 0, 24, 24),      # grass surface soil block
    # ....
}

class GameMap: 
    def __init__(self, map_data):
        self.map_data = map_data
    
    def render(self, renderer, tileset_texture, camera_x = 0):
        # camera_x: use to move the map when main character move

        y_index = 0
        for y_index, row in enumerate(self.map_data):
            for x_index, char in enumerate(row):

                if char in TILE_DEFINITIONS:
                    # 1. Get the cutting information
                    src_x, src_y, src_w, src_h = TILE_DEFINITIONS[char]
                    src_rect = SDL_Rect(src_x, src_y, src_w, src_h)

                    # 2. Calculate the render postion
                    # Multiply with size and need to scale to place the right place and right size
                    dst_w = src_w * SCALE_FACTOR
                    dst_h = src_h * SCALE_FACTOR

                    dst_x = (x_index * TILE_SIZE) - int(camera_x)
                    dst_y = (y_index * TILE_SIZE)

                    dst_rect = SDL_Rect(dst_x, dst_y, dst_w, dst_h)
                    
                    SDL_RenderCopy(renderer, tileset_texture, src_rect, dst_rect)
                    

        

