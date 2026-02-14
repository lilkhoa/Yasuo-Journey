import sys
import os
# Tính toán đường dẫn gốc từ vị trí file này (core/game.py)
current_file_path = os.path.abspath(__file__)
core_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(core_dir) # Lên 1 cấp để về root

sys.path.append(project_root)

import sdl2
import sdl2.ext
import sdl2.sdlttf
from settings import *
from world.map import GameMap
from world.interactable import Box
from world.decoration import Decoration
from world.interactable import Barrel, Chest, BARREL_RENDER_WIDTH, BARREL_RENDER_HEIGHT
from sdl2 import SDL_Rect, SDL_RenderCopy
from core.camera import Camera
from core.text_renderer import TextRenderer

# --- IMPORTS ---
from entities.player import Player
from entities.npc import NPCManager
from entities.boss import BossManager
from entities.projectile import ProjectileManager
from core.event import handle_input
from combat.skill_q import update_q_logic
from combat.skill_w import update_w_logic
from ui.hud import SkillBarHUD

from items.item import ItemManager, ItemType
from core.sound import get_sound_manager

# --- MAP DATA ---
TERRAIN_MAP = [
    "                                                  ",  
    "                                                  ", 
    "                                                  ", 
    "  2233                    2233                    ", 
    "          (- - 8 8 8 8 8 8        (- - 8 8 8 8 8 8", 
    "      [== 78 8 0 0 0 0 0 0    [== 78 8 0 0 0 0 0 0", 
    "-5===5------68 0 0 0 0 0 0-5= =5- - - 68 0 0 0 0 0", 
    "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ", 
]

DECO_MAP = [
    "                                                  ", 
    "    ff                                            ", 
    "                                                  ", 
    "                          S                       ", 
    "          g g              l      g g             ", 
    "      r   r                       r               ", 
    "                                                  ", 
    "                                                  ", 
]

INTERACT_MAP = [
    "                                                  ", 
    "                                                  ", 
    "   C                                              ", 
    "                                                  ", 
    "        b                     b                   ", 
    " B                                                ", 
    "                                                  ", 
    "                                                  ", 
]

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
    if surface is None: return
    texture = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, surface)
    if not texture: return 
    w, h = surface.w, surface.h
    dst_rect = sdl2.SDL_Rect(int(x), int(y), w, h)
    sdl2.SDL_RenderCopy(sdl_renderer, texture, None, dst_rect)
    sdl2.SDL_DestroyTexture(texture)

