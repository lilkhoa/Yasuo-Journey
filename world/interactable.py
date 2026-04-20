import math
import sys
import os
import sdl2.ext
import random
from sdl2 import SDL_Rect
from settings import *

from core.camera import Camera
from entities.base_char import BaseChar

from .map import GameMap
from items.item import DroppedItem

BOX_PUSH_THRESHOLD = 0.2  # Time (second) which the player need to hold before pushing
BOX_PUSH_SPEED_RATIO = 0.7 # Speed of Player while pushing the box (reduce 30% to normal)

class Box:
    # Thêm bộ đếm ID cho Box (Bắt đầu từ 1000 để không trùng với Barrel)
    _next_net_id = 1000

    def __init__(self, x, y, texture):
        self.net_id = Box._next_net_id
        Box._next_net_id += 1
        self.last_pushed_time = 0.0  # [MỚI] Chống giật lùi khi lag mạng

        self.x = x
        self.y = y
        self.initial_x = x  # Store initial position for reset
        self.initial_y = y
        self.width = int(TILE_SIZE)
        self.height = int(TILE_SIZE)
        
        self.texture = texture
        self.vel_y = 0
        self.gravity = GRAVITY
        self.is_falling = True

        # pushing logic
        self.push_timer = 0 # accumulate the time that player has been held
        self.is_being_pushed = False

        # turn on Blend to support fade out effect
        sdl2.SDL_SetTextureBlendMode(self.texture, sdl2.SDL_BLENDMODE_BLEND)

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
        # [SỬA LỖI CÀ GIẬT 1]: Giảm từ từ push_timer thay vì reset về 0 ngay lập tức
        # Nếu Player vô tình bị mất chạm 1-2 frame, lực đẩy vẫn được giữ lại một phần
        if not self.is_being_pushed:
            self.push_timer = max(0, self.push_timer - dt * 2) # reset the timer if the player do not hold

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
        

    def reset(self):
        """Reset box to initial position and state"""
        self.x = self.initial_x
        self.y = self.initial_y
        self.vel_y = 0
        self.is_falling = True
        self.push_timer = 0
        self.is_being_pushed = False

    def push(self, dx, dt, game_map: GameMap, boxes=None):
        """
            Called from the Player when horizontal collision
            dx: the amount of distance which the Player has made
            boxes: list of other interactable objects to check collision against
        """
        self.is_being_pushed = True

        # increase timer
        if self.push_timer < BOX_PUSH_THRESHOLD:
            self.push_timer += dt
            return False, 0 # do not have enough force to push

        # calculate new speed
        push_dx = int(dx * BOX_PUSH_SPEED_RATIO)
        # [MẸO NHỎ]: Đảm bảo thùng luôn nhích ít nhất 1 pixel nếu có lực đẩy, 
        # tránh trường hợp (tốc độ * 0.7) quá nhỏ bị làm tròn về 0 khiến thùng kẹt cứng
        if push_dx == 0 and dx != 0:
            push_dx = 1 if dx > 0 else -1

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
            if sdl2.SDL_HasIntersection(future_rect, tile):
                can_move = False
                break
        
        # [NEW] Check collision with other boxes/barrels
        if can_move and boxes:
            for other in boxes:
                if other is self: continue
                # Basic AABB check
                if sdl2.SDL_HasIntersection(future_rect, other.rect):
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
    _next_net_id = 0  # Class-level counter for unique network IDs

    def __init__(self, x, y, texture, item_data, text_renderer):
        """
            item_data: Dictionary of tuple 
                "red_potion"[type]: (name, width, height, texture)
        """
        self.net_id = Barrel._next_net_id
        Barrel._next_net_id += 1
        self.last_pushed_time = 0.0  # [MỚI] Chống giật lùi khi lag mạng

        self.x = x
        self.y = y
        self.initial_x = x  # Store initial position for reset
        self.initial_y = y
        self.width = BARREL_RENDER_WIDTH
        self.height = BARREL_RENDER_HEIGHT 

        self.texture = texture      # barrel texture
        self.item_data = item_data  # dict of item's texture can be dropped
        self.text_renderer = text_renderer

        self.src_rect = sdl2.SDL_Rect(195, 29, 27, 35)

        self.is_broken = False  
        self.health = 3             # broke after 1 hit
        self.is_fading = False      # mark as fading out
        self.alpha = 255.0          # from 255 (clearest) -> 0 (faded)
        self.fade_speed = 500.0     # fading speed: 500 alpha / second

        self.shake_timer = 0
        self.shake_duration = 0.2   # shaking time of each hit
        self.shake_amplitude = 4    # max 4 pixel deviation to x-axis
        self.shake_speed = 60       # shaking frequency, 60 frames per second
        
        # prevent getting multi-hit from multi-attack frame of Player
        self.invulnerable_timer = 0
        self.invulnerable_duration = 0.4

        # --- PHYSICS PROPERTIES ---
        self.vel_y = 0
        self.gravity = GRAVITY
        self.is_falling = True
        self.push_timer = 0 
        self.is_being_pushed = False

        sdl2.SDL_SetTextureBlendMode(self.texture, sdl2.SDL_BLENDMODE_BLEND)

    @property
    def rect(self):
        return SDL_Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, dt, game_map=None):
        """
            Update shaking animation and fading at each frame
            Also update physics if passed game_map
        """
        if self.is_broken:
            return
        
        # Physics Update
        if game_map:
            self.update_physics(dt, game_map)
        
        # Decrease invulnerable time
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt

        # 1. Update shaking animation
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer <= 0:
                self.shake_timer = 0

        # 2. Update fading out animation
        if self.is_fading: 
            self.alpha -= self.fade_speed * dt
            if self.alpha <= 0:
                self.alpha = 0
                self.is_broken = True
                self.is_fading = False

    def update_physics(self, dt, game_map):
        # 1. gravity
        self.vel_y += self.gravity
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED
        
        self.y += self.vel_y

        # 2. Collide with Map (vertical axis - Y)
        nearby_tiles = game_map.get_tile_rects_around(self.x, self.y, self.width, self.height)
        
        box_rect = self.rect # use property
        self.is_falling = True

        for tile in nearby_tiles:
            if sdl2.SDL_HasIntersection(box_rect, tile):
                if self.vel_y > 0:  # falling and reach the ground surface
                    self.y = tile.y - self.height
                    self.vel_y = 0
                    self.is_falling = False
        
        # reset pushing state
        if not self.is_being_pushed:
            self.push_timer = max(0, self.push_timer - dt * 2)

        self.is_being_pushed = False

    def push(self, dx, dt, game_map, boxes=None):
        """
            Called from the Player when horizontal collision
        """
        if self.is_broken: return False, 0

        self.is_being_pushed = True

        # increase timer
        if self.push_timer < BOX_PUSH_THRESHOLD:
            self.push_timer += dt
            return False, 0 

        # calculate new speed
        push_dx = int(dx * BOX_PUSH_SPEED_RATIO)
        if push_dx == 0 and dx != 0:
            push_dx = 1 if dx > 0 else -1

        # predict new position
        next_x = self.x + push_dx

        if next_x < 0:
            self.x = 0
            return False, 0
        
        if (next_x + self.width) > game_map.width_pixel:
            self.x = game_map.width_pixel - self.width
            return False, 0
        
        future_rect = SDL_Rect(int(next_x), int(self.y), self.width, self.height)

        # check collision with wall
        nearby_tiles = game_map.get_tile_rects_around(int(next_x), int(self.y), self.width, self.height)

        can_move = True
        for tile in nearby_tiles:
            if sdl2.SDL_HasIntersection(future_rect, tile):
                can_move = False
                break

        # [NEW] Check collision with other boxes/barrels
        if can_move and boxes:
            for other in boxes:
                if other is self: continue
                # Basic AABB check
                if sdl2.SDL_HasIntersection(future_rect, other.rect):
                    can_move = False
                    break
                    
        if can_move: 
            self.x = next_x
            return True, push_dx
        else:
            return False, 0

    def get_bounds(self):
        return SDL_Rect(int(self.x), int(self.y), BARREL_RENDER_WIDTH, BARREL_RENDER_HEIGHT)
    
    def render(self, renderer, camera: Camera):
        if self.is_broken:
            return
        
        # --- Calculate shaking position ---
        render_x = self.x
        if self.shake_timer > 0:
            offset_x = math.sin(self.shake_timer * self.shake_speed) * self.shake_amplitude
            render_x += offset_x


        dst_rect = SDL_Rect(
            int(render_x - camera.camera.x),
            int(self.y - camera.camera.y),
            self.width, # Use class width
            self.height # Use class height
        )

        if self.is_fading:
            sdl2.SDL_SetTextureAlphaMod(self.texture, int(self.alpha))

        sdl2.SDL_RenderCopy(renderer, self.texture, self.src_rect, dst_rect)

        if self.is_fading:
           sdl2.SDL_SetTextureAlphaMod(self.texture, 255)

    def take_damage(self, amount, dropped_items_list, renderer):
        if self.is_broken or self.is_fading or self.invulnerable_timer > 0:
            return

        self.health -= amount
        self.invulnerable_timer = self.invulnerable_duration    # start invulerable time
        if self.health > 0:
            self.shake_timer = self.shake_duration
        else:
            self.break_barrel(dropped_items_list, renderer)
        
        print(f"[BARREL] PLayer hits Barrel: Barrel health = {self.health}")

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
                self.x + self.width/2,
                self.y + self.height/2,
                tex,
                width, height,
                self.text_renderer,
                item_type, name
            )
            drop_items_list.append(item)
            
            # Play item pop sound
            from core.sound import get_sound_manager
            sound_manager = get_sound_manager()
            if sound_manager:
                sound_manager.play_sound("item_pop")

        print("Barrel broken!")
    
    def reset(self):
        """Reset barrel to initial position and unbroken state"""
        self.x = self.initial_x
        self.y = self.initial_y
        self.vel_y = 0
        self.is_falling = True
        self.push_timer = 0
        self.is_being_pushed = False
        self.is_broken = False
        self.health = 3
        self.is_fading = False
        self.alpha = 255.0
        self.shake_timer = 0
        self.invulnerable_timer = 0

