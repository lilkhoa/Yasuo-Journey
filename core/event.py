import sdl2
import sys

def handle_input(event, player, world, factory, renderer, active_tornadoes, active_walls, npc_manager):
    """
    Xử lý sự kiện đầu vào (Keyboard, Quit).
    Trả về False nếu người chơi muốn thoát game.
    """
    if event.type == sdl2.SDL_QUIT:
        return False
    
    if event.type == sdl2.SDL_KEYDOWN:
        key = event.key.keysym.sym
        keys = sdl2.SDL_GetKeyboardState(None)
        
        # Xác định hướng dựa trên phím giữ
        dash_dir = 0
        if keys[sdl2.SDL_SCANCODE_RIGHT]: dash_dir = 1
        elif keys[sdl2.SDL_SCANCODE_LEFT]: dash_dir = -1
        
        # Kiểm tra Modifier (Ctrl)
        is_ctrl = (event.key.keysym.mod & sdl2.KMOD_CTRL)

        # Hành động Player
        if is_ctrl:
            # Upgrade Skills
            if key == sdl2.SDLK_q: player.upgrade_skill('q')
            elif key == sdl2.SDLK_w: player.upgrade_skill('w')
            elif key == sdl2.SDLK_e: player.upgrade_skill('e')
            elif key == sdl2.SDLK_a: player.upgrade_skill('a')
            return True # Tiêu thụ sự kiện nếu upgrade
            
        if key == sdl2.SDLK_SPACE:
            player.jump()
        elif key == sdl2.SDLK_q: 
            player.start_q(dash_dir)
        elif key == sdl2.SDLK_w: 
            player.start_w(dash_dir)
        elif key == sdl2.SDLK_e: 
            player.start_e(world, factory, renderer, dash_dir)
        elif key == sdl2.SDLK_a:
            player.attack()
    
    return True
