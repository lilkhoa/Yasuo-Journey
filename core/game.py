import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sdl2
import sdl2.ext
from settings import *
from world.map import GameMap
from world.decoration import Decoration
from sdl2 import SDL_Rect, SDL_RenderCopy
from camera import Camera

# --- THÊM IMPORTS CHO PLAYER VÀ NPC ---
from entities.player import Player
from entities.npc import NPCManager
from core.event import handle_input
from combat.skill_q import update_q_logic
from combat.skill_w import update_w_logic

# Long test map to test camera scroll: TERRAIN
TEST_LEVEL = [
    "                                                  ",  
    "                                                  ", 
    "                                                  ", 
    "  2233                    2233                    ", 
    "          (- - 8 8 8 8 8 8        (- - 8 8 8 8 8 8", 
    "      [== 78 8 0 0 0 0 0 0    [== 78 8 0 0 0 0 0 0", 
    "-5= =5- - - 68 0 0 0 0 0 0-5= =5- - - 68 0 0 0 0 0", 
    "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ", 
]

# DECO MAP (Mask Map)
# Lưu ý: the length must be compatible
DECO_MAP = [
    "                                                  ", 
    "    ff                                            ", 
    "                                                  ", 
    "                          S                       ", # f: hàng rào, S: Shop
    "          g g              l      g g             ", # g: cỏ, l: đèn
    "      r   r                       r               ", # r: đá
    "                                                  ", 
    "                                                  ", 
]

# --- HELPER: Wrapper cho NPC tương thích với Skill collision ---
class SpriteWrapper:
    def __init__(self, npc_instance):
        self.npc = npc_instance
    @property
    def x(self): return self.npc.x
    @x.setter
    def x(self, value): self.npc.x = value
    @property
    def y(self): return self.npc.y
    @y.setter
    def y(self, value): self.npc.y = value
    @property
    def position(self): return (self.npc.x, self.npc.y)
    @position.setter
    def position(self, value): self.npc.x, self.npc.y = value
    @property
    def size(self): return (self.npc.width, self.npc.height)

def make_npc_compatible(npc):
    npc.sprite = SpriteWrapper(npc)
    return npc

def render_surface_to_texture(sdl_renderer, surface, x, y):
    """Chuyển Surface sang Texture để render với camera offset"""
    if surface is None: return
    texture = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, surface)
    if not texture: return 
    w, h = surface.w, surface.h
    dst_rect = sdl2.SDL_Rect(int(x), int(y), w, h)
    sdl2.SDL_RenderCopy(sdl_renderer, texture, None, dst_rect)
    sdl2.SDL_DestroyTexture(texture)

