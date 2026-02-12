import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sdl2
import sdl2.ext
from settings import *
from world.map import GameMap
from world.interactable import Box
from world.decoration import Decoration
from sdl2 import SDL_Rect, SDL_RenderCopy
from core.camera import Camera

# --- THÊM IMPORTS CHO PLAYER VÀ NPC ---
from entities.player import Player
from entities.npc import NPCManager
from entities.boss import BossManager
from entities.projectile import ProjectileManager
from core.event import handle_input
from combat.skill_q import update_q_logic
from combat.skill_w import update_w_logic
from ui.hud import SkillBarHUD

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

# BOX MAP (Mask Map cho vật thể tương tác)
# 'B' đại diện cho Box
BOX_MAP = [
    "                                                  ", 
    "                                                  ", 
    "                                                  ", 
    "                                                  ", 
    "                                                  ", # Đặt thử 1 cái thùng
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
    sound_manager = get_sound_manager()
    sound_manager.initialize()
    sound_manager.load_npc_sounds()
    sound_manager.load_boss_sounds()
    
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

        box_tileset_sprite = factory.from_image("assets/Map/interactable_objects/TX Village Props.png")
        box_tileset_texture = box_tileset_sprite.texture

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
    
    # 4. Boxes initialization
    boxes = []
    for y, row in enumerate(BOX_MAP):
        for x, char in enumerate(row):
            if char == "B":
                # calculate the real position
                real_x = x * TILE_SIZE
                # align Y for box to lie on the top of the ground of this row
                # because height is (44 -> 24) * SCALE FACTOR
                real_y = (y * TILE_SIZE) # because we scale the block has the same size to the ground block

                new_box = Box(real_x, real_y, box_tileset_texture)
                boxes.append(new_box)
            

    player = Player(world, software_factory, 100, 350) # Spawn gần mặt đất
    
    # Initialize ProjectileManager for NPC projectiles
    projectile_manager = ProjectileManager(renderer.sdlrenderer)
    npc_manager = NPCManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager)
    boss_manager = BossManager(software_factory, None, renderer.sdlrenderer, projectile_manager, sound_manager, camera)
    
    # Initialize HUD
    hud = SkillBarHUD(renderer.sdlrenderer, player)
    
    # Spawn NPC closer to player for testing (within detection range)
    # GROUND_Y = 480, player sprite 128px, NPC sprite ~72-96px
    # Player spawn ở y=350 (vì sprite 128px sẽ chạm đất ở 350+128=478)
    # NPC spawn thấp hơn để chạm đất cùng level
    npc_ground_y = 500  # Điều chỉnh để NPC đứng cùng mặt đất với player
    
    g1 = npc_manager.spawn_ghost(350, npc_ground_y)  # 250 pixels from player
    g1.set_player(player)
    make_npc_compatible(g1)
    s1 = npc_manager.spawn_shooter(550, npc_ground_y)  # Gần hơn để test
    s1.set_player(player)
    make_npc_compatible(s1)
    o1 = npc_manager.spawn_onre(750, npc_ground_y)  # Gần hơn để test melee
    o1.set_player(player)
    make_npc_compatible(o1)

    # Boss spawn
    boss = boss_manager.spawn_boss(4500, npc_ground_y - 400)
    boss.set_player(player)
    make_npc_compatible(boss)
    
    active_tornadoes = []
    active_walls = []

    # --- GAME STATS ---
    kill_count = 0
    game_over = False
    game_over_timer = 0  # Đếm thời gian trước khi respawn

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
        player.update(dt, world, software_factory, None, active_tornadoes, active_walls, game_map=my_map, boxes=boxes)
        
        # Giới hạn Player trong Map
        if player.entity.sprite.x < 0:
            player.entity.sprite.x = 0
        if player.entity.sprite.x > my_map.width_pixel - 128:
            player.entity.sprite.x = my_map.width_pixel - 128

        # Box updating
        for box in boxes:
            box.update(dt, my_map)
        
        # update Camera theo Player (dùng SDL_Rect để tương thích)
        player_rect = SDL_Rect(int(player.entity.sprite.x), int(player.entity.sprite.y), 128, 128)
        camera.update(player_rect, my_map.width_pixel)
        
        # Skill Updates
        alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
        alive_bosses = boss_manager.get_alive_bosses()
        # Gather all minions from all bosses
        all_minions = []
        for boss in alive_bosses:
            all_minions.extend([m for m in boss.minions if m.health > 0])
        
        # Combine all combat targets for skills
        all_combat_targets = alive_npcs + alive_bosses + all_minions
        
        for t in active_tornadoes[:]:
            update_q_logic(t, all_combat_targets, dt)
            if not t.active: 
                t.delete()
                active_tornadoes.remove(t)
        
        for w in active_walls[:]:
            update_w_logic(w)
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
        # Chỉ xử lý khi chưa game over
        if not game_over:
            # --- 0. PROJECTILE -> BOX (destroy on hit) ---
            for projectile in projectile_manager.projectiles[:]:
                proj_rect = sdl2.SDL_Rect(int(projectile.x), int(projectile.y), projectile.width, projectile.height)
                for box in boxes:
                    if sdl2.SDL_HasIntersection(proj_rect, box.rect):
                        projectile.on_hit()
                        break

            # --- 1. NPC PROJECTILE -> PLAYER ---
            for projectile in projectile_manager.projectiles[:]:
                if projectile.check_collision(player):
                    player.take_damage(projectile.damage)
                    projectile.on_hit()
                    print(f"[COMBAT] Player hit by projectile! HP: {int(player.hp)}/{player.max_hp}")
            
            # --- 2. NPC/BOSS/MINION MELEE ATTACK -> PLAYER ---
            # Check NPCs
            for npc in alive_npcs:
                # Check if NPC is in attacking state and can hit player
                if hasattr(npc, 'is_attacking') and npc.is_attacking:
                    # Get NPC attack hitbox (offset based on direction)
                    npc_x, npc_y, npc_w, npc_h = npc.get_bounds()
                    attack_range = getattr(npc, 'attack_range', 50)
                    
                    # Attack hitbox phía trước NPC
                    if npc.direction == 1:  # Facing right
                        attack_hitbox = (npc_x + npc_w, npc_y, attack_range, npc_h)
                    else:  # Facing left (-1)
                        attack_hitbox = (npc_x - attack_range, npc_y, attack_range, npc_h)
                    
                    # Player bounds
                    px, py, pw, ph = player.x, player.y, player.width, player.height
                    
                    # AABB collision với attack hitbox
                    ax, ay, aw, ah = attack_hitbox
                    if (ax < px + pw and ax + aw > px and ay < py + ph and ay + ah > py):
                        # Check if this attack hasn't hit player yet (prevent multi-hit)
                        if not getattr(npc, '_attack_hit_player', False):
                            npc._attack_hit_player = True
                            player.take_damage(npc.damage)
                            print(f"[COMBAT] Player melee'd by NPC! HP: {int(player.hp)}/{player.max_hp}")
                else:
                    # Reset hit flag when not attacking
                    npc._attack_hit_player = False
            
            # Check Boss attacks (using melee_range from boss)
            for boss in alive_bosses:
                if boss.is_attacking and boss.attack_type == 'melee':
                    boss_x, boss_y, boss_w, boss_h = boss.get_bounds()
                    
                    # Boss melee range is larger
                    if boss.direction.value == 1:  # Facing right
                        attack_hitbox = (boss_x + boss_w, boss_y, boss.melee_range, boss_h)
                    else:  # Facing left
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
            
            # Minions don't have melee attacks (they use projectiles)
            
            # --- 3. PLAYER ATTACK -> NPC/BOSS/MINION ---
            if player.state == 'attacking':
                # Player attack hitbox (phía trước player)
                px, py, pw, ph = player.x, player.y, player.width, player.height
                player_attack_range = 60  # Tầm đánh thường
                
                if player.facing_right:
                    attack_hitbox = (px + pw - 20, py + 20, player_attack_range, ph - 40)
                else:
                    attack_hitbox = (px - player_attack_range + 20, py + 20, player_attack_range, ph - 40)
                
                # Hit NPCs
                for npc in alive_npcs:
                    if not getattr(player, '_attack_hit_npc_' + str(id(npc)), False):
                        nx, ny, nw, nh = npc.get_bounds()
                        ax, ay, aw, ah = attack_hitbox
                        
                        if (ax < nx + nw and ax + aw > nx and ay < ny + nh and ay + ah > ny):
                            # Hit NPC!
                            setattr(player, '_attack_hit_npc_' + str(id(npc)), True)
                            npc.take_damage(PLAYER_ATTACK_DAMAGE)
                            player.on_hit_enemy(PLAYER_ATTACK_DAMAGE)
                            print(f"[COMBAT] Player hit NPC! NPC HP: {npc.health}")
                            
                            # Check if NPC died
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
                            # Hit Boss!
                            setattr(player, '_attack_hit_boss_' + str(id(boss)), True)
                            boss.take_damage(PLAYER_ATTACK_DAMAGE)
                            player.on_hit_enemy(PLAYER_ATTACK_DAMAGE)
                            print(f"[COMBAT] Player hit BOSS! Boss HP: {boss.health}/{boss.max_health}")
                            
                            # Check if boss died
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
                            # Hit Minion!
                            setattr(player, '_attack_hit_minion_' + str(id(minion)), True)
                            minion.take_damage(PLAYER_ATTACK_DAMAGE)
                            player.on_hit_enemy(PLAYER_ATTACK_DAMAGE)
                            print(f"[COMBAT] Player hit Boss Minion! Minion HP: {minion.health}")
                            
                            # Check if minion died
                            if minion.health <= 0:
                                kill_count += 1
                                player.on_kill_enemy()
                                print(f"[COMBAT] Minion killed! Total kills: {kill_count}")
            else:
                # Reset attack hit flags khi hết attacking
                for npc in npc_manager.npcs:
                    if hasattr(player, '_attack_hit_npc_' + str(id(npc))):
                        delattr(player, '_attack_hit_npc_' + str(id(npc)))
                for boss in boss_manager.bosses:
                    if hasattr(player, '_attack_hit_boss_' + str(id(boss))):
                        delattr(player, '_attack_hit_boss_' + str(id(boss)))
                    for minion in boss.minions:
                        if hasattr(player, '_attack_hit_minion_' + str(id(minion))):
                            delattr(player, '_attack_hit_minion_' + str(id(minion)))
            
            # --- 4. CHECK PLAYER DEATH (GAME OVER) ---
            if player.state == 'dead':
                game_over = True
                game_over_timer = 3.0  # 3 giây trước khi respawn
                print("[GAME] Player died! Game Over in 3 seconds...")
        
        else:
            # Game Over countdown
            game_over_timer -= dt
            if game_over_timer <= 0:
                # Respawn player
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
        
        # Box rendering
        for box in boxes:
            box.render(sdl_renderer, camera)

        # Render NPCs
        npc_manager.render_all(camera.camera.x, camera.camera.y)

        # Render Boss
        boss_manager.render_all(camera.camera.x, camera.camera.y)
        
        # Render NPC Projectiles (with camera offset)
        projectile_manager.render_all(camera.camera.x, camera.camera.y)
        
        # Render Player (với camera offset)
        p_dst = SDL_Rect(int(player.entity.sprite.x - camera.camera.x), 
                         int(player.entity.sprite.y - camera.camera.y), 
                         128, 128)
        p_tex = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, player.entity.sprite.surface)
        
        # [MỚI] RED FLASH EFFECT
        if player.flash_timer > 0:
            sdl2.SDL_SetTextureColorMod(p_tex, 255, 100, 100) # Tint Red (R=255, G=100, B=100) -> Bright Red
        
        sdl2.SDL_RenderCopy(sdl_renderer, p_tex, None, p_dst)
        sdl2.SDL_DestroyTexture(p_tex)
        
        # Render HUD (always on top, no camera offset)
        hud.render()

        renderer.present()
        sdl2.SDL_Delay(1000 // FPS)

    hud.cleanup()
    npc_manager.cleanup()
    projectile_manager.cleanup()
    sdl2.ext.quit()

if __name__ == "__main__":
    run()
