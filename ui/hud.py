"""
Skill Bar HUD Module
League of Legends-style skill bar with resource bars, skill icons, and stats panel.
Supports multiple characters dynamically.
"""
import os
import ctypes
import time
import sdl2
import sdl2.ext
from settings import WINDOW_WIDTH, WINDOW_HEIGHT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "..", "assets/fonts/arial.ttf")

class SkillBarHUD:
    """
    Renders the skill bar HUD at the bottom of the screen.
    Dynamically supports any character with a skills list.
    """
    
    def __init__(self, renderer, player, character_type='player1', icon_map=None):
        """
        Initialize the HUD.
        
        Args:
            renderer: SDL2 renderer
            player: Player object with skills list
            character_type: 'player1' (Yasuo) or 'player2' (new character)
            icon_map: Optional dict mapping skill key to texture (for custom icons)
        """
        self.renderer = renderer
        self.player = player
        self.character_type = character_type
        self.icon_map = icon_map if icon_map else {}
        self.last_cast_times = {}  # Track last cast times for cooldown display
        
        # --- SKILL ICONS CONFIG ---
        self.icon_size = 48
        self.icon_spacing = 6
        self.skill_keys = ['Q', 'W', 'E', 'R', 'A']  # 5 slots
        self.skill_levels = {'Q': 1, 'W': 1, 'E': 1, 'R': 1, 'A': 1}
        
        # --- RESOURCE BAR CONFIG ---
        self.bar_height = 8
        self.bar_spacing = 2
        self.bars_padding_top = 4
        
        # --- SKILL BAR LAYOUT CALCULATION ---
        num_skills = len(self.skill_keys)
        content_width = (num_skills * self.icon_size) + ((num_skills - 1) * self.icon_spacing)
        content_height = self.icon_size + self.bars_padding_top + (self.bar_height * 2) + self.bar_spacing
        
        self.padding_x = 4
        self.padding_y = 4
        
        self.skill_bar_width = content_width + (self.padding_x * 2)
        self.skill_bar_height = content_height + (self.padding_y * 2)
        
        self.skill_bar_x = (WINDOW_WIDTH - self.skill_bar_width) // 2
        self.skill_bar_y = WINDOW_HEIGHT - self.skill_bar_height - 5
        
        self.bar_width = content_width
        self.bar_x = self.skill_bar_x + self.padding_x
        
        # --- STATS PANEL CONFIG ---
        self.stats_panel_width = 250
        self.stats_panel_height = 60
        self.stats_panel_x = 20
        self.stats_panel_y = WINDOW_HEIGHT - self.stats_panel_height - 5
        
        # Load textures
        self.skill_icons = {}
        self.stat_icons = {}
        self.no_mana_overlay = None
        self._load_textures()
        
        try:
            self.font_manager = sdl2.ext.FontManager(FONT_PATH, size=14, color=(255, 255, 255))
            self.font_cd = sdl2.ext.FontManager(FONT_PATH, size=10, color=(255, 255, 255))
        except Exception as e:
            print(f"[HUD] Failed to load font: {e}")
            self.font_manager = None
            self.font_cd = None
            
        # Colors
        self.COLOR_HP = (220, 50, 50)
        self.COLOR_MANA = (50, 120, 220)
        self.COLOR_STAMINA = (220, 180, 50)
        self.COLOR_BG = (20, 20, 30)
        self.COLOR_BORDER = (80, 80, 100)

        # --- INVENTORY CONFIG ---
        self.inv_x = 20
        self.inv_y = 20
        self.slot_size = 32
        self.slot_spacing = 4
        
    def _load_textures(self):
        """Load skill and stat icon textures dynamically."""
        base_skill_path = os.path.join("assets", "Skill_Icons")
        base_stat_path = os.path.join("assets", "Stats")
        
        # Load no-mana overlay
        no_mana_path = os.path.join(base_skill_path, "no-mana.jpg")
        if os.path.exists(no_mana_path):
            self.no_mana_overlay = self._load_texture(no_mana_path)
        
        # Load skill icons - character-specific first, then fallback to generic
        character_specific_path = None
        if self.character_type == 'player2':
            character_specific_path = os.path.join(base_skill_path, "Player_2")
        
        for skill in ['Q', 'W', 'E', 'R', 'A', 'S', 'passive']:
            # Try character-specific first
            if character_specific_path:
                filepath = os.path.join(character_specific_path, f"{skill}.png")
                if os.path.exists(filepath):
                    self.skill_icons[skill] = self._load_texture(filepath)
                    continue
            
            # Fall back to generic
            filepath = os.path.join(base_skill_path, f"{skill}.png")
            if os.path.exists(filepath):
                self.skill_icons[skill] = self._load_texture(filepath)
        
        # Load stat icons
        stat_files = {
            'HP': 'HP.png',
            'Regen': 'HP_regen.png',
            'Mana': 'Mana.png',
            'Speed': 'Speed.png',
            'AD': 'AD.png',                 
            'AttackSpeed': 'Attack_speed.png',
            'Range': 'Attack_range.png',
            'Armor': 'AR.png',
            'Crit': 'Crit.png',
            'LifeSteal': 'Life_steal.png'   
        }
        for stat_name, filename in stat_files.items():
            filepath = os.path.join(base_stat_path, filename)
            if os.path.exists(filepath):
                self.stat_icons[stat_name] = self._load_texture(filepath)
                
    def _load_texture(self, filepath):
        try:
            surface = sdl2.ext.load_image(filepath)
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            sdl2.SDL_FreeSurface(surface)
            return texture
        except Exception as e:
            print(f"[HUD] Failed to load {filepath}: {e}")
            return None
    
    def render(self):
        """Render the complete HUD."""
        self._render_skill_bar()
        self._render_stats_panel()
        self._render_inventory()
    
    def _render_skill_bar(self):
        """Render the centralized skill bar (Background + Icons + Resource Bars)."""
        # 1. Skill Bar Background (Tight fit)
        bg_rect = sdl2.SDL_Rect(self.skill_bar_x, self.skill_bar_y, 
                               self.skill_bar_width, self.skill_bar_height)
        
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 20, 20, 30, 240) # Higher opacity
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Border
        sdl2.SDL_SetRenderDrawColor(self.renderer, 100, 90, 60, 255) # Gold-ish border
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
        
        # 2. Skill Icons
        self._render_skill_icons()
        
        # 3. Resource bars (Inside tight box)
        self._render_resource_bars()
        
    def _render_stats_panel(self):
        """Render the separated stats panel on the left."""
        # 1. Panel Background
        bg_rect = sdl2.SDL_Rect(self.stats_panel_x, self.stats_panel_y, 
                               self.stats_panel_width, self.stats_panel_height)
        
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 35, 40, 200) 
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 80, 80, 100, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)

        # 2. Stats Grid (3 Cols x 3 Rows)
        col_width = 80 # widened checks
        col1_x = self.stats_panel_x + 10
        col2_x = col1_x + col_width
        col3_x = col2_x + col_width
        
        start_y = self.stats_panel_y + 10
        line_h = 24
        icon_s = 18
        
        # [UPDATED] Lấy đúng tên biến trong player.py
        # attack_damage (int), attack_speed (float), crit_chance (int/float)
        # lifesteal_ratio (float 0.1 -> 10%), attack_range (int), move_speed (prop)
        # armor (int), hp_regen (float), max_stamina (int)
        
        stats_data = [
            # Col 1: Offensive
            (col1_x, start_y, 'AD', f"{getattr(self.player, 'attack_damage', 0)}"),
            (col1_x, start_y + line_h, 'Crit', f"{getattr(self.player, 'crit_chance', 0)}%"),
            
            # Col 2: Utility / Combat
            (col2_x, start_y, 'Range', f"{getattr(self.player, 'attack_range', 0)}"),
            (col2_x, start_y + line_h, 'Speed', f"{int(getattr(self.player, 'move_speed', 0))}"),
            
            # Col 3: Defensive / Resource
            (col3_x, start_y, 'Armor', f"{getattr(self.player, 'armor', 0)}"),
            (col3_x, start_y + line_h, 'LifeSteal', f"{int(getattr(self.player, 'lifesteal_ratio', 0) * 100)}%"),
        ]
        
        for x, y, icon_key, text in stats_data:
            # Icon
            if icon_key in self.stat_icons:
                dst = sdl2.SDL_Rect(x, y, icon_s, icon_s)
                sdl2.SDL_RenderCopy(self.renderer, self.stat_icons[icon_key], None, dst)
            
            # Text Rendering
            if self.font_manager:
                text_surface = self.font_manager.render(text)
                text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, text_surface)
                
                # Center vertically with icon
                text_w = text_surface.w
                text_h = text_surface.h
                text_dst = sdl2.SDL_Rect(x + icon_s + 4, y + (icon_s - text_h)//2 - 1, text_w, text_h)
                
                sdl2.SDL_RenderCopy(self.renderer, text_texture, None, text_dst)
                sdl2.SDL_FreeSurface(text_surface)
                sdl2.SDL_DestroyTexture(text_texture)

    def _render_resource_bars(self):
        """Render HP and Stamina bars, tightly packed under icons."""
        bars = [
            (self.player.hp, self.player.max_hp, self.COLOR_HP),
            (self.player.stamina, self.player.max_stamina, self.COLOR_STAMINA),
        ]
        
        # Calculate Y starting position for bars (just below icons + padding)
        # skill_bar_y + padding_y + icon_size + bars_padding_top
        start_y = self.skill_bar_y + self.padding_y + self.icon_size + self.bars_padding_top
        
        for i, (current, max_val, color) in enumerate(bars):
            bar_y = start_y + i * (self.bar_height + self.bar_spacing)
            
            # Background
            sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 50, 255)
            # Full width of the content area
            bg_rect = sdl2.SDL_Rect(self.bar_x, bar_y, 
                                     self.bar_width, self.bar_height)
            sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
            
            # Filled
            fill_width = int((current / max_val) * self.bar_width) if max_val > 0 else 0
            fill_width = max(0, min(fill_width, self.bar_width))
            
            sdl2.SDL_SetRenderDrawColor(self.renderer, color[0], color[1], color[2], 255)
            fill_rect = sdl2.SDL_Rect(self.bar_x, bar_y, fill_width, self.bar_height)
            sdl2.SDL_RenderFillRect(self.renderer, fill_rect)
            
            # Nice Border for bars (1px black)
            sdl2.SDL_SetRenderDrawColor(self.renderer, 10, 10, 10, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
            
    def _render_skill_icons(self):
        """Render skill icons centered inside skill bar from player.skills list."""
        start_x = self.skill_bar_x + self.padding_x
        icon_y = self.skill_bar_y + self.padding_y
        
        # Iterate through player.skills and self.skill_keys in parallel
        for i in range(len(self.skill_keys)):
            if i >= len(self.player.skills):
                break
            
            skill_obj = self.player.skills[i]
            skill_key = self.skill_keys[i]
            icon_x = start_x + i * (self.icon_size + self.icon_spacing)
            
            # Icon Background
            sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 30, 40, 255)
            bg_rect = sdl2.SDL_Rect(icon_x, icon_y, self.icon_size, self.icon_size)
            sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
            
            # Draw Icon
            if skill_key in self.skill_icons:
                sdl2.SDL_RenderCopy(self.renderer, self.skill_icons[skill_key], None, bg_rect)
            
            # Only render cooldown if skill exists
            if skill_obj is not None:
                # Cooldown Overlay
                cooldown = self._get_cooldown_remaining(skill_key)
                max_cd = self._get_cooldown_max(skill_key)
                
                # Check if skill needs mana indicator
                needs_mana_overlay = False
                if cooldown <= 0 and i < 3:  # Q, W, E are stamina skills
                    skill_cost = self._get_skill_cost(skill_key)
                    if self.player.stamina < skill_cost:
                        needs_mana_overlay = True
                
                if cooldown > 0:
                    sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 200)
                    
                    ratio = cooldown / max_cd if max_cd > 0 else 0
                    h = int(self.icon_size * ratio)
                    overlay = sdl2.SDL_Rect(icon_x, icon_y + (self.icon_size - h), self.icon_size, h)
                    sdl2.SDL_RenderFillRect(self.renderer, overlay)

                    # Render Cooldown Text (White, Centered 1 decimal)
                    if self.font_cd:
                        seconds = cooldown / 60.0
                        if seconds > 0:
                            text_surface = self.font_cd.render(f"{seconds:.1f}")
                            text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, text_surface)
                            
                            text_w = text_surface.w
                            text_h = text_surface.h
                            text_dst = sdl2.SDL_Rect(
                                icon_x + (self.icon_size - text_w)//2,
                                icon_y + (self.icon_size - text_h)//2, 
                                text_w, text_h
                            )
                            sdl2.SDL_RenderCopy(self.renderer, text_texture, None, text_dst)
                            sdl2.SDL_FreeSurface(text_surface)
                            sdl2.SDL_DestroyTexture(text_texture)
                
                # No-Mana Overlay
                if needs_mana_overlay and self.no_mana_overlay:
                    sdl2.SDL_SetTextureAlphaMod(self.no_mana_overlay, 180)
                    sdl2.SDL_SetTextureBlendMode(self.no_mana_overlay, sdl2.SDL_BLENDMODE_BLEND)
                    sdl2.SDL_RenderCopy(self.renderer, self.no_mana_overlay, None, bg_rect)
                    sdl2.SDL_SetTextureAlphaMod(self.no_mana_overlay, 255)
                
                # Border
                color = (255, 215, 0, 255) if cooldown <= 0 and not needs_mana_overlay else (100, 100, 100, 255)
                sdl2.SDL_SetRenderDrawColor(self.renderer, *color)
                sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)
                
                # Level dots
                p_skill_key = skill_key.lower()
                level = self.player.skill_levels.get(p_skill_key, 0)
                self._draw_level_indicator(icon_x, icon_y + self.icon_size - 6, level)

                # UPGRADE INDICATOR (+)
                if hasattr(self.player, 'can_upgrade_skill') and self.player.can_upgrade_skill(p_skill_key):
                    # Draw Plus Sign at top-right
                    plus_size = 14
                    px = icon_x + self.icon_size - plus_size - 2
                    py = icon_y + 2
                    
                    # Horizontal bar
                    r1 = sdl2.SDL_Rect(px, py + plus_size//2 - 2, plus_size, 4)
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 215, 0, 255)
                    sdl2.SDL_RenderFillRect(self.renderer, r1)
                    
                    # Vertical bar
                    r2 = sdl2.SDL_Rect(px + plus_size//2 - 2, py, 4, plus_size)
                    sdl2.SDL_RenderFillRect(self.renderer, r2)
            else:
                # Empty slot - just draw border
                sdl2.SDL_SetRenderDrawColor(self.renderer, 60, 60, 70, 255)
                sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)

    def _get_cooldown_remaining(self, skill_key):
        """Get remaining cooldown in frames for a skill."""
        # Map skill key to skills list index
        key_to_index = {'Q': 0, 'W': 1, 'E': 2, 'R': 3, 'A': 4}
        index = key_to_index.get(skill_key)
        
        if index is None or index >= len(self.player.skills):
            return 0
        
        skill_obj = self.player.skills[index]
        if skill_obj is None:
            return 0
        
        # Check if skill has cooldown_manager
        if hasattr(skill_obj, 'cooldown_manager'):
            return skill_obj.cooldown_manager.get_cooldown_remaining()
        
        # Fallback: check player's cooldown_manager
        if hasattr(self.player, 'cooldowns'):
            skill_map = {0: 'skill_q', 1: 'skill_w', 2: 'skill_e', 3: 'skill_r', 4: 'skill_a'}
            name = skill_map.get(index, skill_key.lower())
            return self.player.cooldowns.cooldowns.get(name, 0)
        
        return 0
    
    def _get_cooldown_max(self, skill_key):
        """Get max cooldown in frames for a skill."""
        key_to_index = {'Q': 0, 'W': 1, 'E': 2, 'R': 3, 'A': 4}
        index = key_to_index.get(skill_key)
        
        if index is None or index >= len(self.player.skills):
            return 60
        
        skill_obj = self.player.skills[index]
        if skill_obj is None:
            return 60
        
        # Get cooldown_time from skill object (in frames)
        if hasattr(skill_obj, 'cooldown_time'):
            return skill_obj.cooldown_time
        
        # Fallback defaults
        defaults = {0: 45, 1: 30, 2: 15, 3: 120, 4: 30}  # Q, W, E, R, Attack cooldowns in frames
        return defaults.get(index, 60)
    
    def _get_skill_cost(self, skill_key):
        """Get stamina cost for a skill."""
        key_to_index = {'Q': 0, 'W': 1, 'E': 2, 'R': 3, 'A': 4}
        index = key_to_index.get(skill_key)
        
        if index is None or index >= len(self.player.skills):
            return 0
        
        skill_obj = self.player.skills[index]
        if skill_obj is None:
            return 0
        
        # Get stamina_cost from skill object
        if hasattr(skill_obj, 'stamina_cost'):
            return skill_obj.stamina_cost
        
        return 0

    def _draw_level_indicator(self, x, y, level):
        """Draw small dots indicating skill level inside icon bottom."""
        dot_size = 4
        spacing = 2
        total_w = level * dot_size + (level - 1) * spacing
        # Centered horizontally within icon
        start_x = x + (self.icon_size - total_w) // 2
        
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 200, 255) # Bright dots
        for i in range(level):
            r = sdl2.SDL_Rect(start_x + i*(dot_size+spacing), y, dot_size, dot_size)
            sdl2.SDL_RenderFillRect(self.renderer, r)

    def _render_inventory(self):
        # 1. Coin Row
        x, y = self.inv_x, self.inv_y
        coin_tex = self.icon_map.get("COIN_ICON")
        if coin_tex:
            dst = sdl2.SDL_Rect(x, y, 24, 24)
            sdl2.SDL_RenderCopy(self.renderer, coin_tex, None, dst)
        
        # Draw Amount
        if self.font_manager:
            txt_surf = self.font_manager.render(f"{self.player.gold}")
            txt_tex = sdl2.SDL_CreateTextureFromSurface(self.renderer, txt_surf)

            dst = sdl2.SDL_Rect(x + 30, y + 5, txt_surf.w, txt_surf.h)
            sdl2.SDL_RenderCopy(self.renderer, txt_tex, None, dst)

            sdl2.SDL_FreeSurface(txt_surf)
            sdl2.SDL_DestroyTexture(txt_tex)

        # 2. Consumable Row (3 slots)
        x = 3 * WINDOW_WIDTH // 4
        y = WINDOW_HEIGHT - int(1.2 * WINDOW_HEIGHT//10)
        for i in range(3):
            sx = x + i * (self.slot_size + self.slot_spacing)
            slot_rect = sdl2.SDL_Rect(sx, y, self.slot_size, self.slot_size)
            
            # Background
            sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 200)
            sdl2.SDL_RenderFillRect(self.renderer, slot_rect)
            
            # Border
            sdl2.SDL_SetRenderDrawColor(self.renderer, 150, 150, 150, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, slot_rect)
            
            # Item Icon
            if i < len(self.player.consumables):
                item_type = self.player.consumables[i]
                tex = self.icon_map.get(item_type)
                if tex:
                    sdl2.SDL_RenderCopy(self.renderer, tex, None, slot_rect)
            
            # Key Number (1, 2, 3)
            # Draw Amount
            if self.font_manager:
                txt_surf = self.font_manager.render(f"{i+1}")
                txt_tex = sdl2.SDL_CreateTextureFromSurface(self.renderer, txt_surf)

                dst = sdl2.SDL_Rect(    # render at left-bottom corner
                    sx, 
                    y + self.slot_size - 5, 
                    9, 
                    9)
                sdl2.SDL_RenderCopy(self.renderer, txt_tex, None, dst)

                sdl2.SDL_FreeSurface(txt_surf)
                sdl2.SDL_DestroyTexture(txt_tex)

        # 3. Equipment Row (5 Slots)
        y += self.slot_size + 10
        for i in range(5):
            sx = x + i * (self.slot_size + self.slot_spacing)
            slot_rect = sdl2.SDL_Rect(sx, y, self.slot_size, self.slot_size)
            
            sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 200)
            sdl2.SDL_RenderFillRect(self.renderer, slot_rect)
            
            sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 215, 0, 255) # Gold border for equipment
            sdl2.SDL_RenderDrawRect(self.renderer, slot_rect)
            
            if i < len(self.player.equipment):
                item_type = self.player.equipment[i]
                tex = self.icon_map.get(item_type)
                if tex:
                    sdl2.SDL_RenderCopy(self.renderer, tex, None, slot_rect)
        
    def cleanup(self):
        for t in self.skill_icons.values():
            if t: sdl2.SDL_DestroyTexture(t)
        for t in self.stat_icons.values():
            if t: sdl2.SDL_DestroyTexture(t)
        if self.no_mana_overlay:
            sdl2.SDL_DestroyTexture(self.no_mana_overlay)