def draw_bg(renderer, texture, camera_x, speed_factor):
    """
        speed_factor:
            0.0 -> do not move
            0.5 -> move to opposite direction, with speed = 1/2 player
            1.0 -> equal to player
    """
    bg_width = WINDOW_WIDTH

    relative_x = (camera_x * speed_factor) % bg_width

    src_rect = SDL_Rect(0, 0, 320, 180)
    dst_rect1 = SDL_Rect(int(-relative_x), 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    SDL_RenderCopy(renderer, texture, src_rect, dst_rect1)

    if relative_x > 0:
        dst_rect2 = SDL_Rect(int(-relative_x + bg_width), 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        SDL_RenderCopy(renderer, texture, src_rect, dst_rect2)

def run():
    sdl2.ext.init()
    window = sdl2.ext.Window("Project Game Demo", size=(WINDOW_WIDTH, WINDOW_HEIGHT))
    window.show()
    renderer = sdl2.ext.Renderer(window, flags=sdl2.SDL_RENDERER_PRESENTVSYNC)
    factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
    
    try:
        tileset_sprite = factory.from_image("assets/Map/oak_woods_tileset.png")
        tileset_texture = tileset_sprite.texture

        # Load 3 Background layers (far to near order)
        bg1_sprite = factory.from_image("assets/Map/background/background_layer_1.png") # sky
        bg1_tex = bg1_sprite.texture
        
        bg2_sprite = factory.from_image("assets/Map/background/background_layer_2.png") # far forest
        bg2_tex = bg2_sprite.texture

        bg3_sprite = factory.from_image("assets/Map/background/background_layer_3.png") # near forest
        bg3_tex = bg3_sprite.texture

    except Exception as e:
        print(f"Load sprite error: {e}")
        return

    # 1. init Map and decoration handler
    my_map = GameMap(TEST_LEVEL, DECO_MAP)
    deco_mgr = Decoration(renderer)

    # 2. init Camera
    camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)

    # 3. KHỞI TẠO PLAYER VÀ NPC (Thay cho FakePlayer)
    world = sdl2.ext.World()
    software_factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE) # Player cần Software factory
    
    player = Player(world, software_factory, 100, 350) # Spawn gần mặt đất
    npc_manager = NPCManager(software_factory, None, renderer.sdlrenderer)
    
    # Spawn NPC
    g1 = npc_manager.spawn_ghost(600, 350)
    make_npc_compatible(g1)
    s1 = npc_manager.spawn_shooter(900, 350)
    make_npc_compatible(s1)
    
    active_tornadoes = []
    active_walls = []

    # 4.  game loop
    running = True
    last_time = sdl2.SDL_GetTicks()
    
    while running:
        current_time = sdl2.SDL_GetTicks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time
        
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
            # Xử lý input sự kiện (Skills, Jump, Attack)
            if not handle_input(event, player, world, software_factory, renderer, active_tornadoes, active_walls, npc_manager):
                running = False
        
        # Update Logic
        keys = sdl2.SDL_GetKeyboardState(None)
        
        # Block Logic (S key)
        player.set_blocking(keys[sdl2.SDLK_s])
        
        # Movement Logic
        player.handle_movement(keys)
        
        # Player Update (Physics, Animation, Skills)
        player.update(dt, world, software_factory, None, active_tornadoes, active_walls, game_map=None)
        
        # Giới hạn Player trong Map
        if player.entity.sprite.x < 0:
            player.entity.sprite.x = 0
        if player.entity.sprite.x > my_map.width_pixel - 128:
            player.entity.sprite.x = my_map.width_pixel - 128
        
        # update Camera theo Player (dùng SDL_Rect để tương thích)
        player_rect = SDL_Rect(int(player.entity.sprite.x), int(player.entity.sprite.y), 128, 128)
        camera.update(player_rect, my_map.width_pixel)
        
        # Skill Updates
        alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
        for t in active_tornadoes[:]:
            update_q_logic(t, alive_npcs, dt)
            if not t.active: 
                t.delete()
                active_tornadoes.remove(t)
        
        for w in active_walls[:]:
            update_w_logic(w)
            if not w.active:
                w.delete()
                active_walls.remove(w)
                
        player.skill_e.update_dash(dt, alive_npcs)
        if player.skill_e.is_dashing: player.state = 'dashing_e'
        elif player.state == 'dashing_e' and not player.skill_e.is_dashing: player.state = 'idle'

        npc_manager.update_all(dt)

        # Render
        renderer.clear()
        sdl_renderer = renderer.sdlrenderer

        # RENDER BACKGROUND PARALLAX (GIỮ NGUYÊN)
        draw_bg(sdl_renderer, bg1_tex, camera.camera.x, 0.1) 
        draw_bg(sdl_renderer, bg2_tex, camera.camera.x, 0.4) 
        draw_bg(sdl_renderer, bg3_tex, camera.camera.x, 0.7)

        # render Map (GIỮ NGUYÊN)
        my_map.render(sdl_renderer, tileset_texture, deco_mgr, camera)
        
        # Render Skills (với camera offset)
        for t in active_tornadoes: 
             render_surface_to_texture(sdl_renderer, t.sprite.surface, 
                                       t.sprite.x - camera.camera.x, 
                                       t.sprite.y - camera.camera.y)
        for w in active_walls: 
             render_surface_to_texture(sdl_renderer, w.sprite.surface, 
                                       w.sprite.x - camera.camera.x, 
                                       w.sprite.y - camera.camera.y)
        
        # Render NPCs
        npc_manager.render_all()
        
        # Render Player (với camera offset)
        p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), 
                         int(player.entity.sprite.y - camera.camera.y), 
                         128, 128)
        p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, player.entity.sprite.surface)
        sdl2.SDL_RenderCopy(sdl_renderer, p_tex, None, p_dst)
        sdl2.SDL_DestroyTexture(p_tex)

        renderer.present()
        sdl2.SDL_Delay(1000 // FPS)

    npc_manager.cleanup()
    sdl2.ext.quit()

if __name__ == "__main__":
    run()