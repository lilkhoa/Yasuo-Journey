import sdl2
import sdl2.ext
import sdl2.sdlmixer
import math
from sdl2 import SDL_Rect, SDL_RenderCopy, SDL_SetTextureColorMod, SDL_SetTextureAlphaMod
from settings import * 

# Định nghĩa màu
COLOR_RED = (255, 100, 100)
COLOR_BLUE = (100, 150, 255)

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

        self.state = "INACTIVE" # Các trạng thái: "INACTIVE", "ACTIVATING", "ACTIVE"
        self.can_interact = False
        self.interact_range = 100

        # Logic Animation & Timer
        self.activation_timer = 0.0
        self.activation_duration = 2.0  # Thời gian chuyển màu (2 giây)
        self.current_color = COLOR_RED  # Màu hiện tại (bắt đầu là đỏ)

        # Glow effect
        self.glow_timer = 0.0

        # [MỚI] Timer cho Thông báo (Notification)
        self.notification_timer = 0.0  # Thời gian hiển thị thông báo còn lại

        # Âm thanh (Sẽ được gán từ game.py)
        self.sound_click = None    # Âm thanh ngắn khi ấn F
        self.sound_process = None  # Âm thanh dài 2s

    def set_sounds(self, sound_click, sound_process):
        """Nhận âm thanh từ Game Loop"""
        self.sound_click = sound_click
        self.sound_process = sound_process

    def update(self, dt, player):
        # 1. Update Notification Timer (Giảm dần thời gian hiển thị chữ)
        if self.notification_timer > 0:
            self.notification_timer -= dt

        center_x = self.x + TILE_SIZE//2
        center_y = self.y + TILE_SIZE - self.height//2

        player_cx = player.x + player.width//2
        player_cy = player.y + player.height//2

        dst = (center_x - player_cx)**2 + (center_y - player_cy)**2
        self.can_interact = (dst <= self.interact_range**2)

        # 2. Xử lý Logic Animation chuyển màu (ACTIVATING)
        if self.state == "ACTIVATING":
            self.activation_timer += dt
            
            # Tính toán tiến độ (t đi từ 0.0 đến 1.0)
            t = min(self.activation_timer / self.activation_duration, 1.0)
            
            # Nội suy màu (Linear Interpolation - Lerp) từ Đỏ sang Xanh
            r = int(COLOR_RED[0] + (COLOR_BLUE[0] - COLOR_RED[0]) * t)
            g = int(COLOR_RED[1] + (COLOR_BLUE[1] - COLOR_RED[1]) * t)
            b = int(COLOR_RED[2] + (COLOR_BLUE[2] - COLOR_RED[2]) * t)
            self.current_color = (r, g, b)

            # Nếu chạy hết 2 giây -> Chuyển sang ACTIVE
            if t >= 1.0:
                self.state = "ACTIVE"
        
        # 3. Hiệu ứng nhấp nháy khi đã xong (ACTIVE)
        elif self.state == "ACTIVE" or self.state == "INACTIVE":
            self.glow_timer += dt

    def render(self, renderer, camera):
        dst_rect = SDL_Rect(
            int(self.x + TILE_SIZE//2 - self.width//2 - camera.camera.x),
            int(self.y + TILE_SIZE - self.height - camera.camera.y),
            self.width, self.height
        )

        r, g, b = self.current_color
        if self.state == "ACTIVE":
            glow_alpha = 200 + int(55 * abs(math.sin(self.glow_timer * 2)))
            SDL_SetTextureColorMod(self.texture, r, g, b)
            SDL_SetTextureAlphaMod(self.texture, glow_alpha)
        else:
            SDL_SetTextureColorMod(self.texture, r, g, b)
            SDL_SetTextureAlphaMod(self.texture, 255)
        
        SDL_RenderCopy(renderer, self.texture, self.src_rect, dst_rect)
        
        # Reset màu
        SDL_SetTextureColorMod(self.texture, 255, 255, 255)
        SDL_SetTextureAlphaMod(self.texture, 255)

        # --- PHẦN UI ---
        
        # 1. Vẽ chữ "Press F" (Chỉ hiện khi chưa kích hoạt và đứng gần)
        if self.can_interact and self.state == "INACTIVE":
            text = "F: Bless of the Archon"
            text_x = int(dst_rect.x + self.width/2)
            text_y = int(dst_rect.y - 30)
            self.text_renderer.renderer_text(
                text, text_x, text_y,
                color=(255, 255, 0), draw_bg=True, bg_color=(0, 0, 0, 200), radius=8
            )

        # 2. [FIX LỖI HIỂN THỊ] Vẽ Thông báo khi timer > 0
        # Phần này PHẢI nằm trong render, không được nằm trong interact
        if self.notification_timer > 0:
            text = "By the Statue's blessing, a new respawn point has been set and the character's status has been restored."
            
            # Tính Alpha để chữ mờ dần khi sắp hết giờ (0.5 giây cuối)
            alpha = 220
            if self.notification_timer < 0.5:
                alpha = int(220 * (self.notification_timer / 0.5))
            
            text_x = int(WINDOW_WIDTH // 2)
            text_y = int(WINDOW_HEIGHT // 5) - 30 

            self.text_renderer.render_multiline(
                text, text_x, text_y,
                color=(0, 0, 0), 
                draw_bg=True, 
                bg_color=(255, 255, 255, alpha),
                radius=10, 
                line_spacing=8
            )

    def interact(self, player):
        """
            return: saved data of player if successfully activate the statue
        """
        if self.can_interact and self.state == "INACTIVE":
            self.state = "ACTIVATING"
            self.activation_timer = 0.0
            
            # [MỚI] Kích hoạt Timer hiển thị thông báo trong 4 giây
            self.notification_timer = 5.0 
            
            # Phát âm thanh chồng nhau (Layering) -> Tạo hiệu ứng hay hơn
            # [FIX LỖI ÂM THANH] Dùng Mix_PlayChannel thay vì .play()
            if self.sound_click:
                sdl2.sdlmixer.Mix_PlayChannel(-1, self.sound_click, 0)
            if self.sound_process:
                sdl2.sdlmixer.Mix_PlayChannel(-1, self.sound_process, 0)

            return player.get_save_data()
    
        return None