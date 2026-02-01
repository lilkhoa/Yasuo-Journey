import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sdl2
import sdl2.ext
from settings import *
from world.map import GameMap
from sdl2 import SDL_Rect, SDL_RenderCopy # Import hàm vẽ cấp thấp để tối ư

TEST_LEVEL = [
    "              ", # Row 0
    "              ", # Row 1
    "              ", # Row 2
    "      222     ", # Row 3: Một bục nhảy lơ lửng
    "              ", # Row 4
    "              ", # Row 5
    "12222222222222", # Row 6: Mặt đất chính (Sẽ nhìn thấy rõ nhất)
    "              ", # Row 7: Dưới lòng đất (Bị cắt 1 nửa hiển thị)
]

def draw_bg(renderer, texture):
    # Cắt toàn bộ ảnh gốc (320x180)
    src_rect = SDL_Rect(0, 0, 320, 180)
    # Vẽ giãn ra toàn màn hình (1280x720)
    dst_rect = SDL_Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    # Thực hiện lệnh vẽ
    SDL_RenderCopy(renderer, texture, src_rect, dst_rect)

def run():
    # 1. Khởi tạo SDL2
    sdl2.ext.init()
    
    # 2. Tạo cửa sổ (Window)
    window = sdl2.ext.Window("Project Game Demo", size=(WINDOW_WIDTH, WINDOW_HEIGHT))
    window.show()
    
    # 3. Tạo Renderer (Bộ vẽ) - Dùng GPU
    # index=-1 để chọn driver mặc định, flags=0
    renderer = sdl2.ext.Renderer(window, flags=sdl2.SDL_RENDERER_PRESENTVSYNC)
    
    # 4. Load Texture (Ảnh)
    # Factory giúp load ảnh dễ hơn
    factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
    
    try:
        # Đường dẫn ảnh phải chuẩn. Giả sử ảnh nằm cùng thư mục code.
        tileset_sprite = factory.from_image("assets/Map/oak_woods_tileset.png")
        tileset_texture = tileset_sprite.texture # Lấy raw texture SDL

        # Load 3 lớp Background (Theo thứ tự từ xa tới gần)
        bg1_sprite = factory.from_image("assets/Map/background/background_layer_1.png") # Bầu trời
        bg1_tex = bg1_sprite.texture
        
        bg2_sprite = factory.from_image("assets/Map/background/background_layer_2.png") # Rừng xa
        bg2_tex = bg2_sprite.texture

        bg3_sprite = factory.from_image("assets/Map/background/background_layer_3.png") # Rừng gần
        bg3_tex = bg3_sprite.texture
    except Exception as e:
        print(f"Lỗi load ảnh: {e}")
        return

    # 5. Khởi tạo Map
    my_map = GameMap(TEST_LEVEL)

    # 6. Vòng lặp game (Game Loop)
    running = True
    while running:
        # Xử lý sự kiện (Bấm nút tắt, phím bấm...)
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
        
        # --- RENDER (VẼ) ---
        # B1. Xóa màn hình (Tô màu nền)
        renderer.clear()
        
        # Lấy con trỏ renderer gốc để dùng hàm SDL_RenderCopy
        sdl_renderer = renderer.sdlrenderer

        # B2: Vẽ Background (Từ xa tới gần)
        # Nếu vẽ sai thứ tự, cái sau sẽ che mất cái trước!
        draw_bg(sdl_renderer, bg1_tex) # Layer 1: Xanh nhạt
        draw_bg(sdl_renderer, bg2_tex) # Layer 2: Tím nhạt
        draw_bg(sdl_renderer, bg3_tex) # Layer 3: Cây to

        # B3: Vẽ Map (Đè lên background)
        my_map.render(sdl_renderer, tileset_texture)
        
        # B4: Cập nhật màn hình
        renderer.present()

    # Dọn dẹp
    sdl2.ext.quit()

if __name__ == "__main__":
    run()