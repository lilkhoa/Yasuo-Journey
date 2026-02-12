import sdl2.ext
from combat.skill import Skill

class SkillE(Skill):
    def __init__(self, owner):
        super().__init__(owner, cooldown_time=0.5) # Hồi chiêu thấp
        self.dash_speed = 800
        self.dash_duration = 0.2
        self.is_dashing = False
        self.dash_timer = 0
        self.fixed_damage = 70
        self.hit_list = [] # Danh sách npc đã bị chém trong lần lướt này

    def execute(self, world, factory, renderer):
        if self.is_dashing: return None # Đang lướt thì không lướt tiếp được
        
        print("Casting E: Lướt!")
        self.is_dashing = True
        self.dash_timer = 0
        self.hit_list = [] # Reset danh sách trúng
        return self # Trả về chính nó để main loop xử lý update

    def update_dash(self, dt, npcs, boxes=None):
        if not self.is_dashing:
            return

        self.dash_timer += dt
        
        # 1. Di chuyển nhân vật
        direction = 1 if self.owner.facing_right else -1
        move_dist = self.dash_speed * dt * direction
        
        # --- Box collision: stop dash if hitting a box ---
        if boxes:
            import sdl2
            hitbox = self.owner.get_hitbox()
            future_rect = sdl2.SDL_Rect(hitbox.x + int(move_dist), hitbox.y, hitbox.w, hitbox.h)
            
            for box in boxes:
                if sdl2.SDL_HasIntersection(future_rect, box.rect):
                    # Snap to box edge
                    if direction > 0:  # Dashing right
                        self.owner.sprite.x = box.rect.x - 128 + 44 - 2
                    else:  # Dashing left
                        self.owner.sprite.x = box.rect.x + box.rect.w - 44 + 2
                    self.is_dashing = False
                    self.hit_list = []
                    return
        
        self.owner.sprite.x += int(move_dist)

        # 2. Gây dame trên đường lướt
        player_rect = (self.owner.sprite.x, self.owner.sprite.y, 
                       self.owner.sprite.size[0], self.owner.sprite.size[1])

        for npc in npcs:
            if npc in self.hit_list: continue # Đã chém rồi thì bỏ qua
            
            n_rect = (npc.sprite.x, npc.sprite.y, npc.sprite.size[0], npc.sprite.size[1])
            
            # Va chạm
            if (player_rect[0] < n_rect[0] + n_rect[2] and player_rect[0] + player_rect[2] > n_rect[0] and
                player_rect[1] < n_rect[1] + n_rect[3] and player_rect[1] + player_rect[3] > n_rect[1]):
                
                print(f"E Slash! Gây {self.fixed_damage} damage lên NPC.")
                self.hit_list.append(npc)
                # npc.hp -= self.fixed_damage

        # 3. Kết thúc lướt
        if self.dash_timer >= self.dash_duration:
            self.is_dashing = False
            self.hit_list = []