import sdl2
import sdl2.ext
import os
from enum import Enum
import math

class ItemType(Enum):
    COIN = 0            
    TEAR = 1            
    HEALTH_POTION = 2   
    GREAVES = 3         
    BLOODTHIRSTER = 4   
    INFINITY_EDGE = 5   
    THORNMAIL = 6       
    HOURGLASS = 7       

class GameItem:
    def __init__(self, x, y, item_type, texture, renderer, text_renderer, name="Item"):
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.item_type = item_type
        self.texture = texture
        self.renderer = renderer
        self.text_renderer = text_renderer
        self.name = name
        self.active = True
        self.can_interact = False
        self.interact_range = 60
        self.base_y = y
        self.float_timer = 0
        
    def update(self, dt, player):
        self.float_timer += dt * 3
        self.y = self.base_y + (math.sin(self.float_timer) * 5)
        item_cx = self.x + self.width / 2
        player_cx = player.x + 64 
        dist = abs(item_cx - player_cx)
        self.can_interact = (dist < self.interact_range) and self.active

    def render(self, camera_x, camera_y, player):
        if not self.active: return
        
        dst_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        sdl2.SDL_RenderCopy(self.renderer, self.texture, None, dst_rect)

        if self.can_interact and self.text_renderer:
            text = f"Press F: {self.name}"
            text_x = int(self.x - camera_x - 20)
            text_y = int(self.y - camera_y - 30)
            
            # Kiểm tra tên hàm render text
            if hasattr(self.text_renderer, 'renderer_text'):
                self.text_renderer.renderer_text(text, text_x, text_y, color=(255, 255, 0), draw_bg=True, bg_color=(0, 0, 0, 180), radius=5)
            elif hasattr(self.text_renderer, 'render_text'):
                self.text_renderer.render_text(text, text_x, text_y, color=(255, 255, 0))

    def interact(self, player):
        if self.can_interact and self.active:
            print(f"Collected {self.name}")
            self.active = False
            return self.item_type
        return None

class ItemManager:
    def __init__(self, renderer, text_renderer):
        self.renderer = renderer
        self.text_renderer = text_renderer
        self.items = []
        self.textures = {}
        self._load_textures()

    def _load_textures(self):
        # --- [FIX PATH CỨNG] ---
        # Lấy đường dẫn tuyệt đối của file items/item.py
        current_file_path = os.path.abspath(__file__)
        # Lấy thư mục chứa file này (items/)
        items_dir = os.path.dirname(current_file_path)
        # Lấy thư mục gốc dự án (thư mục cha của items/)
        PROJECT_ROOT = os.path.dirname(items_dir)
        
        # Đường dẫn tuyệt đối tới assets
        ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
        
        # Đường dẫn cụ thể
        map_items_path = os.path.join(ASSETS_DIR, "Map", "items")
        lol_equip_path = os.path.join(ASSETS_DIR, "Map", "LOL_Equipment")
        
        print(f"--- DEBUG ITEM PATHS ---")
        print(f"Project Root: {PROJECT_ROOT}")
        print(f"Assets Dir: {ASSETS_DIR}")

        data = {
            ItemType.COIN: (os.path.join(map_items_path, "Golden Coin.png"), "Coin"),
            ItemType.TEAR: (os.path.join(lol_equip_path, "64x64_Tear_of_the_Goddess.png"), "Tear of Goddess"),
            ItemType.HEALTH_POTION: (os.path.join(lol_equip_path, "64x64_Health_Potion.png"), "Health Potion"),
            ItemType.GREAVES: (os.path.join(lol_equip_path, "64x64_Berserkers_Greaves.png"), "Berserker Greaves"),
            ItemType.BLOODTHIRSTER: (os.path.join(lol_equip_path, "64x64_Bloodthirster.png"), "Bloodthirster"),
            ItemType.INFINITY_EDGE: (os.path.join(lol_equip_path, "64x64_Infinity_Edge.png"), "Infinity Edge"),
            ItemType.THORNMAIL: (os.path.join(lol_equip_path, "64x64_Thornmail.png"), "Thornmail"),
            ItemType.HOURGLASS: (os.path.join(lol_equip_path, "64x64_Zhonyas_Hourglass.png"), "Zhonya's Hourglass"),
        }
        
        factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=self.renderer)
        self.item_info = {} 

        for i_type, (filepath, name) in data.items():
            self.item_info[i_type] = name
            
            # Kiểm tra file tồn tại
            if os.path.exists(filepath):
                try:
                    sprite = factory.from_image(filepath)
                    self.textures[i_type] = sprite.texture
                    print(f"[OK] Loaded: {name}")
                except Exception as e:
                    print(f"[ERROR] Failed to load image {filepath}: {e}")
                    self.textures[i_type] = factory.from_color((255,0,255), (32,32)).texture
            else:
                print(f"[MISSING] File not found: {filepath}")
                # Fallback: Màu đỏ để báo lỗi
                self.textures[i_type] = factory.from_color((255,0,0), (32,32)).texture

    def spawn_item(self, x, y, item_type):
        if item_type not in self.textures: return
        name = self.item_info.get(item_type, "Unknown Item")
        item = GameItem(x, y, item_type, self.textures[item_type], 
                        self.renderer.sdlrenderer, self.text_renderer, name)
        self.items.append(item)

    def update(self, dt, player):
        for item in self.items:
            item.update(dt, player)
        self.items = [i for i in self.items if i.active]

    def render(self, camera_x, camera_y, player):
        for item in self.items:
            item.render(camera_x, camera_y, player)

    def handle_interact_key(self, player):
        for item in self.items:
            if item.can_interact:
                item_type = item.interact(player)
                if item_type:
                    self.apply_effect(player, item_type)
                    return True
        return False

    def apply_effect(self, player, item_type):
        if item_type == ItemType.COIN:
            print(">> Received 10 Gold")
        elif item_type == ItemType.TEAR:
            player.max_stamina += 50
            player.stamina = player.max_stamina
            print(">> Max Stamina Increased!")
        elif item_type == ItemType.HEALTH_POTION:
            player.hp = min(player.hp + 100, player.max_hp)
            print(">> Healed 100 HP")
        elif item_type == ItemType.GREAVES:
            player.move_speed_bonus += 50
            print(">> Speed Increased!")
        elif item_type == ItemType.BLOODTHIRSTER:
            player.lifesteal_ratio += 0.10
            player.base_attack_damage += 10
            player.update_stats()
            print(">> Lifesteal & Damage Increased!")
        elif item_type == ItemType.INFINITY_EDGE:
            player.base_attack_damage += 50
            player.update_stats()
            print(">> Huge Damage Boost!")
        elif item_type == ItemType.THORNMAIL:
            player.damage_reduction += 0.10
            player.max_hp += 100
            player.hp += 100
            print(">> Armor & HP Increased!")
        elif item_type == ItemType.HOURGLASS:
            player.activate_star_skill(duration=5.0)
            print(">> Invincible for 5s!")