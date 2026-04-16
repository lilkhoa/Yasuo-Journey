import sdl2.ext
import sdl2
from combat.refactored_skill import BaseSkill

# --- REFACTORED CLASS ---
class SkillE(BaseSkill):
    """Bản chất là DashSkill"""
    def __init__(self, owner):
        super().__init__(owner, name="Dash", base_cooldown=0.5) 
        self.dash_speed = 800
        self.dash_duration = 0.2
        self.is_dashing = False
        self.dash_timer = 0
        
        from settings import DAMAGE_SKILL_E
        self.base_damage = DAMAGE_SKILL_E
        self.hit_list = [] 

    def execute(self, world=None, factory=None, renderer=None, **kwargs):
        if self.is_dashing: return None
        self.is_dashing = True
        self.dash_timer = 0
        self.hit_list = [] 
        return self 

    def update_dash(self, dt, enemies, boxes=None, game_map=None, network_ctx=None):
        if not self.is_dashing: return

        self.dash_timer += dt
        direction = 1 if self.owner.facing_right else -1
        move_dist = self.dash_speed * dt * direction
        
        hitbox = self.owner.get_hitbox()
        future_rect = sdl2.SDL_Rect(hitbox.x + int(move_dist), hitbox.y, hitbox.w, hitbox.h)

        # 1. Collision Tường
        if game_map:
            tiles = game_map.get_tile_rects_around(future_rect.x, future_rect.y, future_rect.w, future_rect.h)
            for tile in tiles:
                if sdl2.SDL_HasIntersection(future_rect, tile):
                    if direction > 0: self.owner.entity.sprite.x = tile.x - 128 + 44 - 2
                    else: self.owner.entity.sprite.x = tile.x + tile.w - 44 + 2
                    self.is_dashing = False
                    return

        # 2. Collision Hộp
        if boxes:
            for box in boxes:
                if sdl2.SDL_HasIntersection(future_rect, box.rect):
                    if direction > 0: self.owner.entity.sprite.x = box.rect.x - 128 + 44 - 2
                    else: self.owner.entity.sprite.x = box.rect.x + box.rect.w - 44 + 2
                    self.is_dashing = False
                    return
        
        self.owner.entity.sprite.x += int(move_dist)

        # 3. Gây sát thương quét
        p_rect = self.owner.get_hitbox()
        for target in enemies:
            if target in self.hit_list: continue
            if hasattr(target, 'health') and target.health <= 0: continue
            
            if hasattr(target, 'get_bounds'):
                tx, ty, tw, th = target.get_bounds()
                t_rect = sdl2.SDL_Rect(int(tx), int(ty), int(tw), int(th))
            else:
                t_rect = sdl2.SDL_Rect(int(target.sprite.x), int(target.sprite.y), 
                                       int(target.sprite.size[0]), int(target.sprite.size[1]))
            
            if sdl2.SDL_HasIntersection(p_rect, t_rect):
                damage = self.base_damage * self.damage_multiplier
                target_net_id = getattr(target, 'net_id', id(target))
                
                if network_ctx:
                    is_multi, is_host, game_client = network_ctx
                    if is_multi and game_client and game_client.is_connected():
                        etype = 'boss' if target.__class__.__name__ == 'Boss' else 'npc'
                        game_client.send_hit_event(etype, target_net_id, damage)
                    else:
                        if hasattr(target, 'take_damage'): target.take_damage(damage)
                else:
                    if hasattr(target, 'take_damage'): target.take_damage(damage)
                
                self.hit_list.append(target)

        # 4. End Dash
        if self.dash_timer >= self.dash_duration:
            self.is_dashing = False
            self.hit_list = []