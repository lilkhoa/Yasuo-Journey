import sys
import os
import sdl2.ext
import random
from sdl2 import SDL_Rect
from settings import *

from core.camera import Camera
from entities.player import Player

from .map import GameMap
from .item import DroppedItem

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

BARREL_RENDER_WIDTH = 27 * 2
BARREL_RENDER_HEIGHT = 35 * 2

class Barrel:
    def __init__(self, x, y, texture, item_data):
        """
            item_data: Dictionary of tuple 
                "red_potion"[type]: (name, width, height, texture)
        """
        self.x = x
        self.y = y

        self.texture = texture      # barrel texture
        self.item_data = item_data  # dict of item's texture can be dropped
        self.is_broken = False
        self.health = 1             # broke after 1 hit

        self.src_rect = sdl2.SDL_Rect(195, 29, 27, 35)

    def get_bounds(self):
        return SDL_Rect(int(self.x), int(self.y), BARREL_RENDER_WIDTH, BARREL_RENDER_HEIGHT)
    
    def render(self, renderer, camera: Camera):
        if self.is_broken:
            return
        
        dst_rect = SDL_Rect(
            int(self.x - camera.camera.x),
            int(self.y - camera.camera.y),
            BARREL_RENDER_WIDTH,
            BARREL_RENDER_HEIGHT
        )

        sdl2.SDL_RenderCopy(renderer, self.texture, self.src_rect, dst_rect)

    def take_damage(self, amount, dropped_items_list, renderer):
        if self.is_broken:
            return

        self.health -= amount
        if self.health <= 0:
            self.break_barrel(dropped_items_list, renderer)

    def break_barrel(self, drop_items_list, renderer):
        self.is_broken = True

        # drop item logic (random 1-3 item) => drop only one item for each barrel
        num_items = 1   # random.randint(1,3)
        for _ in range(num_items):
            # random the type of item, key in dict textures:
            item_type = random.choice(list(self.item_data.keys()))
            name, width, height, tex = self.item_data[item_type]

            # create item at the barrel
            item = DroppedItem(
                self.x + BARREL_RENDER_WIDTH/2,
                self.y + BARREL_RENDER_HEIGHT/2,
                tex,
                width, height,
                item_type, name
            )
            drop_items_list.append(item)

        print("Barrel broken!")

class Chest:
    def __init__(self, world_x, grid_y_pos, sprite_sheet, item_data, text_renderer):
        '''
            real_x, real_y
        '''
        self.world_x = world_x
        self.grid_y_pos = grid_y_pos

        self.texture = sprite_sheet
        self.frame_count = 7
        self.frame_heights = [29, 33, 35, 37, 38, 36, 33]
        self.frame_width = 34
        self.top_left_corner = [
            (31,227), 
            (95,223), 
            (159,221), 
            (223,219), 
            (287, 218), 
            (351, 220), 
            (415, 223)
        ]
        
        # size to render
        self.scaled_heights = [height*2 for height in self.frame_heights]
        self.scaled_width = self.frame_width * 2

        # Animation state
        self.state = "CLOSED"   # CLOSED, OPENING, OPENED
        self.current_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.1   # frame per second

        self.item_data = item_data
        self.text_renderer = text_renderer
        self.can_interact = False
        self.interaction_range = 100

    def update(self, dt, player: Player):
        # 1. Calculate the distance to Player
        center_x = self.world_x + TILE_SIZE//2
        player_cx = player.x + player.width/2

        abs_dist = abs(center_x - player_cx)
        self.can_interact = (abs_dist <= self.interaction_range)

        # 2. Opening chest animation
        if self.state == "OPENING":
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.current_frame += 1

                # if all frames have been rendered, stop at the latest frame
                if self.current_frame >= self.frame_count:
                    self.current_frame = self.frame_count - 1
                    self.state = "OPENED"   # Transform to the opened state

    def interact(self, dropped_items_list, renderer, notification_system):
        """
            Called when Player press F
        """
        if not self.can_interact:
            return
        
        if self.state == "CLOSED":
            # start opening chest
            self.state = "OPENING"
            self.current_frame = 0

            # --- SPAWN ITEM ---
            # Item will spawn immediately when Player open the chest, may be check at frame number 4
            if self.current_frame >= 3: 
                num_items = 1   # may be random.randint(3,5)
                for _ in range(num_items):
                    item_type = random.choice(list(self.item_data.keys()))
                    name, width, height, tex = self.item_data[item_type]
                    
                    item = DroppedItem(
                        self.x + self.scaled_width/2,
                        self.y + self.scaled_heights[self.current_frame]/2,
                        tex,
                        width, height,
                        item_type, name
                    )
                    dropped_items_list.append(item)
                
                print("Chest opening!")

        elif self.state == "OPENED" or (self.state == "OPENING" and self.current_frame >= 3):
            # collecting item
            collected_count = 0
            for item in dropped_items_list:
                if not item.is_collected and item.on_ground:
                    dist = abs(item.x - (self.x + self.scaled_width/2))
                    if dist < self.interaction_range:
                        item.is_collected = True
                        notification_system.add_notification(item.item_type, item.texture)
                        collected_count += 1
            
            if collected_count > 0:
                print(f"Collected {collected_count} items!")
    
    def render(self, renderer, camera: Camera, player: Player):
        # 1. Calculate Source Rect (Cut frame from sprite sheet)
        src_rect = SDL_Rect(
            self.top_left_corner[self.current_frame][0], 
            self.top_left_corner[self.current_frame][1],
            self.frame_width,
            self.frame_heights[self.current_frame]
        )

        # 2 Calculate Destination Rect (Render on windows)
        dst_rect = SDL_Rect(
            int((self.world_x + TILE_SIZE//2 - self.scaled_width//2) - camera.camera.x),
            int(self.grid_y_pos + TILE_SIZE - self.scaled_heights[self.current_frame] - camera.camera.y),
            self.scaled_width,
            self.scaled_heights[self.current_frame]
        )

        # 3. Draw
        sdl2.SDL_RenderCopy(renderer, self.texture, src_rect, dst_rect)

        # 4. Draw UI Text (F character)
        if self.can_interact:
            
            text = ""
            if self.state == "CLOSED":
                text = "Press F to open"
            else:
                # Chỉ hiện collect nếu còn đồ chưa nhặt xung quanh (logic đơn giản: luôn hiện nếu đã mở)
                text = "Press F to collect"

            # Draw small black background
            text_bg_x = player.x - 10
            text_bg_y = player.y + 10

            # sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
            # sdl2. SDL_RenderFillRect(renderer, SDL_Rect(text_bg_x, text_bg_y, 50, 25))

            self.text_renderer.renderer_text(text, text_bg_x, text_bg_y, color=(255,255,0))

