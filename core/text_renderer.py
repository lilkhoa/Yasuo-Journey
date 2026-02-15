import sdl2
import sdl2.ext
import sdl2.sdlttf
import sdl2.sdlgfx as gfx

class TextRenderer:
    def __init__(self, renderer, font_path, size=16):
        self.renderer = renderer
        
        if sdl2.sdlttf.TTF_WasInit() == 0:
            sdl2.sdlttf.TTF_Init()

        try:
            self.font = sdl2.sdlttf.TTF_OpenFont(font_path.encode('utf-8'), size)
            if not self.font:
                print(f"Warning: Could not load font at {font_path}")
        except Exception as e:
            print(f"Font loading error: {e}")
            self.font = None

    def renderer_text(self, text, x, y, color=(255, 255, 255), draw_bg=False, bg_color=(0, 0, 0, 200), radius=8):
        """
            Draw text into screen
            align: "left", "center", "right"
        """
        if not self.font: return

        sdl_color = sdl2.SDL_Color(*color)

        # Create surface from text
        surface = sdl2.sdlttf.TTF_RenderText_Solid(self.font, text.encode('utf-8'), sdl_color)
        if not surface: return

        # create texture from surface
        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)

        # Calculate position
        w = surface.contents.w
        h = surface.contents.h

        draw_x = int(x) - w//2
        draw_y = int(y)

        if draw_bg:
            padding_x = 10  # left/right padding
            padding_y = 6   # top/bottom padding

            left = draw_x - padding_x
            top = draw_y - padding_y
            right = draw_x + w + padding_x
            bottom = draw_y + h + padding_y

            r, g, b, a = bg_color

            gfx.roundedBoxRGBA(
                self.renderer,
                left, top, right, bottom,
                radius,
                r, g, b, a
            )

        dst_rect = sdl2.SDL_Rect(draw_x, draw_y, w, h)

        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst_rect)

        sdl2.SDL_DestroyTexture(texture)
        sdl2.SDL_FreeSurface(surface)

    def create_text_texture(self, text, color=(255, 255, 255)):
        """
            Create a static surface for text, using HUD for not rendering at each frame
            Return: (texture, width, height)
        """
        if not self.font: return None, 0, 0

        sdl_color = sdl2.SDL_Color(*color)
        surface = sdl2.sdlttf.TTF_RenderText_Solid(self.font, text.encode('utf-8'), sdl_color)

        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        w = surface.contents.w
        h = surface.contents.h
        sdl2.SDL_FreeSurface(surface)

        return texture, w, h
    
    def render_multiline(self, text, x, y, color=(255, 255, 255), draw_bg=False, bg_color=(0, 0, 0, 200), radius=8, line_spacing=5):
        """
        Vẽ văn bản nhiều dòng (tách bởi ký tự \n), căn giữa theo trục X.
        """
        if not self.font: return

        sdl_color = sdl2.SDL_Color(*color)
        lines = text.split('\n') # Tách chuỗi thành các dòng
        
        # 1. Tính toán kích thước tổng
        surfaces = []
        max_w = 0
        total_h = 0
        
        # Duyệt qua từng dòng để tính chiều rộng lớn nhất và tổng chiều cao
        for line in lines:
            if not line: continue
            surface = sdl2.sdlttf.TTF_RenderText_Solid(self.font, line.encode('utf-8'), sdl_color)
            w = surface.contents.w
            h = surface.contents.h
            surfaces.append((surface, w, h))
            
            if w > max_w: max_w = w
            total_h += h
        
        # Cộng thêm khoảng cách giữa các dòng
        total_h += (len(surfaces) - 1) * line_spacing
        
        # 2. Vẽ khung nền (Background Box) bao trọn tất cả
        center_x = int(x)
        start_y = int(y)
        
        if draw_bg and surfaces:
            padding_x = 15
            padding_y = 10
            
            left = center_x - max_w // 2 - padding_x
            top = start_y - padding_y
            right = center_x + max_w // 2 + padding_x
            bottom = start_y + total_h + padding_y
            
            r, g, b, a = bg_color
            gfx.roundedBoxRGBA(self.renderer, left, top, right, bottom, radius, r, g, b, a)

        # 3. Vẽ từng dòng text
        current_y = start_y
        for surf, w, h in surfaces:
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surf)
            
            # Căn giữa dòng hiện tại
            draw_x = center_x - w // 2
            
            dst_rect = sdl2.SDL_Rect(draw_x, current_y, w, h)
            sdl2.SDL_RenderCopy(self.renderer, texture, None, dst_rect)
            
            # Dọn dẹp
            sdl2.SDL_DestroyTexture(texture)
            sdl2.SDL_FreeSurface(surf)
            
            # Xuống dòng
            current_y += h + line_spacing



    