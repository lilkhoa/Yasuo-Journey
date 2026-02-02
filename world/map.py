import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import ctypes
import sdl2
import sdl2.ext
from sdl2 import SDL_Rect, SDL_RenderCopy
from enum import Enum
from settings import *
from world.decoration import Decoration
from core.camera import Camera

# Define the cut coordinates in file tileset (Source Rect)
# Base on the data we have take from the tileset: x = top_left_x, y = top_left_y, w = bottom_right_x - top_left_x, h = bottom_right_y - top_left_y
TILE_DEFINITIONS = {
    '(': (0, 0, 24, 24),        # single left padding yellow soil
    '-': (24, 0, 48, 24),       # long yellow soil
    ')': (72, 0, 24, 24),       # single right padding yellow  soil
    '[': (120, 0, 24, 24),      # single left padding gray soil
    '=': (143, 0, 48, 24),      # long gray soil
    ']': (191, 0, 24, 24),      # single right padding gray soil
    '0': (24, 72, 48, 24),      # medium soil 
    '1': (288, 145, 48, 24),    # medium middle yellow, gray at two side soil
    '2': (240, 0, 24, 24),      # single yellow rock bounding
    '3': (288, 0, 24, 24),      # single gray rock bounding
    '4': (288, 145, 24, 24),    # gray -> yello matching
    '5': (312, 145, 24, 24),    # yello -> gray matching
    '6': (288, 96, 24, 24),     # yellow finish transition
    '7': (312, 96, 24, 24),     # gray finish transition
    '8': (121, 24, 72, 24),     # medium pure soil 
}

class GameMap: 
    def __init__(self, map_data):
        self.map_data = map_data
        # real long from map (Pixel) to limit Camera
        self.width_pixel = len(self.map_data[0]) * TILE_SIZE
    
    def render(self, renderer, tileset_texture, camera: Camera):
        # camera: Camera object from game.py

        # 1. Culling technique (just render the things need to render)
        start_col = int(camera.camera.x // TILE_SIZE) - 1
        end_col = start_col + (WINDOW_WIDTH // TILE_SIZE) + 3 # to draw over the edge

        # check the limit range
        start_col = max(0, start_col)
        end_col = min(len(self.map_data[0]), end_col)
        
        cam_x = camera.camera.x

        for y_index, row in enumerate(self.map_data):
            # just traverse the visable range of colun
            for x_index in range(start_col, end_col):
                if x_index >= len(row):
                    break

                char = row[x_index]

                if char in TILE_DEFINITIONS:
                    # 1. Get the cutting information
                    src_x, src_y, src_w, src_h = TILE_DEFINITIONS[char]
                    src_rect = SDL_Rect(src_x, src_y, src_w, src_h)

                    # 2. Calculate the render postion
                    # Logic resize for tile '0'
                    if char == '0':
                        dst_w = src_w * SCALE_FACTOR
                        dst_h = int(src_h * 1.5 * SCALE_FACTOR)
                        # Logic modify special y offset
                        dst_y = (y_index * TILE_SIZE) - int(TILE_SIZE / 4.5)
                    else:
                        dst_w = src_w * SCALE_FACTOR
                        dst_h = src_h * SCALE_FACTOR
                        dst_y = y_index * TILE_SIZE

                    # Tọa độ X trên màn hình = Tọa độ thế giới - Tọa độ Camera
                    dst_x = (x_index * TILE_SIZE) - cam_x

                    dst_rect = SDL_Rect(dst_x, dst_y, dst_w, dst_h)
                    
                    SDL_RenderCopy(renderer, tileset_texture, src_rect, dst_rect)
                    

        

