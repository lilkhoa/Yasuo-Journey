import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sdl2
import sdl2.ext
import sdl2.sdlttf
from settings import *
from world.map import GameMap
from world.interactable import Box
from world.decoration import Decoration
from world.item import DroppedItem
from world.interactable import Barrel, Chest, BARREL_RENDER_WIDTH, BARREL_RENDER_HEIGHT
from sdl2 import SDL_Rect, SDL_RenderCopy
from core.camera import Camera
from core.text_renderer import TextRenderer

# --- THÊM IMPORTS CHO PLAYER VÀ NPC ---
from entities.player import Player
from entities.npc import NPCManager
from entities.boss import BossManager
from entities.projectile import ProjectileManager
from core.event import handle_input
from combat.skill_q import update_q_logic
from combat.skill_w import update_w_logic
from ui.hud import SkillBarHUD
from ui.item_notification import ItemNotification, ItemNotificationSystem

# [MỚI] IMPORT ITEM
from items.item import ItemManager, ItemType

# Sound manager
from core.sound import get_sound_manager

# Long test map to test camera scroll: TERRAIN
TEST_LEVEL = [
    "                                                  ",  
    "                                                  ", 
    "                                                  ", 
    "  2233                    2233                    ", 
    "          (- - 8 8 8 8 8 8        (- - 8 8 8 8 8 8", 
    "      [== 78 8 0 0 0 0 0 0    [== 78 8 0 0 0 0 0 0", 
    "-5===5------68 0 0 0 0 0 0-5= =5- - - 68 0 0 0 0 0", 
    "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ", 
]

# DECO MAP (Mask Map)
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

