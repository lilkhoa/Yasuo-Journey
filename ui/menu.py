import sdl2
import sdl2.ext
import os
import ctypes
import settings

# Màu sắc
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
GREEN = (50, 205, 50)
BLACK = (0, 0, 0)
OVERLAY_COLOR = (0, 0, 0, 150)

class MenuState:
    MAIN_MENU = 0
    OPTION = 1
    ABOUT = 2
    GAME_PLAYING = 3
    PAUSE = 4

class GameMenu:
    def __init__(self, renderer, window_width, window_height):
        self.renderer = renderer
        self.width = window_width
        self.height = window_height
        
        # Load Font
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(base_dir, "..", "assets", "fonts", "arial.ttf")
        
        try:
            self.title_font = sdl2.ext.FontManager(font_path, size=40, color=WHITE)
            self.menu_font = sdl2.ext.FontManager(font_path, size=20, color=WHITE)
            self.info_font = sdl2.ext.FontManager(font_path, size=16, color=WHITE)
        except:
            self.title_font = None
            self.menu_font = None
            self.info_font = None

        self.state = MenuState.MAIN_MENU
        self.selected_index = 0
        
        # --- DATA MENU ---
        self.main_options = ["NEW GAME", "OPTION", "ABOUT", "EXIT"]
        self.pause_options = ["Resume", "Exit to Main Menu"]
        
        # Option Data
        self.option_items = ["Music Volume", "SFX Volume", "Back"]
        self.music_volume = settings.MUSIC_VOLUME # 0 - 100
        self.sfx_volume = settings.SFX_VOLUME   # 0 - 100

        # About Data (Hướng dẫn chơi)
        self.controls_text = [
            ("Arrow Keys", "Move"),
            ("Shift", "Run"),
            ("Space", "Jump"),
            ("A", "Attack"),
            ("Q, W, E", "Skills"),
            ("Ctrl + 6", "Show Mastery"),
            ("F", "Interact (Pick up / Chest)"),
            ("Esc", "Pause / Back")
        ]
        
        # Load background layers
        self.bg_textures = []
        self.bg_scroll_speeds = [0.05, 0.15, 0.25]  # Different speeds for parallax effect
        self.bg_offsets = [0.0, 0.0, 0.0]  # Current scroll positions
        
        assets_dir = os.path.join(base_dir, "..", "assets")
        for i in range(1, 4):
            bg_path = os.path.join(assets_dir, "Map", "background", f"background_layer_{i}.png")
            try:
                bg_surface = sdl2.ext.load_image(bg_path)
                bg_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, bg_surface)
                self.bg_textures.append(bg_texture)
                sdl2.SDL_FreeSurface(bg_surface)
            except Exception as e:
                print(f"[MENU] Warning: Could not load background layer {i}: {e}")
                self.bg_textures.append(None)
        
        # Load placeholder cloth image
        self.placeholder_texture = None
        placeholder_path = os.path.join(assets_dir, "Menu", "placeholder.png")
        try:
            placeholder_surface = sdl2.ext.load_image(placeholder_path)
            self.placeholder_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, placeholder_surface)
            sdl2.SDL_FreeSurface(placeholder_surface)
            
            # Get placeholder dimensions
            w, h = ctypes.c_int(), ctypes.c_int()
            sdl2.SDL_QueryTexture(self.placeholder_texture, None, None, ctypes.byref(w), ctypes.byref(h))
            self.placeholder_w = w.value
            self.placeholder_h = h.value
        except Exception as e:
            print(f"[MENU] Warning: Could not load placeholder: {e}")
            self.placeholder_w = 400
            self.placeholder_h = 400

        # Load prefix
        prefix_path = os.path.join(assets_dir, "Menu", "sword.png")
        try:
            prefix_surface = sdl2.ext.load_image(prefix_path)
            self.prefix_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, prefix_surface)
            sdl2.SDL_FreeSurface(prefix_surface)
            
            # Get prefix dimensions
            w, h = ctypes.c_int(), ctypes.c_int()
            sdl2.SDL_QueryTexture(self.prefix_texture, None, None, ctypes.byref(w), ctypes.byref(h))
            self.prefix_w = w.value
            self.prefix_h = h.value
        except Exception as e:
            print(f"[MENU] Warning: Could not load prefix image: {e}")
            self.prefix_texture = None
            self.prefix_w = 32
            self.prefix_h = 32

    def get_volume(self):
        return self.music_volume, self.sfx_volume

    def handle_input(self, events):
        action = None
        
        for event in events:
            if event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                
                # --- MAIN MENU ---
                if self.state == MenuState.MAIN_MENU:
                    if key == sdl2.SDLK_UP:
                        self.selected_index = (self.selected_index - 1) % len(self.main_options)
                    elif key == sdl2.SDLK_DOWN:
                        self.selected_index = (self.selected_index + 1) % len(self.main_options)
                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER:
                        choice = self.main_options[self.selected_index]
                        if choice == "NEW GAME":
                            self.state = MenuState.GAME_PLAYING
                            return "START_GAME"
                        elif choice == "OPTION":
                            self.state = MenuState.OPTION
                            self.selected_index = 0
                        elif choice == "ABOUT":
                            self.state = MenuState.ABOUT
                        elif choice == "EXIT":
                            return "QUIT_GAME"

                # --- PAUSE MENU ---
                elif self.state == MenuState.PAUSE:
                    if key == sdl2.SDLK_UP:
                        self.selected_index = (self.selected_index - 1) % len(self.pause_options)
                    elif key == sdl2.SDLK_DOWN:
                        self.selected_index = (self.selected_index + 1) % len(self.pause_options)
                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER:
                        choice = self.pause_options[self.selected_index]
                        if choice == "Resume":
                            self.state = MenuState.GAME_PLAYING
                            return "RESUME_GAME"
                        elif choice == "Exit to Main Menu":
                            self.state = MenuState.MAIN_MENU
                            self.selected_index = 0
                            return "BACK_TO_MAIN"
                    elif key == sdl2.SDLK_ESCAPE:
                        self.state = MenuState.GAME_PLAYING
                        return "RESUME_GAME"

                # --- OPTION MENU (Chỉnh âm thanh) ---
                elif self.state == MenuState.OPTION:
                    if key == sdl2.SDLK_UP:
                        self.selected_index = (self.selected_index - 1) % len(self.option_items)
                    elif key == sdl2.SDLK_DOWN:
                        self.selected_index = (self.selected_index + 1) % len(self.option_items)
                    
                    # Chỉnh Volume Trái/Phải
                    elif key == sdl2.SDLK_LEFT:
                        if self.selected_index == 0: # Music
                            self.music_volume = max(0, self.music_volume - 10)
                            settings.MUSIC_VOLUME = self.music_volume
                            return "UPDATE_VOLUME"
                        elif self.selected_index == 1: # SFX
                            self.sfx_volume = max(0, self.sfx_volume - 10)
                            settings.SFX_VOLUME = self.sfx_volume
                            return "UPDATE_VOLUME"
                            
                    elif key == sdl2.SDLK_RIGHT:
                        if self.selected_index == 0: # Music
                            self.music_volume = min(100, self.music_volume + 10)
                            settings.MUSIC_VOLUME = self.music_volume
                            return "UPDATE_VOLUME"
                        elif self.selected_index == 1: # SFX
                            self.sfx_volume = min(100, self.sfx_volume + 10)
                            settings.SFX_VOLUME = self.sfx_volume
                            return "UPDATE_VOLUME"

                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER or key == sdl2.SDLK_ESCAPE:
                        # Nếu chọn Back hoặc bấm Esc -> Về Main Menu
                        if self.selected_index == 2 or key == sdl2.SDLK_ESCAPE:
                            self.state = MenuState.MAIN_MENU
                            self.selected_index = 1 # Trỏ lại vào nút Option

                # --- ABOUT MENU ---
                elif self.state == MenuState.ABOUT:
                    if key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER or key == sdl2.SDLK_ESCAPE:
                        self.state = MenuState.MAIN_MENU
                        self.selected_index = 2 # Trỏ lại vào nút About

                # --- GAME PLAYING ---
                elif self.state == MenuState.GAME_PLAYING:
                    if key == sdl2.SDLK_ESCAPE:
                        self.state = MenuState.PAUSE
                        self.selected_index = 0
                        return "PAUSE_GAME"
        
        return action
    
    def update(self, dt=0.016):
        """Update background animation"""
        for i in range(len(self.bg_offsets)):
            self.bg_offsets[i] += self.bg_scroll_speeds[i]
            # Reset offset when it goes beyond window width
            if self.bg_offsets[i] >= self.width:
                self.bg_offsets[i] = 0

    def render(self):
        if self.state == MenuState.GAME_PLAYING:
            return 

        # Draw animated background for all menu states except pause
        if self.state != MenuState.PAUSE:
            self._draw_background()
        else:
            self._draw_overlay()

        # Render nội dung
        if self.state == MenuState.MAIN_MENU:
            self._render_main_menu()
        elif self.state == MenuState.PAUSE:
            self._render_list("PAUSE", self.pause_options)
        elif self.state == MenuState.OPTION:
            self._render_options()
        elif self.state == MenuState.ABOUT:
            self._render_controls()
    
    def _draw_background(self):
        """Draw scrolling parallax background"""
        for i, texture in enumerate(self.bg_textures):
            if texture is None:
                continue
            
            offset = int(self.bg_offsets[i])
            
            # Draw two copies for seamless scrolling
            src_rect = None
            
            # First copy
            dst_rect1 = sdl2.SDL_Rect(-offset, 0, self.width, self.height)
            sdl2.SDL_RenderCopy(self.renderer, texture, src_rect, dst_rect1)
            
            # Second copy (for seamless loop)
            dst_rect2 = sdl2.SDL_Rect(self.width - offset, 0, self.width, self.height)
            sdl2.SDL_RenderCopy(self.renderer, texture, src_rect, dst_rect2)

    def _draw_overlay(self):
        rect = sdl2.SDL_Rect(0, 0, self.width, self.height)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 180)
        sdl2.SDL_RenderFillRect(self.renderer, rect)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)
    
    def _render_main_menu(self):
        """Render main menu with title and cloth placeholder"""
        # Draw title "Yasuo's Journey" at the top
        self._draw_centered_text("YASUO'S JOURNEY", -220, self.title_font, (255, 215, 100))
        
        # Draw cloth placeholder in center
        if self.placeholder_texture:
            # Scale placeholder to fit nicely
            scale = 1.5
            scaled_w = int(self.placeholder_w * scale)
            scaled_h = int(self.placeholder_h * scale)
            
            placeholder_x = (self.width - scaled_w) // 2
            placeholder_y = (self.height - scaled_h) // 2 + 20
            
            placeholder_rect = sdl2.SDL_Rect(placeholder_x, placeholder_y, scaled_w, scaled_h)
            sdl2.SDL_RenderCopy(self.renderer, self.placeholder_texture, None, placeholder_rect)
            
            # Draw menu options on the cloth
            start_y = placeholder_y + 50
            line_height = 60
            
            for i, option in enumerate(self.main_options):
                color = YELLOW if i == self.selected_index else (220, 200, 170)
                
                y_pos = start_y + (i * line_height)
                
                # Draw sword prefix for selected option
                if i == self.selected_index and self.prefix_texture:
                    text_surface = self.menu_font.render(option, color=color)
                    text_x = (self.width - text_surface.w) // 2 - 20
                    text_y = y_pos
                    
                    # Position sword to the left of text
                    sword_scale = 0.2
                    sword_w = int(self.prefix_w * sword_scale)
                    sword_h = int(self.prefix_h * sword_scale)
                    sword_x = text_x - sword_w
                    sword_y = text_y + (text_surface.h - sword_h) // 2
                    
                    sword_rect = sdl2.SDL_Rect(sword_x, sword_y, sword_w, sword_h)
                    sdl2.SDL_RenderCopy(self.renderer, self.prefix_texture, None, sword_rect)
                    sdl2.SDL_FreeSurface(text_surface)
                
                self._draw_centered_text(option, y_pos - self.height // 2, self.menu_font, color)
        else:
            # Fallback if placeholder not loaded
            self._render_list("YASUO'S JOURNEY", self.main_options)

    def _render_list(self, title, options):
        self._draw_centered_text(title, -100, self.title_font, YELLOW)
        start_y = self.height // 2 - 20
        line_height = 45

        for i, option in enumerate(options):
            color = YELLOW if i == self.selected_index else WHITE
            
            # Draw sword prefix for selected option
            if i == self.selected_index and self.prefix_texture:
                text_surface = self.menu_font.render(option, color=color)
                text_x = (self.width - text_surface.w) // 2 - 20
                text_y = start_y + (i * line_height)
                
                # Position sword to the left of text
                sword_scale = 0.2
                sword_w = int(self.prefix_w * sword_scale)
                sword_h = int(self.prefix_h * sword_scale)
                sword_x = text_x - sword_w
                sword_y = text_y + (text_surface.h - sword_h) // 2
                
                sword_rect = sdl2.SDL_Rect(sword_x, sword_y, sword_w, sword_h)
                sdl2.SDL_RenderCopy(self.renderer, self.prefix_texture, None, sword_rect)
                sdl2.SDL_FreeSurface(text_surface)
            
            self._draw_centered_text(option, (i * line_height), self.menu_font, color, offset_y_base=start_y)

    def _render_options(self):
        """Vẽ menu Option với thanh volume - improved layout"""
        self._draw_centered_text("OPTIONS", -180, self.title_font, YELLOW)
        
        start_y = self.height // 2 - 60
        line_height = 80
        
        for i, item in enumerate(self.option_items):
            color = YELLOW if i == self.selected_index else WHITE
            
            if item == "Back":
                # Center the Back button
                y_pos = start_y + (i * line_height) + 20
                
                # Draw sword prefix for selected option
                if i == self.selected_index and self.prefix_texture:
                    text_surface = self.menu_font.render(item, color=color)
                    text_x = (self.width - text_surface.w) // 2 - 20
                    
                    # Position sword to the left of text
                    sword_scale = 0.2
                    sword_w = int(self.prefix_w * sword_scale)
                    sword_h = int(self.prefix_h * sword_scale)
                    sword_x = text_x - sword_w
                    sword_y = y_pos + (text_surface.h - sword_h) // 2
                    
                    sword_rect = sdl2.SDL_Rect(sword_x, sword_y, sword_w, sword_h)
                    sdl2.SDL_RenderCopy(self.renderer, self.prefix_texture, None, sword_rect)
                    sdl2.SDL_FreeSurface(text_surface)
                
                self._draw_centered_text(item, (i * line_height) + 20, self.menu_font, color, offset_y_base=start_y)
            else:
                # Draw label and volume bar with more spacing
                label_y = start_y + (i * line_height)
                label_x = self.width // 2 - 250
                
                # Draw sword prefix for selected option
                if i == self.selected_index and self.prefix_texture:
                    # Position sword to the left of label
                    sword_scale = 0.2
                    sword_w = int(self.prefix_w * sword_scale)
                    sword_h = int(self.prefix_h * sword_scale)
                    sword_x = label_x - sword_w - 10
                    sword_y = label_y
                    
                    sword_rect = sdl2.SDL_Rect(sword_x, sword_y, sword_w, sword_h)
                    sdl2.SDL_RenderCopy(self.renderer, self.prefix_texture, None, sword_rect)
                
                # Draw label more to the left
                self._draw_text_at(item, label_x, label_y, self.menu_font, color)
                
                # Draw volume bar more to the right with more space
                volume = self.music_volume if i == 0 else self.sfx_volume
                self._draw_volume_bar(self.width // 2 + 20, label_y, 180, 25, volume, color)

    def _render_controls(self):
        """Vẽ bảng hướng dẫn phím - improved layout"""
        self._draw_centered_text("CONTROLS", -200, self.title_font, YELLOW)
        
        start_y = self.height // 2 - 120
        line_height = 40
        
        for i, (key, action) in enumerate(self.controls_text):
            y = start_y + (i * line_height)
            self._draw_text_at(key, self.width // 2 - 250, y, self.info_font, YELLOW)
            self._draw_text_at(action, self.width // 2 + 80, y, self.info_font, WHITE)

    def _draw_volume_bar(self, x, y, w, h, percent, color):
        """Vẽ thanh volume đơn giản"""
        # Viền
        rect = sdl2.SDL_Rect(int(x), int(y), w, h)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, rect)
        
        # Phần đã fill
        fill_w = int(w * (percent / 100))
        if fill_w > 0:
            fill_rect = sdl2.SDL_Rect(int(x + 1), int(y + 1), fill_w - 2, h - 2)
            # Màu xanh lá nếu đang chọn, màu xám nếu không
            r, g, b = GREEN if color == YELLOW else GRAY
            sdl2.SDL_SetRenderDrawColor(self.renderer, r, g, b, 255)
            sdl2.SDL_RenderFillRect(self.renderer, fill_rect)
        
        # Số %
        self._draw_text_at(f"{percent}%", x + w + 10, y - 2, self.info_font, color)

    def _draw_centered_text(self, text, offset_y, font_manager, color, offset_y_base=None):
        if not font_manager: return
        surface = font_manager.render(text, color=color)
        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        w, h = surface.w, surface.h
        
        center_y = self.height // 2 if offset_y_base is None else offset_y_base
        x = (self.width - w) // 2
        y = center_y + offset_y
        
        dst = sdl2.SDL_Rect(x, y, w, h)
        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst)
        sdl2.SDL_FreeSurface(surface)
        sdl2.SDL_DestroyTexture(texture)

    def _draw_text_at(self, text, x, y, font_manager, color):
        if not font_manager: return
        surface = font_manager.render(text, color=color)
        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        dst = sdl2.SDL_Rect(int(x), int(y), surface.w, surface.h)
        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst)
        sdl2.SDL_FreeSurface(surface)
        sdl2.SDL_DestroyTexture(texture)
    
    def cleanup(self):
        """Clean up textures"""
        for texture in self.bg_textures:
            if texture:
                sdl2.SDL_DestroyTexture(texture)
        if self.placeholder_texture:
            sdl2.SDL_DestroyTexture(self.placeholder_texture)
        if self.prefix_texture:
            sdl2.SDL_DestroyTexture(self.prefix_texture)