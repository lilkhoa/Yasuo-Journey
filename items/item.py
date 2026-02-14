import sdl2
import sdl2.ext
import os
from enum import Enum
import math

class ItemType(Enum):
    HEALTH_POTION = 0   # Hồi máu
    STAMINA_POTION = 1  # Hồi nội năng
    STR_POTION = 2      # Thuốc kích dục (Dame tạm thời)
    INFINITY_SWORD = 3  # Vô cực kiếm (Dame vĩnh viễn)
    STAR = 4            # Ngôi sao (Bất tử)

class GameItem:
    def __init__(self, x, y, item_type, texture, renderer):
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.item_type = item_type
        self.texture = texture
        self.renderer = renderer
        self.active = True
        
        # Hiệu ứng bay bổng (Floating animation)
        self.base_y = y
        self.float_timer = 0
        self.float_speed = 0.05
        self.float_range = 5

    def update(self, dt):
        # Tạo hiệu ứng vật phẩm nhấp nhô
        self.float_timer += self.float_speed * (dt * 60) # Chuẩn hóa theo 60 FPS
        self.y = self.base_y + (math.sin(self.float_timer) * self.float_range)

    def render(self, camera_x, camera_y):
        if not self.active: return
        
        dst_rect = sdl2.SDL_Rect(
            int(self.x - camera_x),
            int(self.y - camera_y),
            self.width,
            self.height
        )
        sdl2.SDL_RenderCopy(self.renderer, self.texture, None, dst_rect)

    def get_rect(self):
        return sdl2.SDL_Rect(int(self.x), int(self.y), self.width, self.height)

class ItemManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.items = []
        self.textures = {}
        self._load_textures()

    def _load_textures(self):
        # Đường dẫn: assets/Items/
        base_path = os.path.join("assets", "Items")
        
        # Mapping loại item -> tên file ảnh
        filenames = {
            ItemType.HEALTH_POTION: "health_potion.png",
            ItemType.STAMINA_POTION: "stamina_potion.png",
            ItemType.STR_POTION: "str_potion.png",
            ItemType.INFINITY_SWORD: "sword.png",
            ItemType.STAR: "star.png"
        }
        
        # Màu fallback nếu chưa có ảnh
        colors = {
            ItemType.HEALTH_POTION: (255, 0, 0),    # Đỏ
            ItemType.STAMINA_POTION: (0, 0, 255),   # Xanh
            ItemType.STR_POTION: (128, 0, 128),     # Tím
            ItemType.INFINITY_SWORD: (255, 165, 0), # Cam
            ItemType.STAR: (255, 255, 0)            # Vàng
        }

        factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=self.renderer)

        for i_type, filename in filenames.items():
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    sprite = factory.from_image(filepath)
                    self.textures[i_type] = sprite.texture
                except Exception as e:
                    print(f"[ItemManager] Lỗi load {filename}: {e}")
                    # Fallback color
                    sprite = factory.from_color(colors[i_type], size=(32, 32))
                    self.textures[i_type] = sprite.texture
            else:
                # Tạo ảnh màu fallback
                sprite = factory.from_color(colors[i_type], size=(32, 32))
                self.textures[i_type] = sprite.texture

    def spawn_item(self, x, y, item_type):
        item = GameItem(x, y, item_type, self.textures[item_type], self.renderer.sdlrenderer)
        self.items.append(item)
        return item

    def update(self, dt):
        for item in self.items:
            item.update(dt)

    def render(self, camera_x, camera_y):
        for item in self.items:
            item.render(camera_x, camera_y)

    def check_collision(self, player):
        player_rect = player.get_hitbox()
        
        for item in self.items[:]:
            if sdl2.SDL_HasIntersection(player_rect, item.get_rect()):
                self.apply_effect(player, item.item_type)
                self.items.remove(item)

    def apply_effect(self, player, item_type):
        if item_type == ItemType.HEALTH_POTION:
            heal = 50
            player.hp = min(player.hp + heal, player.max_hp)
            print(f"[Item] +{heal} HP")
            
        elif item_type == ItemType.STAMINA_POTION:
            stamina = 100
            player.stamina = min(player.stamina + stamina, player.max_stamina)
            print(f"[Item] +{stamina} Stamina")
            
        elif item_type == ItemType.STR_POTION:
            # Tăng 50% dame trong 10 giây
            player.apply_buff("damage_boost", duration=10.0, value=1.5)
            print("[Item] Damage Boosted (10s)!")
            
        elif item_type == ItemType.INFINITY_SWORD:
            # Tăng 20 dame vĩnh viễn
            player.base_attack_damage += 20
            player.update_stats()
            print("[Item] Permanent Damage +20!")
            
        elif item_type == ItemType.STAR:
            # Bất tử 5 giây
            player.activate_star_skill(duration=5.0)
            print("[Item] Invincible (5s)!")