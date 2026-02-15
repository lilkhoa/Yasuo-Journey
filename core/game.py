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
from world.checkpoint import CheckpointStatue
from items.item import DroppedItem, ItemType, ItemCategory, ITEM_REGISTRY
from world.interactable import Barrel, Chest, BARREL_RENDER_WIDTH, BARREL_RENDER_HEIGHT
from world.matrix_map import TERRAIN_MAP, DECO_MAP, INTERACT_MAP, NPC_MAP
from sdl2 import SDL_Rect, SDL_RenderCopy
from core.camera import Camera
from core.text_renderer import TextRenderer

# --- IMPORTS ENTITIES ---
from entities.player import Player
from entities.npc import NPCManager
from entities.boss import BossManager
from entities.projectile import ProjectileManager
from core.event import handle_input
from combat.skill_q import update_q_logic
from combat.skill_w import update_w_logic
from ui.hud import SkillBarHUD
from ui.item_notification import ItemNotification, ItemNotificationSystem

# --- IMPORT ITEM & MENU ---
from ui.menu import GameMenu, MenuState

# Sound manager
from core.sound import get_sound_manager

# --- HELPER CLASSES ---
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
    window = sdl2.ext.Window("Project Game Demo", size=(WINDOW_WIDTH, WINDOW_HEIGHT))
    window.show()
    renderer = sdl2.ext.Renderer(window, flags=sdl2.SDL_RENDERER_PRESENTVSYNC)
    factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
    
    # Init Sound
    sound_manager = get_sound_manager()
    sound_manager.initialize()
    sound_manager.load_player_sounds()
    sound_manager.load_npc_sounds()
    sound_manager.load_boss_sounds()
    sound_manager.load_game_sounds()
    sound_manager.load_item_sounds()
    
    if sound_manager.get_sound("statue_process"):
        sound_manager.set_volume("statue_process", 128) # Max volume
    if sound_manager.get_sound("statue_click"):
        sound_manager.set_volume("statue_click", 128)   # Max volume

    if sound_manager.load_background_music():
        sound_manager.play_music(loops=-1)
    else:
        print("[AUDIO] Warning: Could not load background music")

    try:
        # --- LOADING ASSETS ---
        tileset_sprite = factory.from_image("assets/Map/oak_woods_tileset.png")
        tileset_texture = tileset_sprite.texture

        bg1_sprite = factory.from_image("assets/Map/background/background_layer_1.png")
        bg1_tex = bg1_sprite.texture
        bg2_sprite = factory.from_image("assets/Map/background/background_layer_2.png")
        bg2_tex = bg2_sprite.texture
        bg3_sprite = factory.from_image("assets/Map/background/background_layer_3.png")
        bg3_tex = bg3_sprite.texture
        
        box_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Village Props.png")
        box_tileset_texture = box_tileset_sprite.texture

        barrel_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Village Props.png")
        barrel_tileset_texture = barrel_tileset_sprite.texture

        chest_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Chest Animation.png")
        chest_tileset_texture = chest_tileset_sprite.texture

        # Load Item Icons
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

        # Load statue texture
        statue_sprite = factory.from_image("assets/Map/interactable_objects/inazuma_statue.png")
        statue_texture = statue_sprite.texture

    except Exception as e:
        print(f"Load sprite error: {e}")
        return

    common_drop_table = {
        ItemType.COIN: ("Coin", 32, 32, coin_texture),
        ItemType.TEAR: ("Tear of the Goddess", 32, 32, tear_texture),
        ItemType.HEALTH_POTION: ("Health Potion", 32, 32, health_texture),
        ItemType.GREAVES: ("Berserker's Greaves", 32, 32, greaves_texture),
        ItemType.BLOODTHIRSTER: ("Bloodthirster", 32, 32, bloodthirster_texture),
        ItemType.INFINITY_EDGE: ("Infinity Edge", 32, 32, infinity_edge_texture),
        ItemType.THORNMAIL: ("Thornmail", 32, 32, thornmail_texture),
        ItemType.HOURGLASS: ("Zhonya's Hourglass", 32, 32, hourglass_texture),
    }

    icon_map = {
        ItemType.COIN: coin_texture,
        'COIN_ICON': coin_texture, 
        ItemType.HEALTH_POTION: health_texture,
        ItemType.TEAR: tear_texture,
        ItemType.GREAVES: greaves_texture,
        ItemType.BLOODTHIRSTER: bloodthirster_texture,
        ItemType.INFINITY_EDGE: infinity_edge_texture,
        ItemType.THORNMAIL: thornmail_texture,
        ItemType.HOURGLASS: hourglass_texture,
    }

    # --- INIT GAME WORLD ---
    my_map = GameMap(TERRAIN_MAP, DECO_MAP)
    deco_mgr = Decoration(renderer)
    camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
    world = sdl2.ext.World()
    software_factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE) 
    
    boxes = []
    barrels = []
    chests = []
    dropped_items = []
    text_renderer = TextRenderer(renderer.sdlrenderer, "assets/fonts/arial.ttf", size=10)
    notif_system = ItemNotificationSystem(text_renderer)    

    collect_timer = COLLECT_INTERVAL

    checkpoints = []
    # Variable to store revive data
    last_checkpoint_data = None
    last_checkpoint_pos = None

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
                barrels.append(Barrel(real_x, real_y, barrel_tileset_texture, common_drop_table, text_renderer))

            elif char == 'C':
                chests.append(Chest(world_x, grid_y_pos, chest_tileset_texture, common_drop_table, text_renderer))

            elif char == 'P':
                statue = CheckpointStatue(world_x, grid_y_pos, statue_texture, text_renderer)
                statue.set_sounds(
                    sound_manager.get_sound("statue_click"),
                    sound_manager.get_sound("statue_process")
                )
                checkpoints.append(statue)


    # --- INIT PLAYER ---
    player = Player(world, software_factory, 100, 350, sound_manager, renderer_ptr=renderer.sdlrenderer)
    
    projectile_manager = ProjectileManager(renderer.sdlrenderer)
    npc_manager = NPCManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager)
    boss_manager = BossManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager, camera)
    # Create Icon Map for HUD
    icon_map = {}
    for key, val in common_drop_table.items():
        # val = (name, w, h, texture)
        icon_map[key] = val[3]
    
    # Add special icons
    icon_map["COIN_ICON"] = coin_texture

    hud = SkillBarHUD(renderer.sdlrenderer, player, icon_map=icon_map)
    
    def drop_coin_on_death(entity, num_coins=1):
        coin_name, coin_w, coin_h, coin_tex = common_drop_table[ItemType.COIN]
        ex, ey, ew, eh = entity.get_bounds()
        for i in range(num_coins):
            offset_x = (i - num_coins//2) * 20 if num_coins > 1 else 0
            coin_item = DroppedItem(
                ex + ew/2 + offset_x, ey + eh/2, coin_tex, coin_w, coin_h,
                text_renderer, ItemType.COIN, coin_name
            )
            dropped_items.append(coin_item)
        sound_manager.play_sound("item_pop")

    for y, row in enumerate(NPC_MAP):
        for x, char in enumerate(row):
            if char == ' ': continue
            world_x, grid_y_pos = x * TILE_SIZE, y * TILE_SIZE
            if char == 'G':
                npc = npc_manager.spawn_ghost(world_x, grid_y_pos)
                npc.set_player(player); npc.on_death_callback = lambda n: drop_coin_on_death(n, 1)
                make_npc_compatible(npc)
            elif char == 'S':
                npc = npc_manager.spawn_shooter(world_x, grid_y_pos)
                npc.set_player(player); npc.on_death_callback = lambda n: drop_coin_on_death(n, 1)
                make_npc_compatible(npc)
            elif char == 'O':
                npc = npc_manager.spawn_onre(world_x, grid_y_pos)
                npc.set_player(player); npc.on_death_callback = lambda n: drop_coin_on_death(n, 1)
                make_npc_compatible(npc)
            elif char == 'B':
                boss = boss_manager.spawn_boss(world_x, grid_y_pos - 400)
                boss.set_player(player); boss.minion_death_callback = lambda m: drop_coin_on_death(m, 1)
                make_npc_compatible(boss)

    active_tornadoes = []
    active_walls = []
    kill_count = 0
    game_over = False
    game_over_timer = 0
    game_over_sound_played = False
    
    boss_encountered = False
    boss_music_playing = False
    boss_fight_text_timer = 0.0
    boss_fight_text_duration = 2.0
    
    victory = False
    victory_timer = 0
    victory_text_duration = 3.0
    victory_sound_played = False
    
    # Fade to black variables
    fade_active = False
    fade_alpha = 0
    fade_duration = 2.0  # 2 seconds to fade to black
    fade_timer = 0.0

    game_menu = GameMenu(renderer.sdlrenderer, WINDOW_WIDTH, WINDOW_HEIGHT)

    # --- MAIN LOOP ---
    running = True
    last_time = sdl2.SDL_GetTicks()
    
    while running:
        current_time = sdl2.SDL_GetTicks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time
        
        # Update menu background animation
        game_menu.update(dt)
        
        events = sdl2.ext.get_events()
        
        # 1. MENU INPUT
        menu_action = game_menu.handle_input(events)
        if menu_action == "QUIT_GAME": running = False
        elif menu_action == "START_GAME": pass
        elif menu_action == "UPDATE_VOLUME":
            music_volume = int((game_menu.get_volume()[0] / 100.0) * 128)
            sfx_volume = int((game_menu.get_volume()[1] / 100.0) * 128)
            sound_manager.set_music_volume(music_volume)
            sound_manager.set_master_volume(sfx_volume)


        # 2. GAME INPUT
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
            
            if game_menu.state == MenuState.GAME_PLAYING:
                if event.type == sdl2.SDL_KEYDOWN:
                    key = event.key.keysym.sym
                    mod = event.key.keysym.mod
                    
                    if key == sdl2.SDLK_f:
                        for chest in chests: 
                            if collect_timer <= 0: 
                                if chest.interact():
                                    collect_timer = COLLECT_INTERVAL
                                    break
                        
                        for item in dropped_items: 
                            if collect_timer <= 0:
                                if item.interact(notif_system, player):
                                    collect_timer = COLLECT_INTERVAL
                                    if sound_manager:
                                        sound_manager.play_sound("item_pickup")
                                    break

                        for statue in checkpoints:
                            if collect_timer <= 0:
                                saved_data = statue.interact(player)
                                if saved_data: 
                                    # 1. store revive data
                                    last_checkpoint_data = saved_data

                                    # 2. Store revive spawn pos
                                    last_checkpoint_pos = (statue.x + statue.width//2 - 64, y + statue.height - 128)
                                    
                                    # 3. reset collect timer
                                    collect_timer = COLLECT_INTERVAL
                                    break
                    
                    # [MASTERY TRIGGER] Ctrl + 6
                    if key == sdl2.SDLK_6 and (mod & sdl2.KMOD_CTRL):
                        player.trigger_mastery()

                    # PHÍM 1, 2, 3: Dùng Consumable
                    elif key == sdl2.SDLK_1:
                        item_type = player.use_consumable(0)
                        if item_type:
                            sound_manager.play_sound(item_type.name)
                        else:
                            print("Slot 1 Empty")    
                    elif key == sdl2.SDLK_2:
                        item_type = player.use_consumable(1)
                        if item_type:
                            sound_manager.play_sound(item_type.name)
                    elif key == sdl2.SDLK_3:
                        item_type = player.use_consumable(2)
                        if item_type:
                            sound_manager.play_sound(item_type.name)

                if not handle_input(event, player, world, software_factory, renderer, active_tornadoes, active_walls, npc_manager):
                    running = False
            
            collect_timer -= dt
        
        # 2.5. FADE UPDATE
        if fade_active:
            fade_timer += dt
            fade_alpha = int((fade_timer / fade_duration) * 255)
            if fade_alpha > 255:
                fade_alpha = 255
            
            if fade_timer >= fade_duration:
                # Fade complete - return to main menu and reset game state
                fade_active = False
                fade_alpha = 0
                fade_timer = 0.0
                game_menu.state = MenuState.MAIN_MENU
                game_menu.selected_index = 0
                
                # Reset game state
                player.hp = player.max_hp
                player.stamina = player.max_stamina
                player.state = 'idle'
                player.entity.sprite.position = (100, 350)
                player.is_blocking = False
                player.invincible = False
                game_over = False
                game_over_sound_played = False
                victory = False
                victory_sound_played = False
                victory_timer = 0
                game_over_timer = 0
                boss_encountered = False
                
                # Switch back to normal music
                if boss_music_playing:
                    sound_manager.switch_to_normal_music(fade_out_ms=1000, fade_in_ms=1000)
                    boss_music_playing = False
        
        # 3. UPDATE
        if game_menu.state == MenuState.GAME_PLAYING:
            keys = sdl2.SDL_GetKeyboardState(None)
            all_obstacles = boxes + [b for b in barrels if not b.is_broken]

            player.set_blocking(keys[sdl2.SDLK_s])
            player.handle_movement(keys)
            player.update(dt, world, software_factory, None, active_tornadoes, active_walls, game_map=my_map, boxes=all_obstacles)
            
            if player.entity.sprite.x < 0: player.entity.sprite.x = 0
            if player.entity.sprite.x > my_map.width_pixel - 128: player.entity.sprite.x = my_map.width_pixel - 128

            for box in boxes: box.update(dt, my_map)
            for barrel in barrels: barrel.update(dt, my_map)
            for chest in chests: chest.update(dt, player, dropped_items, renderer.sdlrenderer)
            for item in dropped_items: item.update(dt, my_map, player)
            for statue in checkpoints:
                statue.update(dt, player)
            dropped_items = [item for item in dropped_items if not item.is_collected]

            notif_system.update()

            player_rect = SDL_Rect(int(player.entity.sprite.x), int(player.entity.sprite.y), 128, 128)
            camera.update(player_rect, my_map.width_pixel)
            
            # Combat Logic
            alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
            alive_bosses = boss_manager.get_alive_bosses()
            all_minions = []
            for boss in alive_bosses: all_minions.extend([m for m in boss.minions if m.health > 0])
            
            # Boss Music & Text
            if not boss_encountered and alive_bosses:
                for boss in alive_bosses:
                    if boss.is_on_screen():
                        boss_encountered = True
                        boss_fight_text_timer = boss_fight_text_duration
                        sound_manager.switch_to_boss_music(fade_out_ms=1000, fade_in_ms=1000)
                        boss_music_playing = True
                        break
            
            if boss_music_playing:
                boss_on_screen = any(boss.is_on_screen() for boss in alive_bosses)
                if not boss_on_screen:
                    sound_manager.switch_to_normal_music(fade_out_ms=1000, fade_in_ms=1000)
                    boss_music_playing = False
            
            if boss_fight_text_timer > 0: boss_fight_text_timer -= dt
            
            # Victory Check
            if boss_encountered and not victory and len(alive_bosses) == 0:
                victory = True
                victory_timer = victory_text_duration
                if not victory_sound_played:
                    sound_manager.play_sound("victory")
                    victory_sound_played = True
            if victory_timer > 0:
                victory_timer -= dt
                if victory_timer <= 0 and not fade_active:
                    # Start fade to black after victory text
                    fade_active = True
                    fade_timer = 0.0
                    fade_alpha = 0
            
            all_combat_targets = alive_npcs + alive_bosses + all_minions
            
            for t in active_tornadoes[:]:
                update_q_logic(t, all_combat_targets, dt)
                if not t.active: t.delete(); active_tornadoes.remove(t)
            
            for w in active_walls[:]:
                update_w_logic(w, all_combat_targets, projectile_manager.projectiles, dt)
                if not w.active: w.delete(); active_walls.remove(w)
                    
            player.skill_e.update_dash(dt, all_combat_targets, all_obstacles, my_map)
            if player.skill_e.is_dashing: player.state = 'dashing_e'
            elif player.state == 'dashing_e' and not player.skill_e.is_dashing: player.state = 'idle'

            npc_manager.update_all(dt, my_map)
            boss_manager.update_all(dt, my_map)
            projectile_manager.update_all(dt)
            
            # Collision Logic
            if not game_over:
                # Projectile Hit
                for projectile in projectile_manager.projectiles[:]:
                    proj_rect = sdl2.SDL_Rect(int(projectile.x), int(projectile.y), projectile.width, projectile.height)
                    for box in boxes:
                        if sdl2.SDL_HasIntersection(proj_rect, box.rect): projectile.on_hit(); break
                    if projectile.active:
                        for barrel in barrels:
                            if not barrel.is_broken and sdl2.SDL_HasIntersection(proj_rect, barrel.rect): projectile.on_hit(); break

                for projectile in projectile_manager.projectiles[:]:
                    if projectile.check_collision(player):
                        player.take_damage(projectile.damage); projectile.on_hit()
                
                # NPC Melee Hit
                for npc in alive_npcs:
                    if hasattr(npc, 'is_attacking') and npc.is_attacking:
                        nx, ny, nw, nh = npc.get_bounds()
                        ar = getattr(npc, 'attack_range', 50)
                        hitbox = (nx+nw, ny, ar, nh) if npc.direction == 1 else (nx-ar, ny, ar, nh)
                        px, py, pw, ph = player.x, player.y, player.width, player.height
                        ax, ay, aw, ah = hitbox
                        if (ax < px+pw and ax+aw > px and ay < py+ph and ay+ah > py):
                            if not getattr(npc, '_attack_hit_player', False):
                                npc._attack_hit_player = True; player.take_damage(npc.damage)
                    else: npc._attack_hit_player = False
                
                # Boss Melee Hit
                for boss in alive_bosses:
                    if boss.is_attacking and boss.attack_type == 'melee':
                        bx, by, bw, bh = boss.get_bounds()
                        hitbox = (bx+bw, by, boss.melee_range, bh) if boss.direction.value == 1 else (bx-boss.melee_range, by, boss.melee_range, bh)
                        px, py, pw, ph = player.x, player.y, player.width, player.height
                        ax, ay, aw, ah = hitbox
                        if (ax < px+pw and ax+aw > px and ay < py+ph and ay+ah > py):
                            if not getattr(boss, '_attack_hit_player', False):
                                boss._attack_hit_player = True; player.take_damage(boss.melee_damage)
                    else: boss._attack_hit_player = False
                
                # Player Hit Enemies
                if player.state == 'attacking':
                    if not hasattr(player, '_attack_hit_anything'): player._attack_hit_anything = False
                    bx, by, bw, bh = player.get_hitbox().x, player.get_hitbox().y, player.get_hitbox().w, player.get_hitbox().h
                    ar = 50
                    atk_rect = sdl2.SDL_Rect(int(bx+bw if player.facing_right else bx-ar), int(by), ar, bh)
                    
                    for barrel in barrels:
                        if not barrel.is_broken and sdl2.SDL_HasIntersection(atk_rect, barrel.get_bounds()):
                            barrel.take_damage(1, dropped_items, renderer.sdlrenderer)
                            if not player._attack_hit_anything:
                                sound_manager.play_sound("player_auto_barrel"); player._attack_hit_anything = True
                    
                    for enemy in all_combat_targets:
                        ex, ey, ew, eh = enemy.get_bounds()
                        enemy_rect = sdl2.SDL_Rect(int(ex), int(ey), int(ew), int(eh))
                        if sdl2.SDL_HasIntersection(atk_rect, enemy_rect):
                            attr_name = f'_attack_hit_{id(enemy)}'
                            if not getattr(player, attr_name, False):
                                setattr(player, attr_name, True)
                                enemy.take_damage(player.attack_damage); player.on_hit_enemy(player.attack_damage)
                                if not player._attack_hit_anything:
                                    sound_manager.play_sound("player_auto_npc"); player._attack_hit_anything = True
                                if (hasattr(enemy, 'is_alive') and not enemy.is_alive()) or (hasattr(enemy, 'health') and enemy.health <= 0):
                                    kill_count += 1; player.on_kill_enemy()
                else:
                    if hasattr(player, '_attack_hit_anything'):
                        if not player._attack_hit_anything: sound_manager.play_sound("player_auto_miss")
                        delattr(player, '_attack_hit_anything')
                    for enemy in all_combat_targets:
                        attr_name = f'_attack_hit_{id(enemy)}'
                        if hasattr(player, attr_name): delattr(player, attr_name)

                if player.state == 'dead':
                    game_over = True; game_over_timer = 3.0
                    if not game_over_sound_played:
                        sound_manager.play_sound("game_over"); game_over_sound_played = True

                
                if player.state == 'dead' and player.dead_animation_complete:
                    # revive immediately to test
                    if last_checkpoint_data and last_checkpoint_pos:
                        # CASE 1: Có Checkpoint -> Load lại trạng thái cũ
                        spawn_x, spawn_y = last_checkpoint_pos
                        player.load_save_data(last_checkpoint_data, spawn_x, spawn_y)
                    
                    else:
                        # CASE 2: Không có Checkpoint -> Reset về đầu map
                        print("[SYSTEM] No checkpoint. Restarting level...")
                        # Reset thủ công hoặc load lại scene
                        player.hp = player.max_hp
                        player.entity.sprite.x = 100
                        player.entity.sprite.y = 350
                        player.state = 'idle'
                        player.is_blocking = False
                        player.dead_animation_complete = False

            else:
                game_over_timer -= dt
                if game_over_timer <= 0 and not fade_active:
                    # Start fade to black after game over text
                    fade_active = True
                    fade_timer = 0.0
                    fade_alpha = 0

        # --- RENDER ---
        renderer.clear()
        sdl_renderer = renderer.sdlrenderer

        if game_menu.state == MenuState.GAME_PLAYING or game_menu.state == MenuState.PAUSE:
            draw_bg(sdl_renderer, bg1_tex, camera.camera.x, 0.1) 
            draw_bg(sdl_renderer, bg2_tex, camera.camera.x, 0.4) 
            draw_bg(sdl_renderer, bg3_tex, camera.camera.x, 0.7)

            my_map.render(sdl_renderer, tileset_texture, deco_mgr, camera)
            
            for t in active_tornadoes: 
                 render_surface_to_texture(sdl_renderer, t.sprite.surface, t.sprite.x - camera.camera.x, t.sprite.y - camera.camera.y)
            for w in active_walls: 
                 render_surface_to_texture(sdl_renderer, w.sprite.surface, w.sprite.x - camera.camera.x, w.sprite.y - camera.camera.y)
            
            for box in boxes: box.render(sdl_renderer, camera)
            for barrel in barrels: barrel.render(sdl_renderer, camera)
            for chest in chests: chest.render(sdl_renderer, camera, player)
            for item in dropped_items: item.render(sdl_renderer, camera, player)
            for statue in checkpoints:
                statue.render(sdl_renderer, camera)

            notif_system.render(sdl_renderer)

            npc_manager.render_all(camera.camera.x, camera.camera.y)
            boss_manager.render_all(camera.camera.x, camera.camera.y)
            projectile_manager.render_all(camera.camera.x, camera.camera.y)
            
            # Render Player
            p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), int(player.entity.sprite.y - camera.camera.y), 128, 128)
            p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, player.entity.sprite.surface)
            r, g, b = player.color_mod 
            if player.flash_timer > 0: r, g, b = (255, 100, 100)
            sdl2.SDL_SetTextureColorMod(p_tex, int(r), int(g), int(b))
            sdl2.SDL_RenderCopy(sdl_renderer, p_tex, None, p_dst)
            sdl2.SDL_DestroyTexture(p_tex)
            
            # [MASTERY RENDER]
            player.render(sdl_renderer, camera.camera.x, camera.camera.y)
            
            hud.render()

            if boss_fight_text_timer > 0:
                if not hasattr(run, 'boss_text_renderer'):
                    run.boss_text_renderer = TextRenderer(sdl_renderer, "assets/fonts/arial.ttf", size=72)
                run.boss_text_renderer.renderer_text("BOSS FIGHT", WINDOW_WIDTH//2, WINDOW_HEIGHT//3, color=(255, 50, 50), draw_bg=True, bg_color=(0, 0, 0, 200), radius=15)
            
            if game_over and game_over_timer > 0:
                if not hasattr(run, 'game_over_text_renderer'):
                    run.game_over_text_renderer = TextRenderer(sdl_renderer, "assets/fonts/arial.ttf", size=72)
                run.game_over_text_renderer.renderer_text("GAME OVER", WINDOW_WIDTH//2, WINDOW_HEIGHT//3, color=(255, 255, 255), draw_bg=True, bg_color=(0, 0, 0, 200), radius=15)
            
            if victory_timer > 0:
                if not hasattr(run, 'victory_text_renderer'):
                    run.victory_text_renderer = TextRenderer(sdl_renderer, "assets/fonts/arial.ttf", size=72)
                run.victory_text_renderer.renderer_text("VICTORY", WINDOW_WIDTH//2, WINDOW_HEIGHT//3, color=(255, 255, 50), draw_bg=True, bg_color=(0, 0, 0, 200), radius=15)

        game_menu.render()
        
        # Render fade overlay
        if fade_active and fade_alpha > 0:
            fade_rect = sdl2.SDL_Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
            sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderDrawColor(sdl_renderer, 0, 0, 0, fade_alpha)
            sdl2.SDL_RenderFillRect(sdl_renderer, fade_rect)
            sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_NONE)
        
        renderer.present()
        sdl2.SDL_Delay(1000 // FPS)

    hud.cleanup()
    npc_manager.cleanup()
    projectile_manager.cleanup()
    sound_manager.cleanup()
    sdl2.ext.quit()