def draw_bg(renderer, texture, camera_x, speed_factor):
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
    sdl2.sdlttf.TTF_Init()
    
    window = sdl2.ext.Window("Samurai Adventure - Items Update", size=(WINDOW_WIDTH, WINDOW_HEIGHT))
    window.show()
    renderer = sdl2.ext.Renderer(window, flags=sdl2.SDL_RENDERER_PRESENTVSYNC)
    
    # --- FIX PATH CHO FACTORY ---
    # SpriteFactory mặc định không biết root ở đâu, ta cần truyền path đầy đủ nếu cần
    # Hoặc để nó tự tìm nếu CWD đúng. Nhưng ta sẽ dùng os.path.join cho chắc.
    factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
    
    sound_manager = get_sound_manager()
    sound_manager.initialize()
    sound_manager.load_npc_sounds()
    sound_manager.load_boss_sounds()

    # --- FIX PATH CHO FONT ---
    # Lấy đường dẫn tuyệt đối tới assets
    ASSETS_DIR = os.path.join(project_root, "assets")
    
    font_path = os.path.join(ASSETS_DIR, "fonts", "arial.ttf")
    if not os.path.exists(font_path):
        print(f"Warning: Font missing at {font_path}. Using fallback.")
        font_path = "C:\\Windows\\Fonts\\arial.ttf"
    
    text_renderer = TextRenderer(renderer.sdlrenderer, font_path, size=14)
    item_manager = ItemManager(renderer, text_renderer)

    try:
        # Helper function để load ảnh từ assets/Map/...
        def load_map_asset(subpath):
            full = os.path.join(ASSETS_DIR, "Map", subpath)
            if not os.path.exists(full):
                print(f"Error: Missing asset {full}")
                raise FileNotFoundError(full)
            return factory.from_image(full)

        tileset_sprite = load_map_asset("oak_woods_tileset.png")
        tileset_texture = tileset_sprite.texture

        bg1_tex = load_map_asset(os.path.join("background", "background_layer_1.png")).texture
        bg2_tex = load_map_asset(os.path.join("background", "background_layer_2.png")).texture
        bg3_tex = load_map_asset(os.path.join("background", "background_layer_3.png")).texture
        
        box_tileset_texture = load_map_asset(os.path.join("interactable_objects", "TX Village Props.png")).texture
        barrel_tileset_texture = load_map_asset(os.path.join("interactable_objects", "TX Village Props.png")).texture
        chest_tileset_texture = load_map_asset(os.path.join("interactable_objects", "TX Chest Animation.png")).texture

    except Exception as e:
        print(f"FATAL ERROR LOADING ASSETS: {e}")
        return

    my_map = GameMap(TERRAIN_MAP, DECO_MAP)
    deco_mgr = Decoration(renderer)
    camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)

    world = sdl2.ext.World()
    software_factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE) 
    
    boxes, barrels, chests = [], [], []

    for y, row in enumerate(INTERACT_MAP):
        for x, char in enumerate(row):
            world_x = x * TILE_SIZE
            grid_y_pos = (y * TILE_SIZE)

            if char == "B":
                boxes.append(Box(world_x, grid_y_pos, box_tileset_texture))
            elif char == "b":
                barrel_h, barrel_w = BARREL_RENDER_HEIGHT, BARREL_RENDER_WIDTH
                real_x = (world_x + TILE_SIZE // 2) - barrel_w // 2
                real_y = (grid_y_pos + TILE_SIZE) - barrel_h
                barrels.append(Barrel(real_x, real_y, barrel_tileset_texture, {}, text_renderer))
            elif char == 'C':
                chests.append(Chest(world_x, grid_y_pos, chest_tileset_texture, {}, text_renderer))

    player = Player(world, software_factory, 100, 350)
    projectile_manager = ProjectileManager(renderer.sdlrenderer)
    npc_manager = NPCManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager)
    boss_manager = BossManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager, camera)
    hud = SkillBarHUD(renderer.sdlrenderer, player)
    
    npc_ground_y = 500
    g1 = make_npc_compatible(npc_manager.spawn_ghost(350, npc_ground_y))
    g1.set_player(player)
    s1 = make_npc_compatible(npc_manager.spawn_shooter(550, npc_ground_y))
    s1.set_player(player)
    o1 = make_npc_compatible(npc_manager.spawn_onre(750, npc_ground_y))
    o1.set_player(player)
    boss = make_npc_compatible(boss_manager.spawn_boss(4500, npc_ground_y - 400))
    boss.set_player(player)

    # --- SPAWN ITEMS ---
    spawn_y = 480
    item_manager.spawn_item(200, spawn_y, ItemType.COIN)
    item_manager.spawn_item(250, spawn_y, ItemType.TEAR)
    item_manager.spawn_item(300, spawn_y, ItemType.HEALTH_POTION)
    item_manager.spawn_item(350, spawn_y, ItemType.GREAVES)
    item_manager.spawn_item(400, spawn_y, ItemType.BLOODTHIRSTER)
    item_manager.spawn_item(450, spawn_y, ItemType.INFINITY_EDGE)
    item_manager.spawn_item(500, spawn_y, ItemType.THORNMAIL)
    item_manager.spawn_item(550, spawn_y, ItemType.HOURGLASS)

    active_tornadoes, active_walls = [], []
    game_over, game_over_timer = False, 0
    running, last_time = True, sdl2.SDL_GetTicks()
    
    while running:
        current_time = sdl2.SDL_GetTicks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time
        
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT: running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_f:
                    for chest in chests: chest.interact()
                    item_manager.handle_interact_key(player)
            
            if not handle_input(event, player, world, software_factory, renderer, active_tornadoes, active_walls, npc_manager):
                running = False
        
        keys = sdl2.SDL_GetKeyboardState(None)
        player.set_blocking(keys[sdl2.SDLK_s])
        player.handle_movement(keys)
        player.update(dt, world, software_factory, None, active_tornadoes, active_walls, game_map=my_map, boxes=boxes)
        
        if player.entity.sprite.x < 0: player.entity.sprite.x = 0
        if player.entity.sprite.x > my_map.width_pixel - 128: player.entity.sprite.x = my_map.width_pixel - 128

        for box in boxes: box.update(dt, my_map)
        for barrel in barrels: barrel.update(dt)
        for chest in chests: chest.update(dt, player, [], renderer.sdlrenderer)
        item_manager.update(dt, player)

        player_rect = SDL_Rect(int(player.entity.sprite.x), int(player.entity.sprite.y), 128, 128)
        camera.update(player_rect, my_map.width_pixel)
        
        alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
        alive_bosses = boss_manager.get_alive_bosses()
        all_minions = []
        for b in alive_bosses: all_minions.extend([m for m in b.minions if m.health > 0])
        all_combat_targets = alive_npcs + alive_bosses + all_minions
        
        for t in active_tornadoes[:]:
            update_q_logic(t, all_combat_targets, dt)
            if not t.active: t.delete(); active_tornadoes.remove(t)
        for w in active_walls[:]:
            update_w_logic(w, all_combat_targets, projectile_manager.projectiles, dt)
            if not w.active: w.delete(); active_walls.remove(w)
                
        player.skill_e.update_dash(dt, all_combat_targets, boxes)
        if player.skill_e.is_dashing: player.state = 'dashing_e'
        elif player.state == 'dashing_e' and not player.skill_e.is_dashing: player.state = 'idle'

        npc_manager.update_all(dt, my_map)
        boss_manager.update_all(dt, my_map)
        projectile_manager.update_all(dt)
        
        if not game_over:
            # Collision Logic
            for p in projectile_manager.projectiles[:]:
                p_rect = sdl2.SDL_Rect(int(p.x), int(p.y), p.width, p.height)
                for b in boxes:
                    if sdl2.SDL_HasIntersection(p_rect, b.rect): p.on_hit(); break
            
            for p in projectile_manager.projectiles[:]:
                if p.check_collision(player): player.take_damage(p.damage); p.on_hit()
            
            for npc in alive_npcs:
                if hasattr(npc, 'is_attacking') and npc.is_attacking:
                    nx, ny, nw, nh = npc.get_bounds()
                    rng = getattr(npc, 'attack_range', 50)
                    atk_box = (nx + nw, ny, rng, nh) if npc.direction == 1 else (nx - rng, ny, rng, nh)
                    px, py, pw, ph = player.x, player.y, player.width, player.height
                    ax, ay, aw, ah = atk_box
                    if (ax < px+pw and ax+aw > px and ay < py+ph and ay+ah > py):
                        if not getattr(npc, '_hit_p', False):
                            npc._hit_p = True; player.take_damage(npc.damage)
                else: npc._hit_p = False
            
            for b in alive_bosses:
                if b.is_attacking and b.attack_type == 'melee':
                    bx, by, bw, bh = b.get_bounds()
                    rng = b.melee_range
                    atk_box = (bx + bw, by, rng, bh) if b.direction.value == 1 else (bx - rng, by, rng, bh)
                    px, py, pw, ph = player.x, player.y, player.width, player.height
                    ax, ay, aw, ah = atk_box
                    if (ax < px+pw and ax+aw > px and ay < py+ph and ay+ah > py):
                        if not getattr(b, '_hit_p', False):
                            b._hit_p = True; player.take_damage(b.melee_damage)
                else: b._hit_p = False

            if player.state == 'attacking':
                px, py, pw, ph = player.x, player.y, player.width, player.height
                rng = 60
                atk_box = (px + pw - 20, py + 20, rng, ph - 40) if player.facing_right else (px - rng + 20, py + 20, rng, ph - 40)
                ax, ay, aw, ah = atk_box
                for npc in alive_npcs:
                    if not getattr(player, f'_hit_n_{id(npc)}', False):
                        nx, ny, nw, nh = npc.get_bounds()
                        if (ax < nx+nw and ax+aw > nx and ay < ny+nh and ay+ah > ny):
                            setattr(player, f'_hit_n_{id(npc)}', True)
                            npc.take_damage(player.attack_damage)
                            player.on_hit_enemy(player.attack_damage)
                            if not npc.is_alive(): player.on_kill_enemy()
                for b in alive_bosses:
                    if not getattr(player, f'_hit_b_{id(b)}', False):
                        bx, by, bw, bh = b.get_bounds()
                        if (ax < bx+bw and ax+aw > bx and ay < by+bh and ay+ah > by):
                            setattr(player, f'_hit_b_{id(b)}', True)
                            b.take_damage(player.attack_damage)
                            player.on_hit_enemy(player.attack_damage)
                            if not b.is_alive(): player.on_kill_enemy()
            else:
                for n in npc_manager.npcs: 
                    if hasattr(player, f'_hit_n_{id(n)}'): delattr(player, f'_hit_n_{id(n)}')
                for b in boss_manager.bosses:
                    if hasattr(player, f'_hit_b_{id(b)}'): delattr(player, f'_hit_b_{id(b)}')

            if player.state == 'dead':
                game_over = True; game_over_timer = 3.0; print("Game Over")
        else:
            game_over_timer -= dt
            if game_over_timer <= 0:
                player.hp = player.max_hp; player.state = 'idle'; player.entity.sprite.position = (100, 350); game_over = False

        renderer.clear()
        sdl_ren = renderer.sdlrenderer
        draw_bg(sdl_ren, bg1_tex, camera.camera.x, 0.1) 
        draw_bg(sdl_ren, bg2_tex, camera.camera.x, 0.4) 
        draw_bg(sdl_ren, bg3_tex, camera.camera.x, 0.7)
        my_map.render(sdl_ren, tileset_texture, deco_mgr, camera)
        
        # Render Items
        item_manager.render(camera.camera.x, camera.camera.y, player)

        for t in active_tornadoes: render_surface_to_texture(sdl_ren, t.sprite.surface, t.sprite.x - camera.camera.x, t.sprite.y - camera.camera.y)
        for w in active_walls: render_surface_to_texture(sdl_ren, w.sprite.surface, w.sprite.x - camera.camera.x, w.sprite.y - camera.camera.y)
        for box in boxes: box.render(sdl_ren, camera)
        for barrel in barrels: barrel.render(sdl_ren, camera)
        for chest in chests: chest.render(sdl_ren, camera, player)

        npc_manager.render_all(camera.camera.x, camera.camera.y)
        boss_manager.render_all(camera.camera.x, camera.camera.y)
        projectile_manager.render_all(camera.camera.x, camera.camera.y)
        
        p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), int(player.entity.sprite.y - camera.camera.y), 128, 128)
        p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_ren, player.entity.sprite.surface)
        r, g, b = player.color_mod 
        if player.flash_timer > 0: r, g, b = (255, 100, 100)
        sdl2.SDL_SetTextureColorMod(p_tex, int(r), int(g), int(b))
        sdl2.SDL_RenderCopy(sdl_ren, p_tex, None, p_dst)
        sdl2.SDL_DestroyTexture(p_tex)
        
        hud.render()
        renderer.present()
        sdl2.SDL_Delay(1000 // FPS)

    hud.cleanup()
    npc_manager.cleanup()
    projectile_manager.cleanup()
    sdl2.ext.quit()

if __name__ == "__main__":
    run()