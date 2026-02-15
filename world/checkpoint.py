import sdl2
import sdl2.ext
import math
from sdl2 import SDL_Rect, SDL_RenderCopy, SDL_SetTextureColorMod, SDL_SetTextureAlphaMod
from settings import * 

class CheckpointStatue:
    def __init__(self, x, y, texture, text_renderer):
        self.x = x
        self.y = y
        self.texture = texture
        self.text_renderer = text_renderer

        self.src_rect = SDL_Rect(288, 63, 261, 694)

        # Size to render in the map
        scale_ratio = 2 * TILE_SIZE / 694
        self.width = int(261 * scale_ratio)
        self.height = int(694 * scale_ratio)

        self.is_activate = False
        self.can_interact = False
        self.interact_range = 100

        # Glow effect
        self.glow_timer = 0.0

    def update(self, dt, player):
        center_x = self.x + self.width//2
        center_y = self.y + TILE_SIZE - self.height//2

        player_cx = player.x + player.width//2
        player_cy = player.y + player.height//2

        dst = (center_x - player_cx)**2 + (center_y - player_cy)**2
        self.can_interact = (dst <= self.interact_range**2)

        # Blink effect when activated
        self.glow_timer += dt

    def render(self, renderer, camera):
        dst_rect = SDL_Rect(
            int(self.x + TILE_SIZE//2 - self.width//2 - camera.camera.x),
            int(self.y + TILE_SIZE - self.height - camera.camera.y),
            self.width,
            self.height
        )

        glow_alpha = 200 + int(55 * abs(math.sin(self.glow_timer * 2)))
        if self.is_activate:
            # Màu xanh lam nhè nhẹ (Blue Tint)
            # Hiệu ứng "Hào quang": Alpha thay đổi từ 200 -> 255
            SDL_SetTextureColorMod(self.texture, 0, 191, 255)   # light blue
            SDL_SetTextureAlphaMod(self.texture, glow_alpha)
        else:
            # light red
            SDL_SetTextureColorMod(self.texture, 255, 50, 50)
            SDL_SetTextureAlphaMod(self.texture, glow_alpha)
        
        SDL_RenderCopy(renderer, self.texture, self.src_rect, dst_rect)

        # Draw guilding text
        if self.can_interact and not self.is_activate:
            text = "F: Bless of the Archon"
            text_x = int(dst_rect.x + self.width/2)
            text_y = int(dst_rect.y - 30)

            self.text_renderer.renderer_text(
                text, text_x, text_y,
                color=(255, 255, 0), draw_bg=True, bg_color=(0, 0, 0, 200), radius=8
            )

    def interact(self, player):
        """
            return: saved data of player if successfully activate the statue
        """
        if self.can_interact and not self.is_activate:
            self.is_activate = True

            # Sử dụng \n để tách dòng cho dễ đọc
            text = "By the Statue's blessing, a new respawn point has been set\nand the character's status has been restored."
            
            text_x = int(WINDOW_WIDTH // 2)
            # Dịch lên một chút để cân đối vì giờ text cao hơn
            text_y = int(WINDOW_HEIGHT // 2) - 30 

            # Gọi hàm mới
            self.text_renderer.render_multiline(
                text, text_x, text_y,
                color=(255, 255, 0),       # Chữ vàng
                draw_bg=True,              # Có nền đen
                bg_color=(0, 0, 0, 220),   # Màu nền đen mờ
                radius=10,                 # Bo góc tròn hơn chút
                line_spacing=8             # Khoảng cách giữa 2 dòng là 8px
            )

            # Lưu dữ liệu player
            save_data = player.get_save_data()
            return save_data
    
        return None