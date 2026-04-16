import sdl2

def handle_input(event, player, world, factory, renderer, npc_manager):
    """
    Xử lý sự kiện đầu vào (Keyboard, Quit).
    Trả về False nếu người chơi muốn thoát game.
    """
    if event.type == sdl2.SDL_QUIT:
        return False
    
    if event.type == sdl2.SDL_KEYDOWN:
        key = event.key.keysym.sym
        keys = sdl2.SDL_GetKeyboardState(None)
        
        # Khóa điều khiển nếu nhân vật đã chết
        if hasattr(player, 'state') and player.state == 'dead':
            return True

        # Xác định hướng dựa trên phím giữ (Dùng để lướt hoặc định hướng chiêu)
        dash_dir = 0
        if keys[sdl2.SDL_SCANCODE_RIGHT]: dash_dir = 1
        elif keys[sdl2.SDL_SCANCODE_LEFT]: dash_dir = -1
        
        # Kiểm tra Modifier (Ctrl)
        is_ctrl = (event.key.keysym.mod & sdl2.KMOD_CTRL)

        # Hành động: Nâng cấp kỹ năng
        if is_ctrl:
            if key == sdl2.SDLK_q: player.upgrade_skill('q')
            elif key == sdl2.SDLK_w: player.upgrade_skill('w')
            elif key == sdl2.SDLK_e: player.upgrade_skill('e')
            elif key == sdl2.SDLK_a: player.upgrade_skill('a')
            return True # Tiêu thụ sự kiện ngay lập tức, không kích hoạt chiêu
            
        # Lấy đúng con trỏ C (C-Pointer) cho các hàm vẽ bên trong Skill
        sdl_renderer_ptr = getattr(renderer, 'sdlrenderer', renderer)

        # Hành động: Thi triển (Đa hình - Gọi chung cho cả Yasuo & LeafRanger)
        if key == sdl2.SDLK_SPACE:
            player.jump()
        elif key == sdl2.SDLK_q: 
            player.start_q(dash_dir)
        elif key == sdl2.SDLK_w: 
            player.start_w(dash_dir)
        elif key == sdl2.SDLK_e: 
            player.start_e(world, factory, sdl_renderer_ptr, dash_dir)
        elif key == sdl2.SDLK_a:
            player.attack()
    
    return True