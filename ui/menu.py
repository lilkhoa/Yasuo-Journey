import sdl2
import sdl2.ext
import os

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
            self.title_font = sdl2.ext.FontManager(font_path, size=48, color=WHITE)
            self.menu_font = sdl2.ext.FontManager(font_path, size=24, color=WHITE)
            self.info_font = sdl2.ext.FontManager(font_path, size=18, color=WHITE) # Font nhỏ hơn cho About
        except:
            print("[MENU] Warning: Font not found, using default.")
            self.title_font = None
            self.menu_font = None
            self.info_font = None

        self.state = MenuState.MAIN_MENU
        self.selected_index = 0
        
        # --- DATA MENU ---
        self.main_options = ["New Game", "Option", "About", "Exit"]
        self.pause_options = ["Resume", "Exit to Main Menu"]
        
        # Option Data
        self.option_items = ["Music Volume", "SFX Volume", "Back"]
        self.music_volume = 50 # 0 - 100
        self.sfx_volume = 50   # 0 - 100

        # About Data (Hướng dẫn chơi)
        self.controls_text = [
            ("Arrow Keys", "Move"),
            ("Shift", "Run"),
            ("Space", "Jump"),
            ("A", "Attack"),
            ("Q, W, E", "Skills"),
            ("Ctrl + 6", "m gà vcl"),
            ("F", "Interact (Pick up / Chest)"),
            ("Esc", "Pause / Back")
        ]

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
                        if choice == "New Game":
                            self.state = MenuState.GAME_PLAYING
                            return "START_GAME"
                        elif choice == "Option":
                            self.state = MenuState.OPTION
                            self.selected_index = 0
                        elif choice == "About":
                            self.state = MenuState.ABOUT
                        elif choice == "Exit":
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
                            return "UPDATE_VOLUME"
                        elif self.selected_index == 1: # SFX
                            self.sfx_volume = max(0, self.sfx_volume - 10)
                            return "UPDATE_VOLUME"
                            
                    elif key == sdl2.SDLK_RIGHT:
                        if self.selected_index == 0: # Music
                            self.music_volume = min(100, self.music_volume + 10)
                            return "UPDATE_VOLUME"
                        elif self.selected_index == 1: # SFX
                            self.sfx_volume = min(100, self.sfx_volume + 10)
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

    def render(self):
        if self.state == MenuState.GAME_PLAYING:
            return 

        if self.state != MenuState.PAUSE:
            # Vẽ nền tối cho các menu chính
            sdl2.SDL_SetRenderDrawColor(self.renderer, 20, 20, 30, 255)
            sdl2.SDL_RenderClear(self.renderer)
        else:
            self._draw_overlay()

        # Render nội dung
        if self.state == MenuState.MAIN_MENU:
            self._render_list("MAIN MENU", self.main_options)
        elif self.state == MenuState.PAUSE:
            self._render_list("PAUSE", self.pause_options)
        elif self.state == MenuState.OPTION:
            self._render_options()
        elif self.state == MenuState.ABOUT:
            self._render_controls()

    def _draw_overlay(self):
        rect = sdl2.SDL_Rect(0, 0, self.width, self.height)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 180)
        sdl2.SDL_RenderFillRect(self.renderer, rect)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

    def _render_list(self, title, options):
        self._draw_centered_text(title, -100, self.title_font, YELLOW)
        start_y = self.height // 2 - 20
        line_height = 45

        for i, option in enumerate(options):
            color = YELLOW if i == self.selected_index else WHITE
            prefix = "> " if i == self.selected_index else "  "
            text = f"{prefix}{option}"
            self._draw_centered_text(text, (i * line_height), self.menu_font, color, offset_y_base=start_y)

    def _render_options(self):
        """Vẽ menu Option với thanh volume"""
        self._draw_centered_text("OPTIONS", -120, self.title_font, YELLOW)
        
        start_y = self.height // 2 - 40
        line_height = 50
        
        for i, item in enumerate(self.option_items):
            color = YELLOW if i == self.selected_index else WHITE
            
            # Vẽ Label (Music, SFX, Back)
            prefix = "> " if i == self.selected_index else "   "
            text = f"{prefix}{item}"
            
            # Tính vị trí text
            # Vẽ text lệch trái một chút để chừa chỗ cho thanh volume
            if item == "Back":
                self._draw_centered_text(text, (i * line_height), self.menu_font, color, offset_y_base=start_y)
            else:
                # Vẽ Label bên trái
                # Hardcode vị trí X cho đơn giản: width/2 - 150
                label_y = start_y + (i * line_height)
                self._draw_text_at(text, self.width // 2 - 200, label_y, self.menu_font, color)
                
                # Vẽ thanh Volume bên phải
                volume = self.music_volume if i == 0 else self.sfx_volume
                self._draw_volume_bar(self.width // 2 + 50, label_y + 5, 150, 20, volume, color)

    def _render_controls(self):
        """Vẽ bảng hướng dẫn phím"""
        self._draw_centered_text("CONTROLS", -200, self.title_font, YELLOW)
        
        start_y = self.height // 2 - 120
        line_height = 35
        
        # Vẽ Header
        self._draw_text_at("KEY", self.width // 2 - 200, start_y - 40, self.menu_font, GRAY)
        self._draw_text_at("ACTION", self.width // 2 + 50, start_y - 40, self.menu_font, GRAY)
        
        for i, (key, action) in enumerate(self.controls_text):
            y = start_y + (i * line_height)
            self._draw_text_at(key, self.width // 2 - 200, y, self.info_font, YELLOW)
            self._draw_text_at(action, self.width // 2 + 50, y, self.info_font, WHITE)
            
        # Footer
        self._draw_centered_text("Press Enter to Return", 250, self.info_font, GRAY)

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