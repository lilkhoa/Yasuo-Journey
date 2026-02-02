import sys
import os
import sdl2
import sdl2.ext

# ==========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN (PATH SETUP)
# ==========================================
# Lấy đường dẫn file hiện tại (.../Game/testing/test_skill.py)
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# Lấy thư mục gốc (.../Game)
project_root = os.path.dirname(current_dir)

# Thêm root vào sys.path để import được folder 'entities', 'combat'
if project_root not in sys.path:
    sys.path.append(project_root)

# Chuyển thư mục làm việc về Root để game tìm thấy folder 'assets'
os.chdir(project_root)
print(f"Project Root: {project_root}")
print(f"Working Directory: {os.getcwd()}")

# ==========================================
# 2. IMPORTS
# ==========================================
try:
    from entities.player import Player
    from entities.npc import NPCManager, NPCState, Direction
    from combat.skill_q import update_q_logic
    from combat.skill_w import update_w_logic
except ImportError as e:
    print("\n!!! LỖI IMPORT !!!")
    print(f"Chi tiết: {e}")
    print("Hãy đảm bảo cấu trúc thư mục đúng: root/entities/player.py")
    sys.exit(1)

# ==========================================
# 3. CÁC CLASS & HÀM HỖ TRỢ
# ==========================================

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600

class SpriteWrapper:
    """
    Class này bọc NPC lại để Skill Q/E (hệ cũ) có thể đọc được tọa độ.
    Skill cũ dùng: npc.sprite.x
    NPC mới dùng: npc.x
    """
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
    """Gắn wrapper vào NPC"""
    npc.sprite = SpriteWrapper(npc)
    return npc

def render_surface_to_texture(sdl_renderer, surface, x, y):
    """
    Hàm vẽ Surface (của Player/Skill) lên cửa sổ Hardware.
    Chuyển đổi Surface -> Texture tức thời.
    """
    if surface is None: return
    texture = sdl2.SDL_CreateTextureFromSurface(sdl_renderer, surface)
    if not texture: return 
    
    w, h = surface.w, surface.h
    src_rect = sdl2.SDL_Rect(0, 0, w, h)
    dst_rect = sdl2.SDL_Rect(int(x), int(y), w, h)
    
    sdl2.SDL_RenderCopy(sdl_renderer, texture, src_rect, dst_rect)
    # Quan trọng: Hủy texture ngay sau khi vẽ để tránh tràn RAM
    sdl2.SDL_DestroyTexture(texture) 