class Chest:
    _next_net_id = 1

    def __init__(self, world_x, grid_y_pos, sprite_sheet, item_data, text_renderer):
        '''
            real_x, real_y
        '''
        self.world_x = world_x
        self.grid_y_pos = grid_y_pos

        self.net_id = Chest._next_net_id
        Chest._next_net_id += 1

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

        self.has_spawned_items = False
        
        # Chest sound tracking
        self.chest_sound_channel = -1
        self.chest_sound_timer = 0.0

    def update(self, dt, player: BaseChar, dropped_items_list, renderer):
        # Update chest sound timer and stop after 3 seconds
        if self.chest_sound_timer > 0:
            self.chest_sound_timer -= dt
            if self.chest_sound_timer <= 0 and self.chest_sound_channel != -1:
                import sdl2.sdlmixer
                sdl2.sdlmixer.Mix_HaltChannel(self.chest_sound_channel)
                self.chest_sound_channel = -1
        
        # 1. Calculate the distance to Player
        center_x = self.world_x + TILE_SIZE//2
        center_y = self.grid_y_pos + TILE_SIZE - self.scaled_heights[0]//2
        player_cx = player.x + player.width/2
        player_cy = player.y + player.height/2

        dist = (center_x - player_cx)**2 + (center_y - player_cy)**2
        self.can_interact = (dist <= self.interaction_range**2)

        # 2. Opening chest animation
        if self.state == "OPENING":
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.current_frame += 1
                
                # spawn item logic, check every frame
                if self.current_frame >= 3 and not self.has_spawned_items:
                    num_items = 1
                    for _ in range(num_items):
                        item_type = random.choice(list(self.item_data.keys()))
                        name, width, height, tex = self.item_data[item_type]

                        item = DroppedItem(
                            self.world_x + TILE_SIZE // 2,
                            self.grid_y_pos + TILE_SIZE - self.scaled_heights[0]//2 - 5, # 5 pixels higher
                            tex, 
                            width, height, 
                            self.text_renderer,
                            item_type, name
                        )

                        dropped_items_list.append(item)
                    
                    self.has_spawned_items = True
                    # Play item pop sound
                    from core.sound import get_sound_manager
                    sound_manager = get_sound_manager()
                    if sound_manager:
                        sound_manager.play_sound("item_pop")
                    print("Chest items spawned!")

                # if all frames have been rendered, stop at the latest frame
                if self.current_frame >= self.frame_count:
                    self.current_frame = self.frame_count - 1
                    self.state = "OPENED"   # Transform to the opened state

    def interact(self):
        """
            Called when Player press F
        """
        if not self.can_interact:
            return False
        
        if self.state == "CLOSED":
            # start opening chest
            self.state = "OPENING"
            self.current_frame = 0
            self.has_spawned_items = False
            # Play chest open sound (import sound manager)
            from core.sound import get_sound_manager
            sound_manager = get_sound_manager()
            if sound_manager:
                self.chest_sound_channel = sound_manager.play_sound("chest_open")
                self.chest_sound_timer = 3.0  # Stop after 3 seconds
            print("Chest opening!")

            return True
    
    def force_open(self):
        """Force chest to open (for network sync) without checking interaction conditions."""
        if self.state == "CLOSED":
            self.state = "OPENING"
            self.current_frame = 0
            self.has_spawned_items = False
            from core.sound import get_sound_manager
            sound_manager = get_sound_manager()
            if sound_manager:
                self.chest_sound_channel = sound_manager.play_sound("chest_open")
                self.chest_sound_timer = 3.0
            print(f"Chest {self.net_id} forcibly opened!")
            return True
        return False
    
    def reset(self):
        """Reset chest to initial closed state"""
        self.state = "CLOSED"
        self.current_frame = 0
        self.anim_timer = 0
        self.has_spawned_items = False
        self.can_interact = False
        # Stop any playing chest sound
        if self.chest_sound_channel != -1:
            import sdl2.sdlmixer
            sdl2.sdlmixer.Mix_HaltChannel(self.chest_sound_channel)
            self.chest_sound_channel = -1
        self.chest_sound_timer = 0.0
    
    def render(self, renderer, camera: Camera, player: BaseChar):
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
                text = "F: Open"

            # Draw small black background
            text_bg_x = player.x + player.width//2 - camera.camera.x
            text_bg_y = player.y + 10 - camera.camera.y

            # sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
            # sdl2. SDL_RenderFillRect(renderer, SDL_Rect(text_bg_x, text_bg_y, 50, 25))

            self.text_renderer.renderer_text(
                text, 
                text_bg_x, 
                text_bg_y, 
                color=(255, 255, 0),
                draw_bg=True,
                bg_color=(0, 0, 0, 200),
                radius=8
            )
