import sdl2
from enum import Enum
import random
import time
from sdl2 import SDL_Rect, SDL_RenderCopy
from settings import *
from world.map import GameMap
from core.camera import Camera
from ui.item_notification import ItemNotificationSystem

# --- 1. ĐỊNH NGHĨA ITEM TYPE & CATEGORY TẠI ĐÂY ---
class ItemType(Enum):
    COIN = 0            
    HEALTH_POTION = 1   
    TEAR = 2            
    GREAVES = 3         
    BLOODTHIRSTER = 4   
    INFINITY_EDGE = 5   
    THORNMAIL = 6       
    HOURGLASS = 7       

class ItemCategory(Enum):
    CURRENCY = 0
    CONSUMABLE = 1
    EQUIPMENT = 2

# Đăng ký danh mục cho từng Item
ITEM_REGISTRY = {
    ItemType.COIN:          ItemCategory.CURRENCY,
    ItemType.HEALTH_POTION: ItemCategory.CONSUMABLE,
    ItemType.HOURGLASS:     ItemCategory.CONSUMABLE, # Hourglass là Active item -> xếp vào Consumable để bấm số dùng
    ItemType.TEAR:          ItemCategory.CONSUMABLE,
    ItemType.GREAVES:       ItemCategory.EQUIPMENT,
    ItemType.BLOODTHIRSTER: ItemCategory.EQUIPMENT,
    ItemType.INFINITY_EDGE: ItemCategory.EQUIPMENT,
    ItemType.THORNMAIL:     ItemCategory.EQUIPMENT,
}

class DroppedItem:
    collected_count = 0
    _next_net_id = 1000  # Start high to avoid conflicts with entities

    def __init__(self, x, y, texture, width, height, text_renderer, item_type, item_name):
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
        self.interact_range = 70
        self.can_interact = False 

        self.text_renderer = text_renderer
        
        # --- NETWORK SUPPORT ---
        # Unique identifier for network synchronization
        self.net_id = DroppedItem._next_net_id
        DroppedItem._next_net_id += 1
        
        # Pickup delay prevents immediate re-collection on spawn or drop
        self.spawn_time = time.time()
        self.pickup_delay = 0.0  # In seconds (0 = can pickup immediately)

    def update(self, dt, game_map: GameMap, player):
        if self.is_collected:
            return      # logic UI will do later
        
        # Check the distance for the interaction
        center_x = self.x + self.width/2
        center_y = self.y + self.height/2
        player_cx = player.x + player.width/2
        player_cy = player.y + player.height/2

        dist = (center_x - player_cx)**2 + (center_y - player_cy)**2
        self.can_interact = (dist <= self.interact_range**2)
        
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
        item_rect = SDL_Rect(
            int(self.x), 
            int(self.y), 
            self.width, 
            self.height
        )
        nearby_tiles = game_map.get_tile_rects_around(
            self.x, self.y, 
            self.width, self.height
        )

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
                    
    def render(self, renderer, camera: Camera, player):
        if self.is_collected:
            return
        
        dst_rect = SDL_Rect(
            int(self.x - camera.camera.x),
            int(self.y - camera.camera.y),
            self.width,
            self.height
        )

        SDL_RenderCopy(renderer, self.texture, None, dst_rect)

        if self.can_interact:

            text = ""
            if not self.is_collected:
                text = f"F: {self.item_name}"

            # Draw small black background
            player_cx = player.x + player.width//2 - camera.camera.x
            text_bg_y = player.y + 10 - camera.camera.y

            # sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
            # sdl2. SDL_RenderFillRect(renderer, SDL_Rect(text_bg_x, text_bg_y, 50, 25))

            self.text_renderer.renderer_text(
                text, 
                player_cx, 
                text_bg_y, 
                color=(255, 255, 0),
                draw_bg=True,
                bg_color=(0, 0, 0, 200),
                radius=8
            )

    def interact(self, notification_system: ItemNotificationSystem, player, game_client=None):
        """
        Handle item pickup interaction.
        
        Args:
            notification_system: ItemNotificationSystem for UI feedback
            player: Player object attempting pickup
            game_client: GameClient instance (if in network mode)
            
        Returns:
            True if pickup was processed, False otherwise
        """
        if self.is_collected:
            return False
        
        # Check pickup delay - item must wait this many seconds after spawn
        elapsed_time = time.time() - self.spawn_time
        if elapsed_time < self.pickup_delay:
            return False  # Still in pickup delay window, cannot collect
        
        center_x = self.x + self.width/2
        center_y = self.y + self.height/2
        player_cx = player.x + player.width/2
        player_cy = player.y + player.height/2

        dist = (center_x - player_cx)**2 + (center_y - player_cy)**2
        if dist <= self.interact_range**2:
            # Determine item category using ITEM_REGISTRY
            category = ITEM_REGISTRY.get(self.item_type)
            
            # --- NETWORK MODE: Send pickup request to server ---
            if game_client and game_client.is_connected():
                if getattr(self, 'pickup_requested', False):
                    return False
                self.pickup_requested = True
                player_id = getattr(game_client, 'player_id', 1)
                game_client.send_pickup_request(self.net_id, player_id)
                return True  # Pickup interaction was processed
            
            # --- OFFLINE MODE: Collect immediately ---
            self.is_collected = True
            notification_system.add_notification(self.item_name, self.texture)
            
            # Handle different item types
            if category == ItemCategory.CURRENCY:
                # Instant pickup for currency
                player.collect_item(self.item_type)
            elif category == ItemCategory.EQUIPMENT:
                # Instant apply for equipment
                player.collect_item(self.item_type)
            elif category == ItemCategory.CONSUMABLE:
                # Add to inventory for consumables
                player.collect_item(self.item_type)
            
            DroppedItem.collected_count += 1
            if DroppedItem.collected_count > 0:
                print(f"[Items] Collected {DroppedItem.collected_count} items! (Item: {self.item_name})")
            
            return True
        
        return False
        