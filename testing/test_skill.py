import sys
import os
import sdl2
import sdl2.ext

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from entities.player import Player
from combat.skill_q import update_q_logic
from combat.skill_w import update_w_logic

COLOR_BG = sdl2.ext.Color(0, 0, 0)

class NPC(sdl2.ext.Entity):
    def __init__(self, world, sprite, x, y):
        self.sprite = sprite
        self.sprite.position = x, y
        self.base_y = y 

def run_test():
    sdl2.ext.init()
    window = sdl2.ext.Window("Samurai Dash Control Test", size=(1000, 600))
    window.show()
    
    world = sdl2.ext.World()
    factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    spriterenderer = factory.create_sprite_render_system(window)
    world.add_system(spriterenderer)

    print("Loading game...")
    player = Player(world, factory, 100, 400)
    
    npc_img = factory.from_color(sdl2.ext.Color(50, 200, 50), size=(50, 50))
    npcs = [NPC(world, npc_img, 400 + i*150, 400) for i in range(4)]
    
    active_tornadoes = []
    active_walls = []
    
    running = True
    last_time = sdl2.SDL_GetTicks()

    print("=== ĐIỀU KHIỂN ===")
    print("GIỮ [->] + BẤM [E] = Lướt phải")
    print("GIỮ [<-] + BẤM [E] = Lướt trái")
    print("Bấm [E] không = Không lướt")
    
    while running:
        current_time = sdl2.SDL_GetTicks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time

        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                
                # Lấy trạng thái bàn phím để biết hướng đang giữ
                keyboard_state = sdl2.SDL_GetKeyboardState(None)
                current_dir = 0
                if keyboard_state[sdl2.SDL_SCANCODE_RIGHT]:
                    current_dir = 1
                elif keyboard_state[sdl2.SDL_SCANCODE_LEFT]:
                    current_dir = -1
                
                if key == sdl2.SDLK_q: 
                    player.start_q(current_dir)
                    
                elif key == sdl2.SDLK_w: 
                    player.start_w(current_dir)
                
                elif key == sdl2.SDLK_e:
                    player.start_e(world, factory, spriterenderer, current_dir)
        
        keys = sdl2.SDL_GetKeyboardState(None)
        
        player.update(dt, world, factory, spriterenderer, active_tornadoes, active_walls)
        
        if player.state == 'idle' or player.state == 'dashing_e':
            if keys[sdl2.SDL_SCANCODE_RIGHT]:
                player.sprite.x += int(player.move_speed * dt)
                player.facing_right = True
            elif keys[sdl2.SDL_SCANCODE_LEFT]:
                player.sprite.x -= int(player.move_speed * dt)
                player.facing_right = False
                
        player.skill_e.update_dash(dt, npcs)
        if player.skill_e.is_dashing: player.state = 'dashing_e'
        elif player.state == 'dashing_e' and not player.skill_e.is_dashing: player.state = 'idle'

        for t in active_tornadoes[:]:
            update_q_logic(t, npcs, dt)
            if not t.active: active_tornadoes.remove(t)
            
        for w in active_walls[:]:
            update_w_logic(w)
            if not w.active: active_walls.remove(w)

        sdl2.ext.fill(window.get_surface(), COLOR_BG)
        world.process()
        window.refresh()
        sdl2.SDL_Delay(16)

    sdl2.ext.quit()

if __name__ == "__main__":
    run_test()