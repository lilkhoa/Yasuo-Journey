import sys
import os
import sdl2.ext
from sdl2 import SDL_Rect
from settings import *
from .map import GameMap
from core.camera import Camera

BOX_PUSH_THRESHOLD = 0.2  # Time (second) which the player need to hold before pushing
BOX_PUSH_SPEED_RATIO = 0.7 # Speed of Player while pushing the box (reduce 30% to normal)

class Box:
    def __init__(self, x, y, texture):
        self.x = x
        self.y = y
        self.width = int(TILE_SIZE)
        self.height = int(TILE_SIZE)

        self.texture = texture
        self.vel_y = 0
        self.gravity = GRAVITY
        self.is_falling = True

        # pushing logic
        self.push_timer = 0 # accumulate the time that player has been held
        self.is_being_pushed = False

    @property
    def rect(self):
        return SDL_Rect(int(self.x), int(self.y), self.width, self.height)
    
    @property
    def src_rect(self):
        return SDL_Rect(42, 19, BOX_WIDTH, BOX_HEIGHT)

    def update(self, dt, game_map: GameMap):
        # 1. gravity
        self.vel_y += self.gravity
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED
        
        self.y += self.vel_y

        # 2. Collide with Map (vertical axis - Y)
        # reuse checking object surrounding tiles from GameMap
        nearby_tiles = game_map.get_tile_rects_around(self.x, self.y, self.width, self.height)

        box_rect = self.rect
        self.is_failing = True  # falling is default case

        for tile in nearby_tiles:
            if sdl2.SDL_HasIntersection(box_rect, tile):
                if self.vel_y > 0:  # falling and reach the ground surface
                    # Snap the position above the tile
                    self.y = tile.y - self.height
                    self.vel_y = 0
                    self.is_falling = False
        
        # reset the pushing state (will be set to True in player.update if collide)
        if not self.is_being_pushed:
            self.push_timer = 0 # reset the timer if the player do not hold

        self.is_being_pushed = False
    
    def render(self, renderer, camera: Camera):
        # estimate the position to camera
        dst_rect = SDL_Rect(
            int(self.x - camera.camera.x),  # self.x is the x position of the box in the whole long map
            int(self.y - camera.camera.y),
            self.width,
            self.height
        )

        # Render (src_rect is the full texture because we have cut the image while loading)
        sdl2.SDL_RenderCopy(renderer, self.texture, self.src_rect, dst_rect)

    def push(self, dx, dt, game_map: GameMap):
        """
            Called from the Player when horizontal collision
            dx: the amount of distance which the Player has made
        """
        self.is_being_pushed = True

        # increase timer
        if self.push_timer < BOX_PUSH_THRESHOLD:
            self.push_timer += dt
            return False, 0 # do not have enough force to push

        # calculate new speed
        push_dx = dx * BOX_PUSH_SPEED_RATIO

        # predict new position
        next_x = self.x + push_dx

        if next_x < 0:
            self.x = 0
            return False, 0
        
        if (next_x + self.width) > game_map.width_pixel:
            self.x = game_map.width_pixel - self.width
            return False, 0
        
        future_rect = SDL_Rect(int(next_x), int(self.y), self.width, self.height)

        # check the collision with the wall
        # if the box is collide with the wall => stop
        nearby_tiles = game_map.get_tile_rects_around(int(next_x), int(self.y), self.width, self.height)

        can_move = True
        for tile in nearby_tiles:
            for tile in nearby_tiles:
                if sdl2.SDL_HasIntersection(future_rect, tile):
                    can_move = False
                    break
                    
        if can_move: 
            self.x = next_x
            return True, push_dx
        else:
            return False, 0

    