# ==========================================
# 4. MAIN LOOP (VÒNG LẶP CHÍNH)
# ==========================================
def run_test():
    # Kiểm tra thư mục assets
    if not os.path.exists("assets"):
        print("\n!!! CẢNH BÁO: Không tìm thấy thư mục 'assets' tại Root!")
        return

    sdl2.ext.init()
    
    # --- KHỞI TẠO CỬA SỔ & RENDERER ---
    window = sdl2.ext.Window("Samurai vs Ghosts (Jump & Skills)", size=(SCREEN_WIDTH, SCREEN_HEIGHT))
    window.show()
    
    # Dùng Hardware Acceleration
    renderer_obj = sdl2.ext.Renderer(window, flags=sdl2.SDL_RENDERER_ACCELERATED)
    sdl_renderer = renderer_obj.sdlrenderer

    # Tạo Factory Software (cho Player/Skill load ảnh)
    factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    world = sdl2.ext.World()

    print("\n=== ĐANG LOAD TÀI NGUYÊN ===")
    
    # --- TẠO PLAYER ---
    try:
        player = Player(world, factory, 100, 350)
    except Exception as e:
        print(f"Lỗi tạo Player: {e}")
        return

    # --- TẠO NPC MANAGER ---
    npc_manager = NPCManager(factory, None, sdl_renderer)
    spawned_npcs = []

    # Hàm tiện ích để spawn quái an toàn
    def safe_spawn(func, name, x, y):
        try:
            n = func(x, y)
            if not n.sprites:
                print(f"[WARN] {name} spawn OK nhưng không có hình ảnh (Kiểm tra assets).")
            else:
                print(f"[OK] {name} spawned.")
            return make_npc_compatible(n)
        except Exception as e:
            print(f"[ERR] Lỗi spawn {name}: {e}")
            return None

    # Spawn quái mặc định
    g1 = safe_spawn(npc_manager.spawn_ghost, "Ghost", 600, 350)
    if g1: spawned_npcs.append(g1)

    s1 = safe_spawn(npc_manager.spawn_shooter, "Shooter", 800, 350)
    if s1: spawned_npcs.append(s1)
    
    o1 = safe_spawn(npc_manager.spawn_onre, "Onre", 400, 350)
    if o1: spawned_npcs.append(o1)

    print("\n=== HƯỚNG DẪN ĐIỀU KHIỂN ===")
    print(" [Mũi tên] : Di chuyển Trái/Phải")
    print(" [Space]   : NHẢY (Mới)")
    print(" [Q]       : Bắn Lốc")
    print(" [W]       : Cột Lửa")
    print(" [E]       : Lướt Chém")
    print(" [1, 2, 3] : Thả thêm quái")

    active_tornadoes = []
    active_walls = []
    running = True
    last_time = sdl2.SDL_GetTicks()

    while running:
        current_time = sdl2.SDL_GetTicks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time

        # --- XỬ LÝ SỰ KIỆN (INPUT) ---
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                keys = sdl2.SDL_GetKeyboardState(None)
                
                # Xác định hướng
                dash_dir = 0
                if keys[sdl2.SDL_SCANCODE_RIGHT]: dash_dir = 1
                elif keys[sdl2.SDL_SCANCODE_LEFT]: dash_dir = -1
                
                # Input Skill & Jump
                if key == sdl2.SDLK_SPACE:
                    player.jump()  # Gọi hàm nhảy mới
                elif key == sdl2.SDLK_q: 
                    player.start_q(dash_dir)
                elif key == sdl2.SDLK_w: 
                    player.start_w(dash_dir)
                elif key == sdl2.SDLK_e: 
                    player.start_e(world, factory, None, dash_dir)
                
                # Input Spawn Quái
                elif key == sdl2.SDLK_1:
                    n = safe_spawn(npc_manager.spawn_ghost, "Ghost", SCREEN_WIDTH-100, 350)
                    if n: spawned_npcs.append(n)
                elif key == sdl2.SDLK_2:
                    n = safe_spawn(npc_manager.spawn_shooter, "Shooter", SCREEN_WIDTH-100, 350)
                    if n: spawned_npcs.append(n)
                elif key == sdl2.SDLK_3:
                    n = safe_spawn(npc_manager.spawn_onre, "Onre", SCREEN_WIDTH-100, 350)
                    if n: spawned_npcs.append(n)

        # --- CẬP NHẬT LOGIC (UPDATE) ---
        keys = sdl2.SDL_GetKeyboardState(None)
        
        # 1. Update Player (Physics + Animation)
        player.update(dt, world, factory, None, active_tornadoes, active_walls)
        
        # 2. Update Di chuyển Player (Chỉ khi không bị cứng người do skill)
        if player.state in ['idle', 'jumping', 'dashing_e'] or (player.is_jumping and player.state == 'idle'):
            if keys[sdl2.SDL_SCANCODE_RIGHT]:
                player.sprite.x += int(player.move_speed * dt)
                player.facing_right = True
            elif keys[sdl2.SDL_SCANCODE_LEFT]:
                player.sprite.x -= int(player.move_speed * dt)
                player.facing_right = False
        
        # 3. Lọc danh sách NPC còn sống
        alive_npcs = [n for n in npc_manager.npcs if n.is_alive()]
        
        # 4. Update Skill E (Va chạm)
        player.skill_e.update_dash(dt, alive_npcs)
        if player.skill_e.is_dashing: 
            player.state = 'dashing_e'
        elif player.state == 'dashing_e' and not player.skill_e.is_dashing: 
            player.state = 'idle'

        # 5. Update Skills Q & W (Bay & Va chạm)
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

        # 6. Update NPC AI
        npc_manager.update_all(dt)
        p_x = player.sprite.x
        
        # AI đơn giản: Đuổi theo player
        for npc in alive_npcs:
            dist = abs(npc.x - p_x)
            if dist < npc.attack_range:
                npc.attack()
            elif dist < 400: # Tầm nhìn
                if npc.x < p_x: npc.move_right()
                else: npc.move_left()

        # --- VẼ HÌNH (RENDER) ---
        renderer_obj.clear(sdl2.ext.Color(30, 30, 30)) # Màu nền xám

        # Vẽ Skill (Surface -> Texture)
        for t in active_tornadoes:
            render_surface_to_texture(sdl_renderer, t.sprite.surface, t.sprite.x, t.sprite.y)
        for w in active_walls:
            render_surface_to_texture(sdl_renderer, w.sprite.surface, w.sprite.x, w.sprite.y)

        # Vẽ NPC (Texture trực tiếp)
        npc_manager.render_all()

        # Vẽ Player (Surface -> Texture)
        render_surface_to_texture(sdl_renderer, player.sprite.surface, player.sprite.x, player.sprite.y)

        renderer_obj.present()
        world.process()

        # --- QUAN TRỌNG: GIỚI HẠN FPS ---
        # Delay 16ms ~ 60 FPS. 
        # Giúp sửa lỗi "Lốc không bay" và "Nhân vật không đi" do máy chạy quá nhanh.
        sdl2.SDL_Delay(16)

    # Dọn dẹp
    npc_manager.cleanup()
    sdl2.ext.quit()

if __name__ == "__main__":
    run_test()