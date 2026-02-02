import sys
import os
from sdl2 import SDL_Rect
from settings import *

class Camera:
    def __init__(self, width, height):
        # width, height: window size (usually equal 2 screen width)
        self.camera = SDL_Rect(0, 0, width, height)
        self.width = width
        self.height = height

        # config dead zone 
        # player could move freely in the zone from 30% -> 70% window
        # if through this zone => move camera
        self.border_left = int(width * 0.3)
        self.border_right = int(width * 0.7)

    def apply(self, target_rect):
        """
            This function is used for PLAYER or ENEMY (small number)
            TILE with the large number will render directly outside this class
        """
        return SDL_Rect(target_rect.x - self.camera.x,
                        target_rect.y - self.camera.y,
                        target_rect.w, target_rect.h)
    
    def update(self, target, map_width):
        """
            target: is SDL_Rect of PLAYER (x, y, w, h)
        """
        # if camera does not move => x_on_screen = target_x
        x_on_screen = target.x - self.camera.x

        # collision with right border (go forward)
        if x_on_screen > self.border_right:
            self.camera.x += (x_on_screen - self.border_right)

        # collision with left border (go backward)
        if x_on_screen < self.border_left:
            self.camera.x -= (self.border_left - x_on_screen)

        self.camera.x = max(0, self.camera.x)
        self.camera.x = min(map_width - self.width, self.camera.x) # cause the max x position of camera is the map_width = self.width, cause this is the last frame of the game