# INTERACT MAP (Layer dành riêng cho vật thể tương tác)
# 'B' = Box (Thùng đẩy)
# 'b' = Barrel (Thùng phuy đập vỡ)
# 'C' = Chest (Rương)
INTERACT_MAP = [
    "                                                  ", 
    "                                                  ", 
    "   C                                               ", 
    "                                                  ", # Thùng đẩy trên cao
    "        b                         b               ", # Rương và Thùng phuy
    " B                                                ", 
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
    sound_manager = get_sound_manager()
    sound_manager.initialize()
    sound_manager.load_npc_sounds()
    sound_manager.load_boss_sounds()

    try:
        tileset_sprite = factory.from_image("assets/Map/oak_woods_tileset.png")
        tileset_texture = tileset_sprite.texture

        # Load 3 Background layers
        bg1_sprite = factory.from_image("assets/Map/background/background_layer_1.png")
        bg1_tex = bg1_sprite.texture
        bg2_sprite = factory.from_image("assets/Map/background/background_layer_2.png")
        bg2_tex = bg2_sprite.texture
        bg3_sprite = factory.from_image("assets/Map/background/background_layer_3.png")
        bg3_tex = bg3_sprite.texture
        
        # Loading pushable box
        box_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Village Props.png")
        box_tileset_texture = box_tileset_sprite.texture

        # Loading sprite sheet of barrel
        barrel_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Village Props.png")
        barrel_tileset_texture = barrel_tileset_sprite.texture

        # Loading sprite sheet of chest
        chest_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Chest Animation.png")
        chest_tileset_texture = chest_tileset_sprite.texture

        # --- LOAD ITEM ICONS ---
        coin_sprite = factory.from_image("assets/Map/items/Golden Coin.png")
        coin_texture = coin_sprite.texture

        tear_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Tear_of_the_Goddess.png")
        tear_texture = tear_sprite.texture

        health_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Health_Potion.png")
        health_texture = health_sprite.texture

        greaves_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Berserkers_Greaves.png")
        greaves_texture = greaves_sprite.texture

        bloodthirster_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Bloodthirster.png")
        bloodthirster_texture = bloodthirster_sprite.texture

        infinity_edge_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Infinity_Edge.png")
        infinity_edge_texture = infinity_edge_sprite.texture

        thornmail_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Thornmail.png")
        thornmail_texture = thornmail_sprite.texture

        hourglass_sprite = factory.from_image("assets/Map/LOL_Equipment/64x64_Zhonyas_Hourglass.png")
        hourglass_texture = hourglass_sprite.texture
        
        common_drop_table = {
            "coin": ("Coin", 32, 32, coin_texture),
            "tear": ("Tear of the Goddess", 32, 32, tear_texture),
            "heart": ("Health Potion", 32, 32, health_texture),
            "greaves": ("Berserker's Greaves", 32, 32, greaves_texture),
            "bloodthirster": ("Bloodthirster", 32, 32, bloodthirster_texture),
            "infinity_edge": ("Infinity Edge", 32, 32, infinity_edge_texture),
            "thornmail": ("Thornmail", 32, 32, thornmail_texture),
            "hourglass": ("Zhonya's Hourglass", 32, 32, hourglass_texture),
        }

    except Exception as e:
        print(f"Load sprite error: {e}")
        return

    # 1. init Map and decoration handler
    my_map = GameMap(TEST_LEVEL, DECO_MAP)
    deco_mgr = Decoration(renderer)

    # 2. init Camera
    camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)

    # 3. KHỞI TẠO PLAYER VÀ NPC
    world = sdl2.ext.World()
    software_factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE) 
    
    # 4. Boxes initialization
    boxes = []
    barrels = []
    chests = []
    dropped_items = []  # list manager dropped itemsc
    text_renderer = TextRenderer(renderer.sdlrenderer, "assets/fonts/arial.ttf", size=10)
    notif_system = ItemNotificationSystem(text_renderer)    

    for y, row in enumerate(INTERACT_MAP):
        for x, char in enumerate(row):
            # calculate the real position
            world_x = x * TILE_SIZE
            # align Y for box to lie on the top of the ground of this row
            # because height is (44 -> 24) * SCALE FACTOR
            grid_y_pos = (y * TILE_SIZE) # because we scale the block has the same size to the ground block

            if char == "B":
                new_box = Box(world_x, grid_y_pos, box_tileset_texture)
                boxes.append(new_box)
            
            elif char == "b":   # barrel
                barrel_h = BARREL_RENDER_HEIGHT  # value got from the Barrel class
                barrel_w = BARREL_RENDER_WIDTH

                real_x = (world_x + TILE_SIZE // 2) - barrel_w // 2
                real_y = (grid_y_pos + TILE_SIZE) - barrel_h

                new_barrel = Barrel(real_x, real_y, barrel_tileset_texture, common_drop_table, text_renderer)
                barrels.append(new_barrel)

            elif char == 'C':
                new_chest = Chest(world_x, grid_y_pos, chest_tileset_texture, common_drop_table, text_renderer)
                chests.append(new_chest)

    player = Player(world, software_factory, 100, 350) # Spawn gần mặt đất
    
    projectile_manager = ProjectileManager(renderer.sdlrenderer)
    npc_manager = NPCManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager)
    boss_manager = BossManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager, camera)
    
    hud = SkillBarHUD(renderer.sdlrenderer, player)
    
    npc_ground_y = 500
    
    g1 = npc_manager.spawn_ghost(350, npc_ground_y)
    g1.set_player(player)
    make_npc_compatible(g1)
    s1 = npc_manager.spawn_shooter(550, npc_ground_y)
    s1.set_player(player)
    make_npc_compatible(s1)
    o1 = npc_manager.spawn_onre(750, npc_ground_y)
    o1.set_player(player)
    make_npc_compatible(o1)

    # Boss spawn
    boss = boss_manager.spawn_boss(4500, npc_ground_y - 400)
    boss.set_player(player)
    make_npc_compatible(boss)

    active_tornadoes = []
    active_walls = []

    kill_count = 0
    game_over = False
    game_over_timer = 0

    # 4. game loop
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
            
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_f:
                    for chest in chests:
                        chest.interact()

                    for item in dropped_items:
                        item.interact(notif_system, player)

            # Xử lý input sự kiện (Skills, Jump, Attack)
            if not handle_input(event, player, world, software_factory, renderer, active_tornadoes, active_walls, npc_manager):
                running = False
        
        # Update Logic
        keys = sdl2.SDL_GetKeyboardState(None)
        player.set_blocking(keys[sdl2.SDLK_s])
        player.handle_movement(keys)
        player.update(dt, world, software_factory, None, active_tornadoes, active_walls, game_map=my_map, boxes=boxes)
        
        if player.entity.sprite.x < 0: player.entity.sprite.x = 0
        if player.entity.sprite.x > my_map.width_pixel - 128: player.entity.sprite.x = my_map.width_pixel - 128

        # Box updating
        for box in boxes:
            box.update(dt, my_map)

        # Barrel updating
        for barrel in barrels:
            barrel.update(dt)

        # Chest updating
        for chest in chests:
            chest.update(dt, player, dropped_items, renderer.sdlrenderer)
        
        # Item updating
        for item in dropped_items:
            item.update(dt, my_map, player)
        
        dropped_items = [item for item in dropped_items if not item.is_collected]

        notif_system.update()

        player_rect = SDL_Rect(int(player.entity.sprite.x), int(player.entity.sprite.y), 128, 128)
        camera.update(player_rect, my_map.width_pixel)
        
        # Skill Updates
        alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
        alive_bosses = boss_manager.get_alive_bosses()
        all_minions = []
        for boss in alive_bosses:
            all_minions.extend([m for m in boss.minions if m.health > 0])
        
        all_combat_targets = alive_npcs + alive_bosses + all_minions
        
        for t in active_tornadoes[:]:
            update_q_logic(t, all_combat_targets, dt)
            if not t.active: 
                t.delete()
                active_tornadoes.remove(t)
        
        for w in active_walls[:]:
            update_w_logic(w, all_combat_targets, projectile_manager.projectiles, dt)
            if not w.active:
                w.delete()
                active_walls.remove(w)
                
        player.skill_e.update_dash(dt, all_combat_targets, boxes)
        if player.skill_e.is_dashing: player.state = 'dashing_e'
        elif player.state == 'dashing_e' and not player.skill_e.is_dashing: player.state = 'idle'

        npc_manager.update_all(dt, my_map)
        boss_manager.update_all(dt, my_map)
        projectile_manager.update_all(dt)
        
        # ============== COMBAT COLLISION SYSTEM ==============
        if not game_over:
            # 0. PROJECTILE -> BOX
            for projectile in projectile_manager.projectiles[:]:
                proj_rect = sdl2.SDL_Rect(int(projectile.x), int(projectile.y), projectile.width, projectile.height)
                for box in boxes:
                    if sdl2.SDL_HasIntersection(proj_rect, box.rect):
                        projectile.on_hit()
                        break

            # 1. NPC PROJECTILE -> PLAYER
            for projectile in projectile_manager.projectiles[:]:
                if projectile.check_collision(player):
                    player.take_damage(projectile.damage)
                    projectile.on_hit()
                    print(f"[COMBAT] Player hit by projectile! HP: {int(player.hp)}/{player.max_hp}")
            
            # 2. NPC/BOSS/MINION MELEE ATTACK -> PLAYER
            for npc in alive_npcs:
                if hasattr(npc, 'is_attacking') and npc.is_attacking:
                    npc_x, npc_y, npc_w, npc_h = npc.get_bounds()
                    attack_range = getattr(npc, 'attack_range', 50)
                    
                    if npc.direction == 1:
                        attack_hitbox = (npc_x + npc_w, npc_y, attack_range, npc_h)
                    else:
                        attack_hitbox = (npc_x - attack_range, npc_y, attack_range, npc_h)
                    
                    px, py, pw, ph = player.x, player.y, player.width, player.height
                    ax, ay, aw, ah = attack_hitbox
                    if (ax < px + pw and ax + aw > px and ay < py + ph and ay + ah > py):
                        if not getattr(npc, '_attack_hit_player', False):
                            npc._attack_hit_player = True
                            player.take_damage(npc.damage)
                            print(f"[COMBAT] Player melee'd by NPC! HP: {int(player.hp)}/{player.max_hp}")
                else:
                    npc._attack_hit_player = False
            
            for boss in alive_bosses:
                if boss.is_attacking and boss.attack_type == 'melee':
                    boss_x, boss_y, boss_w, boss_h = boss.get_bounds()
                    if boss.direction.value == 1:
                        attack_hitbox = (boss_x + boss_w, boss_y, boss.melee_range, boss_h)
                    else:
                        attack_hitbox = (boss_x - boss.melee_range, boss_y, boss.melee_range, boss_h)
                    
                    px, py, pw, ph = player.x, player.y, player.width, player.height
                    ax, ay, aw, ah = attack_hitbox
                    
                    if (ax < px + pw and ax + aw > px and ay < py + ph and ay + ah > py):
                        if not getattr(boss, '_attack_hit_player', False):
                            boss._attack_hit_player = True
                            player.take_damage(boss.melee_damage)
                            print(f"[COMBAT] Player hit by BOSS melee! HP: {int(player.hp)}/{player.max_hp}")
                else:
                    boss._attack_hit_player = False
            
            # 3. PLAYER ATTACK -> NPC/BOSS/MINION
            if player.state == 'attacking':
                px, py, pw, ph = player.x, player.y, player.width, player.height
                player_attack_range = 60
                
                if player.facing_right:
                    attack_hitbox = (px + pw - 20, py + 20, player_attack_range, ph - 40)
                else:
                    attack_hitbox = (px - player_attack_range + 20, py + 20, player_attack_range, ph - 40)
                
                # Hit Barrels
                atk_rect = sdl2.SDL_Rect(*attack_hitbox)    
                for barrel in barrels:
                    if not barrel.is_broken:
                        if sdl2.SDL_HasIntersection(atk_rect, barrel.get_bounds()):
                            barrel.take_damage(1, dropped_items, renderer.sdlrenderer)
                    
                # Hit NPCs
                for npc in alive_npcs:
                    if not getattr(player, '_attack_hit_npc_' + str(id(npc)), False):
                        nx, ny, nw, nh = npc.get_bounds()
                        ax, ay, aw, ah = attack_hitbox
                        if (ax < nx + nw and ax + aw > nx and ay < ny + nh and ay + ah > ny):
                            setattr(player, '_attack_hit_npc_' + str(id(npc)), True)
                            npc.take_damage(player.attack_damage) # Sử dụng attack_damage mới (có buff)
                            player.on_hit_enemy(player.attack_damage)
                            print(f"[COMBAT] Player hit NPC! NPC HP: {npc.health}")
                            if not npc.is_alive():
                                kill_count += 1
                                player.on_kill_enemy()
                                print(f"[COMBAT] NPC killed! Total kills: {kill_count}")
                
                # Hit Bosses
                for boss in alive_bosses:
                    if not getattr(player, '_attack_hit_boss_' + str(id(boss)), False):
                        bx, by, bw, bh = boss.get_bounds()
                        ax, ay, aw, ah = attack_hitbox
                        if (ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by):
                            setattr(player, '_attack_hit_boss_' + str(id(boss)), True)
                            boss.take_damage(player.attack_damage)
                            player.on_hit_enemy(player.attack_damage)
                            print(f"[COMBAT] Player hit BOSS! Boss HP: {boss.health}/{boss.max_health}")
                            if not boss.is_alive():
                                kill_count += 1
                                player.on_kill_enemy()
                                print(f"[COMBAT] *** BOSS DEFEATED! *** Total kills: {kill_count}")
                
                # Hit Minions
                for minion in all_minions:
                    if not getattr(player, '_attack_hit_minion_' + str(id(minion)), False):
                        mx, my, mw, mh = minion.get_bounds()
                        ax, ay, aw, ah = attack_hitbox
                        if (ax < mx + mw and ax + aw > mx and ay < my + mh and ay + ah > my):
                            setattr(player, '_attack_hit_minion_' + str(id(minion)), True)
                            minion.take_damage(player.attack_damage)
                            player.on_hit_enemy(player.attack_damage)
                            print(f"[COMBAT] Player hit Boss Minion! Minion HP: {minion.health}")
                            if minion.health <= 0:
                                kill_count += 1
                                player.on_kill_enemy()
                                print(f"[COMBAT] Minion killed! Total kills: {kill_count}")
            else:
                for npc in npc_manager.npcs:
                    if hasattr(player, '_attack_hit_npc_' + str(id(npc))):
                        delattr(player, '_attack_hit_npc_' + str(id(npc)))
                for boss in boss_manager.bosses:
                    if hasattr(player, '_attack_hit_boss_' + str(id(boss))):
                        delattr(player, '_attack_hit_boss_' + str(id(boss)))
                    for minion in boss.minions:
                        if hasattr(player, '_attack_hit_minion_' + str(id(minion))):
                            delattr(player, '_attack_hit_minion_' + str(id(minion)))
            
            # 4. CHECK PLAYER DEATH
            if player.state == 'dead':
                game_over = True
                game_over_timer = 3.0
                print("[GAME] Player died! Game Over in 3 seconds...")
        
        else:
            game_over_timer -= dt
            if game_over_timer <= 0:
                player.hp = player.max_hp
                player.stamina = player.max_stamina
                player.state = 'idle'
                player.entity.sprite.position = (100, 350)
                player.is_blocking = False
                player.invincible = False
                game_over = False
                print(f"[GAME] Player respawned! Kills: {kill_count}")

        # Render
        renderer.clear()
        sdl_renderer = renderer.sdlrenderer

        draw_bg(sdl_renderer, bg1_tex, camera.camera.x, 0.1) 
        draw_bg(sdl_renderer, bg2_tex, camera.camera.x, 0.4) 
        draw_bg(sdl_renderer, bg3_tex, camera.camera.x, 0.7)

        my_map.render(sdl_renderer, tileset_texture, deco_mgr, camera)
        
        # Render Skills
        for t in active_tornadoes: 
             render_surface_to_texture(sdl_renderer, t.sprite.surface, 
                                       t.sprite.x - camera.camera.x, 
                                       t.sprite.y - camera.camera.y)
        for w in active_walls: 
             render_surface_to_texture(sdl_renderer, w.sprite.surface, 
                                       w.sprite.x - camera.camera.x, 
                                       w.sprite.y - camera.camera.y)
        
        for box in boxes:
            box.render(sdl_renderer, camera)

        # Barrel and chest renderering
        for barrel in barrels:
            barrel.render(sdl_renderer, camera)
        
        for chest in chests:
            chest.render(sdl_renderer, camera, player)

        for item in dropped_items:
            item.render(sdl_renderer, camera, player)

        notif_system.render(sdl_renderer)

        # Render NPCs
        npc_manager.render_all(camera.camera.x, camera.camera.y)
        boss_manager.render_all(camera.camera.x, camera.camera.y)
        projectile_manager.render_all(camera.camera.x, camera.camera.y)
        
        # Render Player (với camera offset)
        p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), 
                         int(player.entity.sprite.y - camera.camera.y), 
                         128, 128)
        p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, player.entity.sprite.surface)
        
        # [CẬP NHẬT] PLAYER COLOR MOD (Hỗ trợ Buff Items + Red Flash)
        # Nếu có Flash (bị đánh) -> Ưu tiên màu đỏ
        # Nếu không -> Dùng màu buff (tím, vàng, hoặc trắng mặc định)
        r, g, b = player.color_mod 
        if player.flash_timer > 0:
            r, g, b = (255, 100, 100) # Tint Red
        
        sdl2.SDL_SetTextureColorMod(p_tex, int(r), int(g), int(b))
        
        sdl2.SDL_RenderCopy(sdl_renderer, p_tex, None, p_dst)
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