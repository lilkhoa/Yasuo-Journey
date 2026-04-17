import sys
import os
import time
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

# --- IMPORTS ENTITIES (REFACTORED) ---
from entities.yasuo import Yasuo
from entities.leaf_ranger import LeafRanger
from entities.leaf_ranger_projectile import PoisonProjectile, PlantProjectile
from entities.npc import NPCManager
from entities.boss import BossManager
from entities.projectile import ProjectileManager
from core.event import handle_input
from ui.hud import SkillBarHUD
from ui.item_notification import ItemNotification, ItemNotificationSystem

# --- IMPORT ITEM & MENU ---
from ui.menu import GameMenu, MenuState

# Sound manager
from core.sound import get_sound_manager

# --- MULTIPLAYER NETWORKING ---
from network import packet as net_pkt
from network.server import GameServer
from network.client import GameClient
from network.remote_player import RemotePlayer

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

def run(net_mode: str = "solo", host_ip: str = "127.0.0.1", ext_seed: int = 0):
    """
    net_mode : 'solo'   – single-player (default)
               'host'   – start server + local client
               'client' – remote client only
    host_ip  : IP of the server (used in 'client' mode only)
    ext_seed : seed provided by server handshake (client only)
    """
    sdl2.ext.init()
    window = sdl2.ext.Window("Yasuo's Journey", size=(WINDOW_WIDTH, WINDOW_HEIGHT))
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

    # --- MULTIPLAYER: SERVER / CLIENT SETUP ---
    game_server:  GameServer | None  = None
    game_client:  GameClient | None  = None
    remote_player: RemotePlayer | None = None
    is_host   = False
    is_client = False
    is_multi  = False
    spawn_seed = 0

    # Tick counter for throttled world-state broadcasts
    _net_tick = 0
    _net_broadcast_every = max(1, FPS // NETWORK_TICK_RATE)

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
    last_checkpoint_data = None
    default_spawn_pos = (100, 350)
    last_checkpoint_pos = default_spawn_pos

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

    # --- INIT PLAYER (Mặc định Yasuo) ---
    player = Yasuo(world, software_factory, 100, 350, sound_manager, renderer_ptr=renderer.sdlrenderer)

    remote_player = None

    projectile_manager = ProjectileManager(renderer.sdlrenderer)
    npc_manager = NPCManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager)
    boss_manager = BossManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager, camera)
    
    icon_map = {}
    for key, val in common_drop_table.items():
        icon_map[key] = val[3]
    icon_map["COIN_ICON"] = coin_texture

    # Xác định loại nhân vật để nạp SkillBarHUD
    character_type = 'player1' if player.__class__.__name__ == 'Yasuo' else 'player2'
    hud = SkillBarHUD(renderer.sdlrenderer, player, character_type=character_type, icon_map=icon_map)
    
    def drop_coin_on_death(entity, num_coins=1):
        coin_name, coin_w, coin_h, coin_tex = common_drop_table[ItemType.COIN]
        ex, ey, ew, eh = entity.get_bounds()
        for i in range(num_coins):
            offset_x = (i - num_coins//2) * 20 if num_coins > 1 else 0
            coin_item = DroppedItem(
                ex + ew/2 + offset_x, ey + eh/2, coin_tex, coin_w, coin_h,
                text_renderer, ItemType.COIN, coin_name
            )
            if is_multi:
                coin_item.pickup_delay = 1.5 
            dropped_items.append(coin_item)
        sound_manager.play_sound("item_pop")
    
    def spawn_all_npcs_and_bosses():
        _next_net_id = 1
        for y, row in enumerate(NPC_MAP):
            for x, char in enumerate(row):
                if char == ' ': continue
                world_x, grid_y_pos = x * TILE_SIZE, y * TILE_SIZE
                if char == 'G':
                    npc = npc_manager.spawn_ghost(world_x, grid_y_pos)
                    npc.set_player(player); npc.on_death_callback = lambda n: drop_coin_on_death(n, 1)
                    npc.net_id = _next_net_id; _next_net_id += 1
                    make_npc_compatible(npc)
                elif char == 'S':
                    npc = npc_manager.spawn_shooter(world_x, grid_y_pos)
                    npc.set_player(player); npc.on_death_callback = lambda n: drop_coin_on_death(n, 1)
                    npc.net_id = _next_net_id; _next_net_id += 1
                    make_npc_compatible(npc)
                elif char == 'O':
                    npc = npc_manager.spawn_onre(world_x, grid_y_pos)
                    npc.set_player(player); npc.on_death_callback = lambda n: drop_coin_on_death(n, 1)
                    npc.net_id = _next_net_id; _next_net_id += 1
                    make_npc_compatible(npc)
                elif char == 'B':
                    boss = boss_manager.spawn_boss(world_x, grid_y_pos - 200)
                    boss.set_player(player); boss.minion_death_callback = lambda m: drop_coin_on_death(m, 1)
                    boss.net_id = _next_net_id; _next_net_id += 1
                    make_npc_compatible(boss)

    spawn_all_npcs_and_bosses()

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
    
    fade_active = False
    fade_alpha = 0
    fade_duration = 2.0
    fade_timer = 0.0

    game_menu = GameMenu(renderer.sdlrenderer, WINDOW_WIDTH, WINDOW_HEIGHT)

    # --- HELPER: Xoá chiêu thức an toàn ---
    def clear_active_skills(p):
        if hasattr(p, 'active_tornadoes'):
            for t in p.active_tornadoes: t.delete()
            p.active_tornadoes.clear()
        if hasattr(p, 'active_walls'):
            for w in p.active_walls: w.delete()
            p.active_walls.clear()
        if hasattr(p, 'active_lasers'):
            for l in p.active_lasers: l.delete()
            p.active_lasers.clear()
        if hasattr(p, 'e_aoe') and p.e_aoe:
            p.e_aoe = None

    running = True
    last_time = sdl2.SDL_GetTicks()
    
    while running:
        current_time = sdl2.SDL_GetTicks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time
        
        game_menu.update(dt)
        events = sdl2.ext.get_events()
        
        # 1. MENU INPUT
        menu_action = game_menu.handle_input(events)

        if game_menu.state == MenuState.HOST_LOBBY:
            if is_host and game_server:
                game_menu.lobby_client_ready = game_server.client_ready
                game_menu.lobby_host_ready = game_server.host_ready
                game_server.push_lobby_state()
            elif is_client and game_client:
                game_menu.lobby_client_ready = game_client.lobby_client_ready
                game_menu.lobby_host_ready = game_client.lobby_host_ready
                if game_client.lobby_game_starting:
                    game_menu.state = MenuState.CHARACTER_SELECT
                    game_menu.char_selection = 0

        if menu_action == "QUIT_GAME": running = False
        elif menu_action == "START_HOST":
            import socket
            is_host = True
            is_multi = True
            if game_server is None:
                game_server = GameServer(NETWORK_HOST, NETWORK_PORT)
                game_server.start()
            game_menu.host_ip = socket.gethostbyname(socket.gethostname())
            if remote_player is None:
                remote_player = RemotePlayer(world, software_factory, renderer_ptr=renderer.sdlrenderer)
            
        elif menu_action == "START_JOIN":
            is_client = True
            is_multi = True
            import network.packet
            conn_ip = network.packet.decode_ip(game_menu.join_ip.strip())
            if game_client is None:
                game_client = GameClient(conn_ip, NETWORK_PORT)
                connected = game_client.connect(timeout=5.0)
                if not connected:
                    game_menu.state = MenuState.JOIN_LOBBY
                    game_menu.join_ip = ""
                    game_menu.lobby_status_msg = "Connection Failed!"
                    is_client = False
                    is_multi = False
                else:
                    if remote_player is None:
                        remote_player = RemotePlayer(world, software_factory, renderer_ptr=renderer.sdlrenderer)
                    # Load host's character sprite for remote_player
                    host_char = game_client.get_remote_character_type()
                    if remote_player and host_char:
                        remote_player.set_character_type(host_char)

        elif menu_action == "LOBBY_ACTION":
            if is_host and game_server:
                if not game_server.host_ready:
                    game_server.host_ready = True
                elif game_server.client_ready:
                    game_server.game_starting = True
                    game_server.push_lobby_state()
                    # Go to character select first, then start game
                    game_menu.state = MenuState.CHARACTER_SELECT
                    game_menu.char_selection = 0
            elif is_client and game_client:
                game_client.send_lobby_ready(not game_menu.lobby_client_ready)
                game_menu.lobby_client_ready = not game_menu.lobby_client_ready

        elif menu_action == "CANCEL_LOBBY":
            if game_server:
                game_server.stop()
                game_server = None
            if game_client:
                game_client.stop()
                game_client = None
            is_host = False
            is_client = False
            is_multi = False

        elif menu_action == "START_GAME" or (isinstance(menu_action, tuple) and menu_action[0] == "START_GAME"):
            game_menu.state = MenuState.GAME_PLAYING
            
            char_id = "yasuo" 
            if isinstance(menu_action, tuple):
                char_id = menu_action[1]
            
            print(f"[DEBUG] Starting game with character: {char_id}")

            # Notify network about character selection
            if is_host and game_server:
                game_server.set_host_character_type(char_id)
                # Load remote player's character (client's choice)
                remote_char = game_server.get_remote_character_type()
                if remote_player and remote_char:
                    remote_player.set_character_type(remote_char)
            elif is_client and game_client:
                game_client.send_character_select(char_id)
                # Load host's character for remote display
                host_char = game_client.get_remote_character_type()
                if remote_player and host_char:
                    remote_player.set_character_type(host_char)
            
            if 'player' in locals() and player.entity:
                player.entity.delete()

            # KHỞI TẠO ĐÚNG CLASS NHÂN VẬT
            if char_id == "leaf_ranger":
                player = LeafRanger(world, software_factory, 100, 350, sound_manager, renderer_ptr=renderer.sdlrenderer)
                character_type = 'player2'
            else:
                player = Yasuo(world, software_factory, 100, 350, sound_manager, renderer_ptr=renderer.sdlrenderer)
                character_type = 'player1'
            
            hud = SkillBarHUD(renderer.sdlrenderer, player, character_type=character_type, icon_map=icon_map)

            player.hp = player.max_hp
            player.stamina = player.max_stamina
            player.state = 'idle'
            player.prev_state = 'idle'
            if player.entity.sprite:
                player.entity.sprite.position = (100, 350)
            player.is_blocking = False
            player.invincible = False
            player.exhausted = False
            player.frame_index = 0
            player.anim_timer = 0
            player.hurt_timer = 0
            player.hit_count = 0
            player.dead_animation_complete = False
            player.flash_timer = 0
            player.color_mod = (255, 255, 255)
            player.is_jumping = False
            player.jump_count = 0
            player.is_running = False
            player.vel_y = 0
            player.buffs = {}
            player.cooldowns.reset()
            player.walk_sound_channel = -1
            player.run_sound_channel = -1
            player.gold = 0
            player.consumables = []
            player.equipment = []
            player.skill_levels = {'q': 0, 'w': 0, 'e': 0, 'a': 0}
            player.attack_damage = player.base_attack_damage
            player.move_speed_bonus = 0
            player.lifesteal_ratio = player.base_lifesteal
            player.damage_reduction = 0.0
            player.armor = player.base_armor
            player.crit_chance = 0
            player.attack_range = 150
            player.attack_speed = 1.0
            player.hp_regen = PLAYER_HEALTH_REGEN
            
            npc_manager.cleanup()
            boss_manager.cleanup()
            projectile_manager.clear_all()
            
            dropped_items.clear()
            clear_active_skills(player)
            
            spawn_all_npcs_and_bosses()
            for box in boxes: box.reset()
            for barrel in barrels: barrel.reset()
            for chest in chests: chest.reset()
            
            kill_count = 0
            boss_encountered = False
            game_over = False
            game_over_sound_played = False
            victory = False
            victory_sound_played = False

        elif menu_action == "PAUSE_GAME":
            if is_host and game_server:
                game_server.push_game_event(net_pkt.make_game_pause())
            elif is_client and game_client:
                game_client.send_game_pause()

        elif menu_action == "RESUME_GAME":
            if is_host and game_server:
                game_server.push_game_event(net_pkt.make_game_resume())
            elif is_client and game_client:
                game_client.send_game_resume()
                
        elif menu_action == "UPDATE_VOLUME":
            music_volume = int((game_menu.get_volume()[0] / 100.0) * 128)
            sfx_volume = int((game_menu.get_volume()[1] / 100.0) * 128)
            sound_manager.set_music_volume(music_volume)
            sound_manager.set_master_volume(sfx_volume)
            
        elif menu_action == "BACK_TO_MAIN":
            sound_manager.stop_all_sounds()
            player.hp = player.max_hp
            player.stamina = player.max_stamina
            player.state = 'idle'
            player.prev_state = 'idle'
            if player.entity.sprite:
                player.entity.sprite.position = (100, 350)
            player.is_blocking = False
            player.invincible = False
            player.exhausted = False
            player.frame_index = 0
            player.anim_timer = 0
            player.hurt_timer = 0
            player.hit_count = 0
            player.dead_animation_complete = False
            player.flash_timer = 0
            player.color_mod = (255, 255, 255)
            player.is_jumping = False
            player.jump_count = 0
            player.is_running = False
            player.vel_y = 0
            player.buffs = {}
            player.cooldowns.reset()
            player.walk_sound_channel = -1
            player.run_sound_channel = -1
            player.gold = 0
            player.consumables = []
            player.equipment = []
            player.skill_levels = {'q': 0, 'w': 0, 'e': 0, 'a': 0}
            player.attack_damage = player.base_attack_damage
            player.move_speed_bonus = 0
            player.lifesteal_ratio = player.base_lifesteal
            player.damage_reduction = 0.0
            player.armor = player.base_armor
            player.crit_chance = 0
            player.attack_range = 150
            player.attack_speed = 1.0
            player.hp_regen = PLAYER_HEALTH_REGEN
            
            npc_manager.cleanup()
            boss_manager.cleanup()
            projectile_manager.clear_all()
            
            dropped_items.clear()
            clear_active_skills(player)
            
            for box in boxes: box.reset()
            for barrel in barrels: barrel.reset()
            for chest in chests: chest.reset()
            
            kill_count = 0
            boss_encountered = False
            game_over = False
            game_over_sound_played = False
            victory = False
            victory_sound_played = False
            
            spawn_all_npcs_and_bosses()
            sound_manager.switch_to_normal_music(fade_out_ms=500, fade_in_ms=1000)
            boss_music_playing = False


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
                        for item in dropped_items: 
                            if collect_timer <= 0:
                                if item.interact(notif_system, player, game_client):
                                    collect_timer = COLLECT_INTERVAL
                                    if sound_manager:
                                        sound_manager.play_sound("item_pickup")
                                    break

                        for chest in chests: 
                            if collect_timer <= 0: 
                                if chest.interact():
                                    collect_timer = COLLECT_INTERVAL
                                    break
                        
                        for statue in checkpoints:
                            if collect_timer <= 0:
                                saved_data = statue.interact(player)
                                if saved_data: 
                                    last_checkpoint_data = saved_data
                                    last_checkpoint_pos = (statue.x + statue.width//2 - 64, statue.y + statue.height - 128)
                                    collect_timer = COLLECT_INTERVAL
                                    break
                    
                    if key == sdl2.SDLK_6 and (mod & sdl2.KMOD_CTRL):
                        player.trigger_mastery()

                    elif key == sdl2.SDLK_1:
                        item_type = player.use_consumable(0)
                        if item_type: sound_manager.play_sound(item_type.name)
                    elif key == sdl2.SDLK_2:
                        item_type = player.use_consumable(1)
                        if item_type: sound_manager.play_sound(item_type.name)
                    elif key == sdl2.SDLK_3:
                        item_type = player.use_consumable(2)
                        if item_type: sound_manager.play_sound(item_type.name)

                if not handle_input(event, player, world, software_factory, renderer, npc_manager):
                    running = False
            
            collect_timer -= dt
        
        # 2.5. FADE UPDATE
        if fade_active:
            fade_timer += dt
            fade_alpha = int((fade_timer / fade_duration) * 255)
            if fade_alpha > 255: fade_alpha = 255
            
            if fade_timer >= fade_duration:
                fade_active = False
                fade_alpha = 0
                fade_timer = 0.0

                if victory:
                    game_menu.state = MenuState.MAIN_MENU
                    game_menu.selected_index = 0
                    sound_manager.stop_all_sounds()
                
                    player.hp = player.max_hp
                    player.stamina = player.max_stamina
                    player.state = 'idle'
                    player.prev_state = 'idle'
                    if player.entity.sprite:
                        player.entity.sprite.position = (100, 350)
                    player.is_blocking = False
                    player.invincible = False
                    player.exhausted = False
                    player.frame_index = 0
                    player.anim_timer = 0
                    player.hurt_timer = 0
                    player.hit_count = 0
                    player.dead_animation_complete = False
                    player.flash_timer = 0
                    player.color_mod = (255, 255, 255)
                    player.is_jumping = False
                    player.jump_count = 0
                    player.is_running = False
                    player.vel_y = 0
                    player.buffs = {}
                    player.cooldowns.reset()
                    player.walk_sound_channel = -1
                    player.run_sound_channel = -1
                    player.gold = 0
                    player.consumables = []
                    player.equipment = []
                    player.skill_levels = {'q': 0, 'w': 0, 'e': 0, 'a': 0}
                    player.attack_damage = player.base_attack_damage
                    player.move_speed_bonus = 0
                    player.lifesteal_ratio = player.base_lifesteal
                    player.damage_reduction = 0.0
                    player.armor = player.base_armor
                    player.crit_chance = 0
                    player.attack_range = 150
                    player.attack_speed = 1.0
                    player.hp_regen = PLAYER_HEALTH_REGEN
                    
                    game_over = False
                    game_over_sound_played = False
                    victory = False
                    victory_sound_played = False
                    victory_timer = 0
                    game_over_timer = 0
                    boss_encountered = False
                    kill_count = 0
                    
                    npc_manager.cleanup()
                    boss_manager.cleanup()
                    projectile_manager.clear_all()
                    
                    dropped_items.clear()
                    clear_active_skills(player)
                    
                    for box in boxes: box.reset()
                    for barrel in barrels: barrel.reset()
                    for chest in chests: chest.reset()
                    
                    spawn_all_npcs_and_bosses()
                    sound_manager.switch_to_normal_music(fade_out_ms=500, fade_in_ms=1000)
                    boss_music_playing = False

                else:
                    sound_manager.set_music_volume(128)
                    if last_checkpoint_data:
                        player.respawn_penalty(last_checkpoint_pos[0], last_checkpoint_pos[1])
                        
                        game_over = False
                        game_over_sound_played = False
                        victory = False
                        victory_sound_played = False
                        victory_timer = 0
                        game_over_timer = 0
                        
                        if boss_music_playing:
                            sound_manager.switch_to_normal_music(fade_out_ms=500, fade_in_ms=1000)
                            boss_music_playing = False
                    else:
                        game_menu.state = MenuState.MAIN_MENU
                        game_menu.selected_index = 0
                        sound_manager.stop_all_sounds()
                        
                        player.hp = player.max_hp
                        player.stamina = player.max_stamina
                        player.state = 'idle'
                        player.prev_state = 'idle'
                        if player.entity.sprite:
                            player.entity.sprite.position = (100, 350)
                        player.is_blocking = False
                        player.invincible = False
                        player.exhausted = False
                        player.frame_index = 0
                        player.anim_timer = 0
                        player.hurt_timer = 0
                        player.hit_count = 0
                        player.dead_animation_complete = False
                        player.flash_timer = 0
                        player.color_mod = (255, 255, 255)
                        player.is_jumping = False
                        player.jump_count = 0
                        player.is_running = False
                        player.vel_y = 0
                        player.buffs = {}
                        player.cooldowns.reset()
                        player.walk_sound_channel = -1
                        player.run_sound_channel = -1
                        
                        player.gold = 0
                        player.consumables = []
                        player.equipment = []
                        player.skill_levels = {'q': 0, 'w': 0, 'e': 0, 'a': 0}
                        player.attack_damage = player.base_attack_damage
                        player.move_speed_bonus = 0
                        player.lifesteal_ratio = player.base_lifesteal
                        player.damage_reduction = 0.0
                        player.armor = player.base_armor
                        player.crit_chance = 0
                        player.attack_range = 150
                        player.attack_speed = 1.0
                        player.hp_regen = PLAYER_HEALTH_REGEN
                        
                        game_over = False
                        game_over_sound_played = False
                        victory = False
                        victory_sound_played = False
                        victory_timer = 0
                        game_over_timer = 0
                        boss_encountered = False
                        kill_count = 0
                        
                        npc_manager.cleanup()
                        boss_manager.cleanup()
                        projectile_manager.clear_all()
                        
                        dropped_items.clear()
                        clear_active_skills(player)
                        
                        for box in boxes: box.reset()
                        for barrel in barrels: barrel.reset()
                        for chest in chests: chest.reset()
                        
                        spawn_all_npcs_and_bosses()
                        sound_manager.switch_to_normal_music(fade_out_ms=500, fade_in_ms=1000)
                        boss_music_playing = False
                        
        # 3. UPDATE
        if game_menu.state == MenuState.GAME_PLAYING:
            keys = sdl2.SDL_GetKeyboardState(None)
            all_obstacles = boxes + [b for b in barrels if not b.is_broken]

            player.set_blocking(keys[sdl2.SDLK_s])
            player.handle_movement(keys)
            
            player.update(dt, world, software_factory, renderer.sdlrenderer, game_map=my_map, boxes=all_obstacles)

            if player.entity.sprite:
                if player.entity.sprite.x < 0: player.entity.sprite.x = 0
                if player.entity.sprite.x > my_map.width_pixel - 128: player.entity.sprite.x = my_map.width_pixel - 128

            _net_tick += 1

            def _safe_str(v): return v.name if hasattr(v, 'name') and hasattr(v, 'value') else str(v)
            def _safe_dir(v): return v.value if hasattr(v, 'value') else int(v)

            if is_host and game_server and game_server.is_connected():
                local_state = player.get_network_state()
                state_pkt = net_pkt.make_player_state(
                    player_id=0,
                    x=local_state['x'], y=local_state['y'],
                    vel_y=local_state['vel_y'],
                    facing_right=local_state['facing_right'],
                    state=local_state['state'],
                    hp=local_state['hp'],
                    stamina=local_state['stamina'],
                    frame_index=local_state['frame_index'],
                    timestamp=local_state['ts'],
                )
                game_server.push_local_player_state(state_pkt)

                if _net_tick % _net_broadcast_every == 0:
                    entity_list = []
                    for n in npc_manager.npcs:
                        entity_list.append({
                            'etype': 'npc', 'eid': getattr(n, 'net_id', id(n)),
                            'x': float(n.x), 'y': float(n.y),
                            'hp': float(getattr(n, 'health', 0)),
                            'state': _safe_str(getattr(n, 'state', 'IDLE')),
                            'direction': _safe_dir(getattr(n, 'direction', 1)),
                            'is_attacking': bool(getattr(n, 'is_attacking', False)),
                        })
                    for b in boss_manager.bosses:
                        entity_list.append({
                            'etype': 'boss', 'eid': getattr(b, 'net_id', id(b)),
                            'x': float(b.x), 'y': float(b.y),
                            'hp': float(getattr(b, 'health', 0)),
                            'state': _safe_str(getattr(b, 'state', 'idle')),
                            'direction': _safe_dir(b.direction),
                            'is_attacking': bool(getattr(b, 'is_attacking', False)),
                            'attack_type': str(getattr(b, 'attack_type', 'melee')),
                        })
                    game_server.push_world_state(
                        net_pkt.make_entity_state(entity_list),
                        net_pkt.make_projectile_state([
                            {'pid': id(proj), 'x': float(proj.x), 'y': float(proj.y),
                             'vx': float(getattr(proj, 'vx', 0)),
                             'vy': float(getattr(proj, 'vy', 0)),
                             'active': bool(proj.active)}
                            for proj in projectile_manager.projectiles
                        ])
                    )

                remote_raw = game_server.get_remote_state()
                if remote_player:
                    remote_char = game_server.get_remote_character_type()
                    if getattr(remote_player, '_character_type', '') != remote_char:
                        remote_player.set_character_type(remote_char)
                    if remote_raw:
                        remote_player.apply_network_state(remote_raw)
                    remote_player.update(dt)

                # Sync dropped items from host to client
                for item in dropped_items:
                    if not getattr(item, 'broadcasted', False):
                        drop_pkt = {
                            "type": net_pkt.ITEM_DROPPED,
                            "item_type": item.item_type.value,
                            "x": item.x,
                            "y": item.y,
                            "item_net_id": item.net_id
                        }
                        game_server.push_game_event(drop_pkt)
                        item.broadcasted = True
                    elif item.is_collected and not getattr(item, 'pickup_broadcasted', False):
                        approved_ev = net_pkt.make_pickup_request(0, item.net_id, 0)
                        approved_ev['approved'] = True
                        game_server.push_game_event(approved_ev)
                        item.pickup_broadcasted = True

                for ev in game_server.pop_events():
                    t = ev.get('type')
                    if t == net_pkt.HIT_EVENT:
                        target_id = ev.get('target_id')
                        damage    = ev.get('damage', 0)
                        for n in npc_manager.npcs:
                            if getattr(n, 'net_id', id(n)) == target_id and n.is_alive():
                                n.take_damage(damage)
                                break
                        for b in boss_manager.bosses:
                            if getattr(b, 'net_id', id(b)) == target_id:
                                b.take_damage(damage)
                                break
                    elif t == net_pkt.PICKUP_REQUEST:
                        item_net_id = ev.get('item_net_id')
                        player_id = ev.get('player_id')
                        for item in dropped_items:
                            if item.net_id == item_net_id and not item.is_collected:
                                item.is_collected = True
                                approved_ev = net_pkt.make_pickup_request(player_id, item_net_id, player_id)
                                approved_ev['approved'] = True
                                game_server.push_game_event(approved_ev)
                                break
                    elif t == net_pkt.GAME_PAUSE:
                        if game_menu.state == MenuState.GAME_PLAYING:
                            game_menu.state = MenuState.PAUSE
                    elif t == net_pkt.GAME_RESUME:
                        if game_menu.state == MenuState.PAUSE:
                            game_menu.state = MenuState.GAME_PLAYING

            elif is_host and game_server and not game_server.is_connected() and game_menu.state == MenuState.GAME_PLAYING:
                print("[Server] Client disconnected! Returning to menu.")
                game_server.stop()
                game_server = None
                is_host = False
                is_multi = False
                game_menu.state = MenuState.MAIN_MENU
                game_menu.selected_index = 0
                menu_action = "BACK_TO_MAIN"

            elif is_client and game_client and game_client.is_connected():
                local_state = player.get_network_state()
                state_pkt = net_pkt.make_player_state(
                    player_id=game_client.player_id,
                    x=local_state['x'], y=local_state['y'],
                    vel_y=local_state['vel_y'],
                    facing_right=local_state['facing_right'],
                    state=local_state['state'],
                    hp=local_state['hp'],
                    stamina=local_state['stamina'],
                    frame_index=local_state['frame_index'],
                    timestamp=local_state['ts'],
                )
                game_client.send_player_state(state_pkt)

                remote_raw = game_client.get_remote_player_state()
                if remote_player and remote_raw:
                    remote_player.apply_network_state(remote_raw)
                    remote_player.update(dt)

                for e_state in game_client.get_entity_state():
                    target_id = e_state.get('eid')
                    hp = e_state.get('hp', 0)
                    for n in npc_manager.npcs:
                        if getattr(n, 'net_id', id(n)) == target_id:
                            if n.health > 0 and hp <= 0:
                                n.take_damage(n.health)
                            else:
                                n.health = hp
                            n.x = e_state.get('x', n.x)
                            n.y = e_state.get('y', n.y)
                            n.direction = 1 if e_state.get('direction', 1) > 0 else -1
                            n.is_attacking = e_state.get('is_attacking', False)
                            break
                    for b in boss_manager.bosses:
                        if getattr(b, 'net_id', id(b)) == target_id:
                            if getattr(b, 'health', 0) > 0 and hp <= 0:
                                b.take_damage(getattr(b, 'health', 0))
                            elif hasattr(b, 'health'):
                                b.health = hp
                            b.x = e_state.get('x', b.x)
                            b.y = e_state.get('y', b.y)
                            b.direction = 1 if e_state.get('direction', 1) > 0 else -1
                            b.is_attacking = e_state.get('is_attacking', False)
                            b.attack_type = e_state.get('attack_type', 'melee')
                            break

                for gev in game_client.pop_game_events():
                    t = gev.get('type')
                    if t == net_pkt.GAME_EVENT:
                        ev_name = gev.get('event')
                        if ev_name == 'game_over':
                            game_over = True
                            game_over_timer = 3.0
                        elif ev_name == 'victory':
                            victory = True
                            victory_timer = victory_text_duration
                    elif t == net_pkt.GAME_PAUSE:
                        if game_menu.state == MenuState.GAME_PLAYING:
                            game_menu.state = MenuState.PAUSE
                    elif t == net_pkt.GAME_RESUME:
                        if game_menu.state == MenuState.PAUSE:
                            game_menu.state = MenuState.GAME_PLAYING
                    elif t == net_pkt.ITEM_DROPPED:
                        item_type_val = gev.get('item_type')
                        ix = gev.get('x', 0)
                        iy = gev.get('y', 0)
                        item_net_id = gev.get('item_net_id')
                        try:
                            item_type = ItemType(item_type_val)
                            item_info = common_drop_table.get(item_type)
                            if item_info:
                                item_name, item_w, item_h, item_tex = item_info
                                new_item = DroppedItem(ix, iy, item_tex, item_w, item_h,
                                                      text_renderer, item_type, item_name)
                                new_item.net_id = item_net_id
                                new_item.pickup_delay = 1.5
                                dropped_items.append(new_item)
                        except ValueError:
                            pass
                    elif t == net_pkt.PICKUP_REQUEST:
                        item_net_id = gev.get('item_net_id')
                        approved = gev.get('approved', False)
                        if approved:
                            for i, item in enumerate(dropped_items):
                                if item.net_id == item_net_id:
                                    item.is_collected = True
                                    break
                    elif t == net_pkt.CHARACTER_SELECT:
                        remote_char = gev.get('character_type', 'yasuo')
                        if remote_player:
                            remote_player.set_character_type(remote_char)

            elif is_client and game_client and not game_client.is_connected() and game_menu.state == MenuState.GAME_PLAYING:
                print("[Client] Disconnected from server! Returning to menu.")
                game_client.stop()
                game_client = None
                is_client = False
                is_multi = False
                game_menu.state = MenuState.MAIN_MENU
                game_menu.selected_index = 0
                menu_action = "BACK_TO_MAIN"

            elif is_multi and remote_player:
                remote_player.update(dt)

            for box in boxes: box.update(dt, my_map)
            for barrel in barrels: barrel.update(dt, my_map)
            for chest in chests: chest.update(dt, player, dropped_items, renderer.sdlrenderer)
            for item in dropped_items: item.update(dt, my_map, player)
            for statue in checkpoints: statue.update(dt, player)
            dropped_items = [item for item in dropped_items if not item.is_collected]

            notif_system.update()

            # hard code for yasuo
            # if player.entity.sprite:
            #     player_rect = SDL_Rect(int(player.entity.sprite.x), int(player.entity.sprite.y), 128, 128)
            #     camera.update(player_rect, my_map.width_pixel)
            if player.entity.sprite:
                hitbox = player.get_hitbox()
                offset_x = hitbox.x - player.x
                
                # Giới hạn map dựa trên hitbox
                if hitbox.x < 0: 
                    player.entity.sprite.x = -offset_x
                if hitbox.x + hitbox.w > my_map.width_pixel: 
                    player.entity.sprite.x = my_map.width_pixel - hitbox.w - offset_x
                
                # Camera theo dõi vị trí của hitbox thay vì toàn bộ ảnh (để đỡ bị lệch tâm)
                camera.update(player.get_hitbox(), my_map.width_pixel)

            alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
            alive_bosses = boss_manager.get_alive_bosses()
            all_minions = []
            for boss in alive_bosses: all_minions.extend([m for m in boss.minions if m.health > 0])
            
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
            
            if boss_encountered and not victory and len(alive_bosses) == 0:
                victory = True
                victory_timer = victory_text_duration
                if not victory_sound_played:
                    sound_manager.stop_music(fade_out_ms=500)
                    sound_manager.play_sound("victory")
                    victory_sound_played = True
            if victory_timer > 0:
                victory_timer -= dt
                if victory_timer <= 0 and not fade_active:
                    fade_active = True
                    fade_timer = 0.0
                    fade_alpha = 0
            
            all_combat_targets = alive_npcs + alive_bosses + all_minions
            
            network_ctx = (is_multi, is_host, game_client)

            # [SỬA LỖI Ở ĐÂY] Lấy danh sách đạn đang bay và truyền vào cho nhân vật
            active_projectiles = getattr(projectile_manager, 'projectiles', [])
            player.update_skills(dt, all_combat_targets, projectiles=active_projectiles, 
                               network_ctx=network_ctx, camera=camera, game_map=my_map, 
                               renderer=renderer.sdlrenderer)
            
            if hasattr(player, 'skill_e') and hasattr(player.skill_e, 'update_dash'):
                player.skill_e.update_dash(dt, all_combat_targets, all_obstacles, my_map, network_ctx)
                if getattr(player.skill_e, 'is_dashing', False): 
                    player.state = 'dashing_e'
                elif player.state == 'dashing_e' and not getattr(player.skill_e, 'is_dashing', False): 
                    player.state = 'idle'

            npc_manager.update_all(dt, my_map)
            boss_manager.update_all(dt, my_map)
            obstacles = all_obstacles + chests
            projectile_manager.update_all(dt, world, my_map, obstacles)
            
            if not game_over:
                for projectile in projectile_manager.projectiles[:]:
                    # 1. Đạn của NPC/Boss trúng Player
                    if projectile.check_collision(player):
                        player.take_damage(projectile.damage)
                        projectile.on_hit()
                    
                    # 2. Đạn của Player (Mũi tên) trúng NPC/Boss
                    owner_class = getattr(getattr(projectile, 'owner', None), '__class__', None)
                    if owner_class and owner_class.__name__ in ['Yasuo', 'LeafRanger']:
                        # ================= THÊM MỚI: BẮN BỂ THÙNG GỖ =================
                        hit_barrel = False
                        for barrel in barrels:
                            if not barrel.is_broken:
                                bx, by, bw, bh = barrel.get_bounds()
                                barrel_rect = sdl2.SDL_Rect(int(bx), int(by), int(bw), int(bh))
                                
                                px = getattr(projectile, 'x', 0)
                                py = getattr(projectile, 'y', 0)
                                pw = getattr(projectile, 'width', 20)
                                ph = getattr(projectile, 'height', 20)
                                p_rect = sdl2.SDL_Rect(int(px), int(py), int(pw), int(ph))
                                
                                if sdl2.SDL_HasIntersection(p_rect, barrel_rect):
                                    barrel.take_damage(1, dropped_items, sdl_renderer)
                                    
                                    # Kích hoạt âm thanh vỡ thùng
                                    if sound_manager:
                                        if owner_class and owner_class.__name__ == 'LeafRanger':
                                            sound_manager.play_sound("lr_on_hit")
                                        else:
                                            sound_manager.play_sound("player_auto_barrel")
                                    
                                    # Hủy mũi tên
                                    if hasattr(projectile, 'on_hit'): projectile.on_hit()
                                    else: projectile.active = False
                                    
                                    hit_barrel = True
                                    break # Trúng 1 thùng là đủ, thoát vòng lặp thùng
                                    
                        if hit_barrel:
                            continue # Mũi tên đã bốc hơi, bỏ qua việc xét va chạm với quái
                        # =============================================================

                        for enemy in all_combat_targets:
                            # Bỏ qua quái đã chết
                            if hasattr(enemy, 'is_alive') and not enemy.is_alive(): continue
                            if hasattr(enemy, 'health') and enemy.health <= 0: continue
                            
                            # Nếu mũi tên chạm quái
                            if projectile.check_collision(enemy):
                                target_net_id = getattr(enemy, 'net_id', id(enemy))
                                
                                # Gây sát thương (hỗ trợ cả chơi mạng)
                                if is_multi and game_client and game_client.is_connected():
                                    etype = 'boss' if enemy.__class__.__name__ == 'Boss' else 'npc'
                                    game_client.send_hit_event(etype, target_net_id, projectile.damage)
                                else:
                                    if hasattr(enemy, 'take_damage'): enemy.take_damage(projectile.damage)
                                
                                # Kích hoạt hồi máu / thể lực lifesteal cho Leaf Ranger
                                if hasattr(player, 'on_hit_enemy'):
                                    player.on_hit_enemy(projectile.damage)
                                    if isinstance(projectile, (PoisonProjectile, PlantProjectile)):
                                        sound_manager.play_sound("lr_w2")
                                    else:
                                        sound_manager.play_sound("lr_on_hit")
                                
                                # Cộng điểm hạ gục nếu quái chết
                                if (hasattr(enemy, 'is_alive') and not enemy.is_alive()) or (hasattr(enemy, 'health') and enemy.health <= 0):
                                    kill_count += 1
                                    if hasattr(player, 'on_kill_enemy'): player.on_kill_enemy()
                                
                                # Áp dụng hiệu ứng đặc biệt (độc, chặn, ...) nếu đạn hỗ trợ
                                if hasattr(projectile, 'apply_effect'):
                                    projectile.apply_effect(enemy)
                                
                                # Gọi hàm on_hit() để mũi tên biến mất ngay lập tức
                                projectile.on_hit()
                                break # Trúng 1 quái là kết thúc viên đạn
                
                for npc in alive_npcs:
                    if hasattr(npc, 'projectile_manager') and npc.projectile_manager is not None:
                        continue
                    
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
                
                if player.state == 'attacking':
                    # [PHÂN LUỒNG ĐA HÌNH] Leaf Ranger bắn cung, Yasuo chém kiếm
                    if player.__class__.__name__ == 'LeafRanger':
                        # Leaf Ranger bắn cung ở Frame thứ 8
                        if player.frame_index == 8 and not getattr(player, '_arrow_spawned', False):
                            player.spawn_attack_projectile(sdl_renderer, projectile_manager, network_ctx)
                            player._arrow_spawned = True
                            sound_manager.play_sound("arrow_shoot")
                    else:
                        # Logic chém cận chiến của Yasuo
                        if not hasattr(player, '_attack_hit_anything'): player._attack_hit_anything = False
                        bx, by, bw, bh = player.get_hitbox().x, player.get_hitbox().y, player.get_hitbox().w, player.get_hitbox().h
                        ar = 50
                        atk_x = int(bx + bw if player.facing_right else bx - ar)
                        atk_rect = sdl2.SDL_Rect(atk_x, int(by), ar, bh)
                        
                        for barrel in barrels:
                            if not barrel.is_broken and sdl2.SDL_HasIntersection(atk_rect, barrel.get_bounds()):
                                barrel.take_damage(1, dropped_items, sdl_renderer)
                                if not player._attack_hit_anything:
                                    sound_manager.play_sound("player_auto_barrel"); player._attack_hit_anything = True
                        
                        for enemy in all_combat_targets:
                            ex, ey, ew, eh = enemy.get_bounds()
                            enemy_rect = sdl2.SDL_Rect(int(ex), int(ey), int(ew), int(eh))
                            if sdl2.SDL_HasIntersection(atk_rect, enemy_rect):
                                target_net_id = getattr(enemy, 'net_id', id(enemy))
                                attr_name = f'_attack_hit_{target_net_id}'
                                if not getattr(player, attr_name, False):
                                    setattr(player, attr_name, True)
                                    
                                    if is_multi and game_client and game_client.is_connected():
                                        etype = 'boss' if enemy in alive_bosses else 'npc'
                                        game_client.send_hit_event(etype, target_net_id, player.attack_damage)
                                        sound_manager.play_sound("player_auto_npc"); player._attack_hit_anything = True
                                    else:
                                        enemy.take_damage(player.attack_damage)
                                        if not player._attack_hit_anything:
                                            sound_manager.play_sound("player_auto_npc"); player._attack_hit_anything = True
                                            
                                    player.on_hit_enemy(player.attack_damage)
                                    
                                    if (hasattr(enemy, 'is_alive') and not enemy.is_alive()) or (hasattr(enemy, 'health') and enemy.health <= 0):
                                        kill_count += 1; player.on_kill_enemy()
                else:
                    # Reset các cờ (flags) khi kết thúc hoạt ảnh đánh
                    if hasattr(player, '_arrow_spawned'): 
                        player._arrow_spawned = False
                        
                    if hasattr(player, '_attack_hit_anything'):
                        if not player._attack_hit_anything: sound_manager.play_sound("player_auto_miss")
                        delattr(player, '_attack_hit_anything')
                        
                    for enemy in all_combat_targets:
                        target_net_id = getattr(enemy, 'net_id', id(enemy))
                        attr_name = f'_attack_hit_{target_net_id}'
                        if hasattr(player, attr_name): delattr(player, attr_name)

                if player.state == 'dead' and player.dead_animation_complete:
                    game_over = True
                    game_over_timer = 3.0
                    if not game_over_sound_played:
                        sound_manager.set_music_volume(int(0.3 * 128))
                        sound_manager.play_sound("game_over")
                        game_over_sound_played = True

            else:
                game_over_timer -= dt
                if game_over_timer <= 0 and not fade_active:
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
            
            player.render_skills(sdl_renderer, camera)
            
            for box in boxes: box.render(sdl_renderer, camera)
            for barrel in barrels: barrel.render(sdl_renderer, camera)
            for chest in chests: chest.render(sdl_renderer, camera, player)
            for item in dropped_items: item.render(sdl_renderer, camera, player)
            for statue in checkpoints: statue.render(sdl_renderer, camera)

            notif_system.render(sdl_renderer)

            npc_manager.render_all(camera.camera.x, camera.camera.y)
            boss_manager.render_all(camera.camera.x, camera.camera.y)
            projectile_manager.render_all(camera.camera.x, camera.camera.y)
            
            if DEBUG_COLLISION_BOXES:
                sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_BLEND)
                
                for npc in npc_manager.npcs:
                    nx, ny, nw, nh = npc.get_bounds()
                    npc_rect = sdl2.SDL_Rect(int(nx - camera.camera.x), int(ny - camera.camera.y), int(nw), int(nh))
                    sdl2.SDL_SetRenderDrawColor(sdl_renderer, 0, 255, 0, 100)
                    sdl2.SDL_RenderFillRect(sdl_renderer, npc_rect)
                    sdl2.SDL_SetRenderDrawColor(sdl_renderer, 0, 255, 0, 255)
                    sdl2.SDL_RenderDrawRect(sdl_renderer, npc_rect)
                
                for boss in boss_manager.bosses:
                    bx, by, bw, bh = boss.get_bounds()
                    boss_rect = sdl2.SDL_Rect(int(bx - camera.camera.x), int(by - camera.camera.y), int(bw), int(bh))
                    sdl2.SDL_SetRenderDrawColor(sdl_renderer, 255, 0, 0, 100)
                    sdl2.SDL_RenderFillRect(sdl_renderer, boss_rect)
                    sdl2.SDL_SetRenderDrawColor(sdl_renderer, 255, 0, 0, 255)
                    sdl2.SDL_RenderDrawRect(sdl_renderer, boss_rect)
                    
                    for minion in boss.minions:
                        mx, my, mw, mh = minion.get_bounds()
                        minion_rect = sdl2.SDL_Rect(int(mx - camera.camera.x), int(my - camera.camera.y), int(mw), int(mh))
                        sdl2.SDL_SetRenderDrawColor(sdl_renderer, 255, 165, 0, 100)
                        sdl2.SDL_RenderFillRect(sdl_renderer, minion_rect)
                        sdl2.SDL_SetRenderDrawColor(sdl_renderer, 255, 165, 0, 255)
                        sdl2.SDL_RenderDrawRect(sdl_renderer, minion_rect)
                
                sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_NONE)
            
            if remote_player:
                remote_player.render(sdl_renderer, camera.camera.x, camera.camera.y)

            if player.entity.sprite:
                # Hard code for yasuo
                # p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), int(player.entity.sprite.y - camera.camera.y), 128, 128)
                # p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, player.entity.sprite.surface)
                
                # Lấy kích thước thật thay vì ép về 128x128
                w, h = player.entity.sprite.size
                p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), int(player.entity.sprite.y - camera.camera.y), w, h)
                p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, player.entity.sprite.surface)
                r, g, b = player.color_mod
                if player.flash_timer > 0: r, g, b = (255, 100, 100)
                sdl2.SDL_SetTextureColorMod(p_tex, int(r), int(g), int(b))
                sdl2.SDL_RenderCopy(sdl_renderer, p_tex, None, p_dst)
                sdl2.SDL_DestroyTexture(p_tex)

            player.render(sdl_renderer, camera.camera.x, camera.camera.y)
            
            if DEBUG_COLLISION_BOXES and player.state == 'attacking':
                bx, by, bw, bh = player.get_hitbox().x, player.get_hitbox().y, player.get_hitbox().w, player.get_hitbox().h
                ar = 50
                atk_x = int(bx + bw if player.facing_right else bx - ar)
                atk_rect = sdl2.SDL_Rect(int(atk_x - camera.camera.x), int(by - camera.camera.y), ar, bh)
                sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_BLEND)
                sdl2.SDL_SetRenderDrawColor(sdl_renderer, 0, 100, 255, 128)
                sdl2.SDL_RenderFillRect(sdl_renderer, atk_rect)
                sdl2.SDL_SetRenderDrawColor(sdl_renderer, 0, 150, 255, 255)
                sdl2.SDL_RenderDrawRect(sdl_renderer, atk_rect)
                sdl2.SDL_SetRenderDrawBlendMode(sdl_renderer, sdl2.SDL_BLENDMODE_NONE)
            
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
    if game_client: game_client.stop()
    if game_server: game_server.stop()
    sdl2.ext.quit()