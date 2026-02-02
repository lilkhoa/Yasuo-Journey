import sdl2
import sdl2.ext
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')
SKILL_ASSET_DIR = os.path.join(root_dir, 'assets', 'Skills')

from combat.skill_q import SkillQ, load_tornado_assets
from combat.skill_w import SkillW, load_wall_assets
from combat.skill_e import SkillE
from combat.utils import load_grid_sprite_sheet, flip_sprites_horizontal 

class Player:
    def __init__(self, world, factory, x, y):
        self.anims_right = {}
        self.anims_right['idle'] = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Idle.png"), cols=6, rows=1)
        self.anims_right['q']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_2.png"), cols=4, rows=1)
        self.anims_right['w']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Shield.png"), cols=2, rows=1)
        self.anims_right['e']    = load_grid_sprite_sheet(factory, os.path.join(PLAYER_ASSET_DIR, "Attack_3.png"), cols=3, rows=1)

        if not self.anims_right['idle']: 
            self.anims_right['idle'] = [factory.from_color(sdl2.ext.Color(255,0,0), (40,60))]

        self.anims_left = {}
        for key, sprites in self.anims_right.items():
            self.anims_left[key] = flip_sprites_horizontal(factory, sprites)

        self.tornado_frames = load_tornado_assets(factory, SKILL_ASSET_DIR)
        self.wall_frames = load_wall_assets(factory, SKILL_ASSET_DIR)
        
        self.entity = sdl2.ext.Entity(world)
        self.entity.sprite = self.anims_right['idle'][0] 
        self.entity.sprite.position = x, y
        self.facing_right = True 
        
        self.move_speed = 200
        self.state = 'idle'
        self.frame_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.15
        
        self.skill_q = SkillQ(self)
        self.skill_w = SkillW(self)
        self.skill_e = SkillE(self)

    @property
    def sprite(self):
        return self.entity.sprite

    def update(self, dt, world, factory, renderer, active_list_q, active_list_w):
        self.anim_timer += dt
        
        current_anims = self.anims_right if self.facing_right else self.anims_left
        
        current_frames = []
        if self.state == 'idle': current_frames = current_anims['idle']
        elif self.state == 'casting_q': current_frames = current_anims['q']
        elif self.state == 'casting_w': current_frames = current_anims['w']
        elif self.state == 'dashing_e': current_frames = current_anims['e']
        
        if not current_frames: return

        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.frame_index += 1
            
            if self.frame_index >= len(current_frames):
                if self.state == 'casting_q':
                    self.spawn_tornado(world, factory, renderer, active_list_q)
                    self.state = 'idle'
                elif self.state == 'casting_w':
                    self.spawn_wall(world, factory, renderer, active_list_w)
                    self.state = 'idle'
                elif self.state == 'dashing_e':
                     if not self.skill_e.is_dashing: self.state = 'idle'
                self.frame_index = 0
        
        idx = self.frame_index % len(current_frames)
        old_x, old_y = self.entity.sprite.position
        self.entity.sprite = current_frames[idx]
        self.entity.sprite.position = old_x, old_y

    def start_q(self, direction=0):
        if self.state == 'idle':
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            
            self.state = 'casting_q'
            self.frame_index = 0
            self.anim_timer = 0
            
    def start_w(self, direction=0):
        if self.state == 'idle':
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            
            self.state = 'casting_w'
            self.frame_index = 0
            self.anim_timer = 0
            
    def start_e(self, world, factory, renderer, direction):
        if direction == 0: return
        if self.state != 'dashing_e':
            if direction > 0: self.facing_right = True
            elif direction < 0: self.facing_right = False
            self.state = 'dashing_e'
            self.frame_index = 0
            self.skill_e.cast(world, factory, renderer)

    def spawn_tornado(self, world, factory, renderer, active_list):
        if self.tornado_frames:
            t = self.skill_q.cast(world, factory, renderer, skill_sprites=self.tornado_frames)
            if t: active_list.append(t)

    def spawn_wall(self, world, factory, renderer, active_list):
        if self.wall_frames:
            w = self.skill_w.cast(world, factory, renderer, skill_sprites=self.wall_frames)
            if w: active_list.append(w)