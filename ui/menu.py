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
GREEN_DARK = (0, 180, 0)      # xanh lá đậm hơn
CYAN = (0, 200, 255)          # xanh da trời (cyan)
BLUE_DEEP = (0, 102, 204)
BLACK = (0, 0, 0)
OVERLAY_COLOR = (0, 0, 0, 150)

class MenuState:
    MAIN_MENU = 0
    OPTION = 1
    ABOUT = 2
    GAME_PLAYING = 3
    PAUSE = 4
    MULTIPLAYER = 5
    HOST_LOBBY = 6
    JOIN_LOBBY = 7
    CHARACTER_SELECT = 8

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
        self.main_options = ["SINGLE PLAYER", "MULTIPLAYER", "OPTION", "ABOUT", "EXIT"]
        self.pause_options = ["Resume", "Exit to Main Menu"]
        self.multiplayer_options = ["Host Game", "Join Game", "Back"]

        # --- [NEW] CHARACTER SELECT DATA ---
        self.char_selection = 0  # 0: Yasuo, 1: Leaf Ranger
        self.char_profiles = [
            {"name": "YASUO", "id": "yasuo", "texture": None, "w": 128, "h": 128},
            {"name": "LEAF RANGER", "id": "leaf_ranger", "texture": None, "w": 288, "h": 128}
        ]

        assets_dir = "./assets"
        # Load ảnh Yasuo (Cắt frame đầu tiên của animation Idle)
        yasuo_path = os.path.join(assets_dir, "Player", "Idle.png")
        try:
            surf = sdl2.ext.load_image(yasuo_path)
            self.char_profiles[0]["texture"] = sdl2.SDL_CreateTextureFromSurface(self.renderer, surf)
            # Giả định ảnh strip ngang, frame_width = frame_height
            self.char_profiles[0]["w"] = surf.contents.h 
            self.char_profiles[0]["h"] = surf.contents.h
            sdl2.SDL_FreeSurface(surf)
        except Exception as e:
            print(f"[MENU] Không thể load ảnh Yasuo: {e}")

        # Load ảnh Leaf Ranger (Lấy frame idle_1.png)
        ranger_path = os.path.join(assets_dir, "Player_2", "idle", "idle_1.png")
        try:
            surf = sdl2.ext.load_image(ranger_path)
            self.char_profiles[1]["texture"] = sdl2.SDL_CreateTextureFromSurface(self.renderer, surf)
            self.char_profiles[1]["w"] = surf.contents.w
            self.char_profiles[1]["h"] = surf.contents.h
            sdl2.SDL_FreeSurface(surf)
        except Exception as e:
            print(f"[MENU] Không thể load ảnh Leaf Ranger: {e}")

        # Multiplayer Data
        self.join_ip = ""
        self.host_ip = "127.0.0.1" # Will be updated dynamically by game.py
        self.lobby_status_msg = ""
        self.lobby_host_ready = False
        self.lobby_client_ready = False
        self.is_host = False
        
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
                        if choice == "SINGLE PLAYER":
                            # [FIX] Chuyển state sang màn hình chọn tướng
                            self.state = MenuState.CHARACTER_SELECT
                            self.char_selection = 0  # Reset về Yasuo mặc định
                            return None  # Trả về None để vòng lặp menu tiếp tục chạy
                        elif choice == "MULTIPLAYER":
                            self.state = MenuState.MULTIPLAYER
                            self.selected_index = 0
                        elif choice == "OPTION":
                            self.state = MenuState.OPTION
                            self.selected_index = 0
                        elif choice == "ABOUT":
                            self.state = MenuState.ABOUT
                        elif choice == "EXIT":
                            return "QUIT_GAME"

                # --- CHARACTER SELECT MENU ---
                elif self.state == MenuState.CHARACTER_SELECT:
                    if key == sdl2.SDLK_LEFT:
                        self.char_selection = (self.char_selection - 1) % len(self.char_profiles)
                        # Play sound tick (nếu có)
                    elif key == sdl2.SDLK_RIGHT:
                        self.char_selection = (self.char_selection + 1) % len(self.char_profiles)
                        # Play sound tick (nếu có)
                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER:
                        selected_id = self.char_profiles[self.char_selection]["id"]
                        self.state = MenuState.GAME_PLAYING
                        return ("START_GAME", selected_id)  # Trả về Tuple để game.py nhận diện
                    elif key == sdl2.SDLK_ESCAPE:
                        self.state = MenuState.MAIN_MENU
                        self.selected_index = 0

                # --- MULTIPLAYER MENU ---
                elif self.state == MenuState.MULTIPLAYER:
                    if key == sdl2.SDLK_UP:
                        self.selected_index = (self.selected_index - 1) % len(self.multiplayer_options)
                    elif key == sdl2.SDLK_DOWN:
                        self.selected_index = (self.selected_index + 1) % len(self.multiplayer_options)
                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER:
                        choice = self.multiplayer_options[self.selected_index]
                        if choice == "Host Game":
                            self.state = MenuState.HOST_LOBBY
                            self.is_host = True
                            return "START_HOST"
                        elif choice == "Join Game":
                            self.state = MenuState.JOIN_LOBBY
                            self.is_host = False
                            self.join_ip = ""
                            sdl2.SDL_StartTextInput()
                        elif choice == "Back":
                            self.state = MenuState.MAIN_MENU
                            self.selected_index = 1
                    elif key == sdl2.SDLK_ESCAPE:
                        self.state = MenuState.MAIN_MENU
                        self.selected_index = 1

                # --- JOIN LOBBY ---
                elif self.state == MenuState.JOIN_LOBBY:
                    if key == sdl2.SDLK_BACKSPACE:
                        self.join_ip = self.join_ip[:-1]
                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER:
                        if self.join_ip:
                            sdl2.SDL_StopTextInput()
                            self.state = MenuState.HOST_LOBBY
                            return "START_JOIN"
                    elif key == sdl2.SDLK_ESCAPE:
                        sdl2.SDL_StopTextInput()
                        self.state = MenuState.MULTIPLAYER
                        self.selected_index = 1

                # --- HOST LOBBY ---
                elif self.state == MenuState.HOST_LOBBY:
                    if key == sdl2.SDLK_ESCAPE:
                        self.state = MenuState.MULTIPLAYER
                        self.selected_index = 0
                        return "CANCEL_LOBBY"
                    elif key == sdl2.SDLK_RETURN or key == sdl2.SDLK_KP_ENTER:
                        return "LOBBY_ACTION"

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

            elif event.type == sdl2.SDL_TEXTINPUT and self.state == MenuState.JOIN_LOBBY:
                text = event.text.text.decode('utf-8')
                if len(self.join_ip) < 15:
                    self.join_ip += text
        
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
        elif self.state == MenuState.MULTIPLAYER:
            self._render_list("MULTIPLAYER", self.multiplayer_options)
        elif self.state == MenuState.JOIN_LOBBY:
            self._render_join_lobby()
        elif self.state == MenuState.HOST_LOBBY:
            self._render_host_lobby()
        elif self.state == MenuState.CHARACTER_SELECT:
            self._render_character_select()
    
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
            scale = 1.7
            scaled_w = int(self.placeholder_w * scale)
            scaled_h = int(self.placeholder_h * scale)
            
            placeholder_x = (self.width - scaled_w) // 2
            placeholder_y = (self.height - scaled_h) // 2 + 20
            
            placeholder_rect = sdl2.SDL_Rect(placeholder_x, placeholder_y, scaled_w, scaled_h)
            sdl2.SDL_RenderCopy(self.renderer, self.placeholder_texture, None, placeholder_rect)
            
            # Draw menu options on the cloth
            start_y = placeholder_y + 54
            line_height = 50
            
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

    def _render_character_select(self):
        """Vẽ giao diện chọn nhân vật trực quan với ảnh và mũi tên"""
        self._draw_centered_text("CHOOSE YOUR HERO", -200, self.title_font, YELLOW)
        
        profile = self.char_profiles[self.char_selection]
        
        # Vẽ 2 mũi tên điều hướng < và >
        self._draw_text_at("<", self.width // 2 - 200, self.height // 2 - 30, self.title_font, WHITE)
        self._draw_text_at(">", self.width // 2 + 180, self.height // 2 - 30, self.title_font, WHITE)
        
        # Vẽ Ảnh Nhân Vật
        if profile["texture"]:
            scale = 2.0 if profile["id"] == "yasuo" else 3.5  # Phóng to ảnh lên gấp đôi cho rõ
            dst_w = int(profile["w"] * scale)
            dst_h = int(profile["h"] * scale)
            dst_x = (self.width - dst_w) // 2
            dst_y = (self.height - dst_h) // 2 - 60 if profile["id"] == "yasuo" else (self.height - dst_h) // 2 - 150
            
            # Cắt frame đầu tiên (nếu là sprite sheet)
            src_rect = sdl2.SDL_Rect(0, 0, profile["w"], profile["h"])
            dst_rect = sdl2.SDL_Rect(dst_x, dst_y, dst_w, dst_h)
            
            sdl2.SDL_RenderCopy(self.renderer, profile["texture"], src_rect, dst_rect)
        else:
            self._draw_centered_text("[NO IMAGE FOUND]", -50, self.menu_font, GRAY)
            
        # Vẽ Tên Nhân Vật (Màu xanh lá cho Leaf Ranger, Màu Vàng cho Yasuo)
        # name_color = GREEN if profile["id"] == "leaf_ranger" else YELLOW
        name_color = GREEN_DARK if profile["id"] == "leaf_ranger" else BLUE_DEEP
        self._draw_centered_text(profile["name"], 80, self.title_font, name_color)
        
        # Vẽ Hướng dẫn
        self._draw_centered_text("[Left/Right] Select   [Enter] Play   [Esc] Back", 160, self.info_font, WHITE)

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

    def _render_join_lobby(self):
        self._draw_centered_text("JOIN GAME", -200, self.title_font, YELLOW)
        self._draw_centered_text("Enter Host IP or Room ID:", -50, self.menu_font, YELLOW)
        
        # Draw text box
        box_w, box_h = 300, 40
        box_x = (self.width - box_w) // 2
        box_y = self.height // 2 + 10
        rect = sdl2.SDL_Rect(box_x, box_y, box_w, box_h)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 50, 50, 200)
        sdl2.SDL_RenderFillRect(self.renderer, rect)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 0, 255) # Yellow border
        sdl2.SDL_RenderDrawRect(self.renderer, rect)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)
        
        # Draw IP text
        display_text = self.join_ip + "_"
        self._draw_centered_text(display_text, 20, self.menu_font, YELLOW)
        
        self._draw_centered_text("[Enter] to Connect   [Esc] to Cancel", 100, self.info_font, YELLOW)

    def _render_host_lobby(self):
        title = "HOST LOBBY" if self.is_host else "GAME LOBBY"
        self._draw_centered_text(title, -200, self.title_font, YELLOW)
        
        if self.is_host:
            import network.packet
            room_id = network.packet.encode_ip(self.host_ip)
            self._draw_centered_text(f"IP: {self.host_ip}  |  Room ID: {room_id}", -120, self.menu_font, YELLOW)
            if not self.lobby_client_ready and not self.lobby_host_ready:
                self._draw_centered_text("Waiting for Player 2 to join...", -70, self.menu_font, YELLOW)
        else:
            self._draw_centered_text(f"Connected to {self.host_ip}", -120, self.menu_font, YELLOW)
            
        # Draw players status
        self._draw_text_at("Player 1 (Host):", self.width // 2 - 200, self.height // 2 - 20, self.menu_font, YELLOW)
        h_status = "READY" if self.lobby_host_ready else "Not Ready"
        h_color = GREEN if self.lobby_host_ready else YELLOW
        self._draw_text_at(h_status, self.width // 2 + 150, self.height // 2 - 20, self.menu_font, h_color)
        
        self._draw_text_at("Player 2 (Guest):", self.width // 2 - 200, self.height // 2 + 30, self.menu_font, YELLOW)
        c_status = "READY" if self.lobby_client_ready else "Not Ready"
        c_color = GREEN if self.lobby_client_ready else YELLOW
        self._draw_text_at(c_status, self.width // 2 + 150, self.height // 2 + 30, self.menu_font, c_color)

        if self.lobby_status_msg:
            self._draw_centered_text(self.lobby_status_msg, 100, self.info_font, YELLOW)

        self._draw_centered_text("[Enter] Toggle Ready / Start   [Esc] Leave", 150, self.info_font, YELLOW)

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

        # [NEW] Dọn dẹp ảnh character select
        if hasattr(self, 'char_profiles'):
            for profile in self.char_profiles:
                if profile["texture"]:
                    sdl2.SDL_DestroyTexture(profile["texture"])