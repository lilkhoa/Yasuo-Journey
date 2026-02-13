import sdl2
import sdl2.ext
import random
from sdl2 import SDL_Rect, SDL_RenderCopy
from settings import *
from world.map import GameMap
from core.camera import Camera

class DroppedItem:
    def __init__(self, x, y, texture, width, height, item_type="potion_red", item_name="Health Potion"):
        self.x = x
        self.y = y
        self.width = width     # scale item 2 times
        self.height = height

        self.texture = texture
        self.item_type = item_type      # item's name to display or logic processing
        self.item_name = item_name

        # Bounce physics
        self.vel_x = random.uniform(-3, 3)      # drop randomly to the left or right
        self.vel_y = random.uniform(-6, -3)     # up bouncing
        self.gravity = 0.4
        self.on_ground = False

        # collecting effects
        self.is_collected = False

    def update(self, dt, game_map: GameMap):
        if self.is_collected:
            return      # logic UI will do later
        
        # 1. gravity
        self.vel_y += self.gravity
        if self.vel_y > MAX_FALL_SPEED: self.vel_y = MAX_FALL_SPEED

        # 2. update position
        self.x += self.vel_x
        self.y += self.vel_y

        # 3. friction with the air (such that item can not sliding forever)
        if self.on_ground:
            self.vel_x *= 0.9

        # 4. map collision
        # create virtual rect to check the collision
        item_rect = SDL_Rect(int(self.x), int(self.y), self.width, self.height)
        nearby_tiles = game_map.get_tile_rects_around(self.x, self.y, self.width, self.height)

        self.on_ground = False
        for tile in nearby_tiles:
            if sdl2.SDL_HasIntersection(item_rect, tile):
                # collision with y-axis (drop to the ground)
                if self.vel_y > 0:
                    self.y = tile.y - self.height
                    self.vel_y = 0
                    self.vel_x = 0
                    self.on_ground = True   # do not move
                    break

    def render(self, renderer, camera: Camera):
        if self.is_collected:
            return
        
        dst_rect = SDL_Rect(
            int(self.x - camera.camera.x),
            int(self.y - camera.camera.y),
            self.width,
            self.height
        )

        SDL_RenderCopy(renderer, self.texture, None, dst_rect)

