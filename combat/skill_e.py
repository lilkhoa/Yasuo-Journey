import sdl2.ext
import sdl2
from combat.skill import Skill

class SkillE(Skill):
    def __init__(self, owner):
        super().__init__(owner, cooldown_time=0.5) 
        self.dash_speed = 800
        self.dash_duration = 0.2
        self.is_dashing = False
        self.dash_timer = 0
        self.fixed_damage = 70
        self.hit_list = [] # Danh sách kẻ địch đã bị chém trong lần lướt này

    def execute(self, world, factory, renderer):
        if self.is_dashing: return None
        
        print("Casting E: Lướt!")
        self.is_dashing = True
        self.dash_timer = 0
        self.hit_list = [] # Reset danh sách trúng
        return self 

    def update_dash(self, dt, enemies, boxes=None):
        """
        enemies: List NPC/Boss/Minions
        """
        if not self.is_dashing:
            return

        self.dash_timer += dt
        
        # 1. Di chuyển nhân vật
        direction = 1 if self.owner.facing_right else -1
        move_dist = self.dash_speed * dt * direction
        
        # --- Box collision (Dừng lướt nếu đụng vật cản) ---
        if boxes:
            hitbox = self.owner.get_hitbox()
            future_rect = sdl2.SDL_Rect(hitbox.x + int(move_dist), hitbox.y, hitbox.w, hitbox.h)
            
            for box in boxes:
                if sdl2.SDL_HasIntersection(future_rect, box.rect):
                    # Snap vào cạnh hộp
                    if direction > 0:  
                        self.owner.entity.sprite.x = box.rect.x - 128 + 44 - 2
                    else:  
                        self.owner.entity.sprite.x = box.rect.x + box.rect.w - 44 + 2
                    self.is_dashing = False # Dừng lướt
                    return
        
        self.owner.entity.sprite.x += int(move_dist)

        # 2. Gây dame trên đường lướt (SỬA LẠI LOGIC VA CHẠM)
        # Lấy hitbox của người chơi
        p_rect = self.owner.get_hitbox()

        for target in enemies:
            # Bỏ qua nếu đã chém trúng trong lần lướt này hoặc target đã chết
            if target in self.hit_list: continue
            if hasattr(target, 'health') and target.health <= 0: continue
            
            # Lấy hitbox của mục tiêu (NPC/Boss)
            if hasattr(target, 'get_bounds'):
                tx, ty, tw, th = target.get_bounds()
                t_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
            else:
                # Fallback cho object đơn giản
                t_rect = sdl2.SDL_Rect(int(target.sprite.x), int(target.sprite.y), 
                                       int(target.sprite.size[0]), int(target.sprite.size[1]))
            
            # Kiểm tra va chạm
            if sdl2.SDL_HasIntersection(p_rect, t_rect):
                print(f"E Slash Hit! Gây {self.fixed_damage} damage.")
                
                # --- QUAN TRỌNG: GÂY DAMAGE THẬT SỰ ---
                if hasattr(target, 'take_damage'):
                    target.take_damage(self.fixed_damage)
                
                # Thêm vào danh sách đã đánh trúng (để không hit 1 quái nhiều lần trong 1 lần lướt)
                self.hit_list.append(target)

        # 3. Kết thúc lướt
        if self.dash_timer >= self.dash_duration:
            self.is_dashing = False
            self.hit_list = []