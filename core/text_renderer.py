import sdl2
import sdl2.ext
import sdl2.sdlttf

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

    def renderer_text(self, text, x, y, color=(255, 255, 255)):
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

        draw_x = int(x)
        draw_y = int(y)

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



    