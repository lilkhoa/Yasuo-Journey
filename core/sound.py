"""
Sound Manager Module
Centralized audio management for the entire game using SDL2_mixer.
"""
import os
import sdl2
import sdl2.sdlmixer


class SoundManager:
    """
    Centralized sound manager for all game audio.
    
    Handles initialization, loading, playing, and cleanup of all sound effects and music.
    """
    
    def __init__(self):
        """Initialize the sound manager."""
        self.initialized = False
        self.sounds = {}
        self.music = None
        
    def initialize(self, frequency=44100, format_type=None, channels=2, chunk_size=2048):
        """
        Initialize SDL2 audio system.
        
        Args:
            frequency: Audio frequency (default: 44100 Hz)
            format_type: Audio format (default: MIX_DEFAULT_FORMAT)
            channels: Number of audio channels (default: 2 for stereo)
            chunk_size: Audio buffer size (default: 2048)
            
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        if self.initialized:
            return True
        
        # Use default format if not specified
        if format_type is None:
            format_type = sdl2.sdlmixer.MIX_DEFAULT_FORMAT
        
        # Initialize SDL2 mixer
        if sdl2.sdlmixer.Mix_OpenAudio(frequency, format_type, channels, chunk_size) != 0:
            return False
        
        self.initialized = True
        return True
    
    def load_sound(self, sound_id, filepath):
        """
        Load a sound effect from file.
        
        Args:
            sound_id: Unique identifier for this sound
            filepath: Path to the sound file
            
        Returns:
            bool: True if sound loaded successfully, False otherwise
        """
        if not self.initialized:
            return False
        
        # Check if already loaded
        if sound_id in self.sounds and self.sounds[sound_id] is not None:
            return True
        
        # Check if file exists
        if not os.path.exists(filepath):
            return False
        
        # Load sound
        try:
            sound_chunk = sdl2.sdlmixer.Mix_LoadWAV(filepath.encode('utf-8'))
            if sound_chunk:
                self.sounds[sound_id] = sound_chunk
                return True
            else:
                return False
        except Exception as e:
            return False
    
    def play_sound(self, sound_id, loops=0, channel=-1, duration=-1):
        """
        Play a loaded sound effect.
        
        Args:
            sound_id: Identifier of the sound to play
            loops: Number of times to loop (0 = play once, -1 = loop forever)
            channel: Channel to play on (-1 = first available channel)
            
        Returns:
            int: Channel number the sound is playing on, or -1 on error
        """
        if not self.initialized:
            return -1
        
        if sound_id not in self.sounds or self.sounds[sound_id] is None:
            return -1
        
        if duration > 0:
            channel_num = sdl2.sdlmixer.Mix_PlayChannelTimed(channel, self.sounds[sound_id], loops, ticks=duration)
        else:
            channel_num = sdl2.sdlmixer.Mix_PlayChannel(channel, self.sounds[sound_id], loops)
        return channel_num
    
    def get_sound(self, sound_id):
        """
        Get a loaded sound chunk directly.
        
        Args:
            sound_id: Identifier of the sound
            
        Returns:
            Mix_Chunk pointer or None
        """
        return self.sounds.get(sound_id, None)
    
    def stop_all_sounds(self):
        """Stop all currently playing sound effects."""
        sdl2.sdlmixer.Mix_HaltChannel(-1)
    
    def set_volume(self, sound_id, volume):
        """
        Set the volume for a specific sound.
        
        Args:
            sound_id: Identifier of the sound
            volume: Volume level (0-128)
        """
        if sound_id in self.sounds and self.sounds[sound_id] is not None:
            sdl2.sdlmixer.Mix_VolumeChunk(self.sounds[sound_id], volume)
    
    def set_master_volume(self, volume):
        """
        Set the master volume for all channels.
        
        Args:
            volume: Volume level (0-128)
        """
        sdl2.sdlmixer.Mix_Volume(-1, volume)
    
    def load_music(self, filepath):
        """
        Load background music from file.
        
        Args:
            filepath: Path to the music file
            
        Returns:
            bool: True if music loaded successfully, False otherwise
        """
        if not self.initialized:
            return False
        
        # Check if file exists
        if not os.path.exists(filepath):
            return False
        
        # Free existing music if any
        if self.music:
            sdl2.sdlmixer.Mix_FreeMusic(self.music)
            self.music = None
        
        # Load music
        try:
            music = sdl2.sdlmixer.Mix_LoadMUS(filepath.encode('utf-8'))
            if music:
                self.music = music
                return True
            else:
                return False
        except Exception as e:
            return False
    
    def play_music(self, loops=-1, fade_in_ms=0):
        """
        Play the loaded background music.
        
        Args:
            loops: Number of times to loop (-1 = loop forever, 0 = play once)
            fade_in_ms: Fade in duration in milliseconds (0 = no fade)
            
        Returns:
            bool: True if music started playing, False otherwise
        """
        if not self.initialized or not self.music:
            return False
        
        if fade_in_ms > 0:
            return sdl2.sdlmixer.Mix_FadeInMusic(self.music, loops, fade_in_ms) == 0
        else:
            return sdl2.sdlmixer.Mix_PlayMusic(self.music, loops) == 0
    
    def stop_music(self, fade_out_ms=0):
        """
        Stop the currently playing music.
        
        Args:
            fade_out_ms: Fade out duration in milliseconds (0 = stop immediately)
        """
        if fade_out_ms > 0:
            sdl2.sdlmixer.Mix_FadeOutMusic(fade_out_ms)
        else:
            sdl2.sdlmixer.Mix_HaltMusic()
    
    def is_music_playing(self):
        """
        Check if music is currently playing.
        
        Returns:
            bool: True if music is playing, False otherwise
        """
        return sdl2.sdlmixer.Mix_PlayingMusic() != 0
    
    def set_music_volume(self, volume):
        """
        Set the volume for music.
        
        Args:
            volume: Volume level (0-128)
        """
        sdl2.sdlmixer.Mix_VolumeMusic(volume)
    
    def load_player_sounds(self):
        """
        Load all player sounds (attacks, skills, movement, damage).
        
        Returns:
            bool: True if all sounds loaded successfully
        """
        success = True
        
        # Player normal attack sounds
        success &= self.load_sound("player_auto_barrel", os.path.join("assets", "Sounds", "auto-barrel.ogg"))
        success &= self.load_sound("player_auto_npc", os.path.join("assets", "Sounds", "auto-npc.ogg"))
        success &= self.load_sound("player_auto_miss", os.path.join("assets", "Sounds", "auto.ogg"))
        
        # Skill sounds
        success &= self.load_sound("player_q1", os.path.join("assets", "Sounds", "Q-1.ogg"))
        success &= self.load_sound("player_q2", os.path.join("assets", "Sounds", "Q-2.ogg"))
        success &= self.load_sound("player_w1", os.path.join("assets", "Sounds", "W-1.ogg"))
        success &= self.load_sound("player_w2", os.path.join("assets", "Sounds", "W-2.ogg"))
        success &= self.load_sound("player_e1", os.path.join("assets", "Sounds", "E-1.ogg"))
        success &= self.load_sound("player_e2", os.path.join("assets", "Sounds", "E-2.ogg"))

        # Leaf Ranger skill sounds
        success &= self.load_sound("lr_q1", os.path.join("assets", "Sounds", "leaf_ranger", "Q-1.ogg"))
        success &= self.load_sound("lr_q2", os.path.join("assets", "Sounds", "leaf_ranger", "Q_2.mp3"))
        success &= self.load_sound("lr_w2", os.path.join("assets", "Sounds", "leaf_ranger", "W_2.mp3"))
        success &= self.load_sound("lr_e1", os.path.join("assets", "Sounds", "leaf_ranger", "E_1.ogg"))
        success &= self.load_sound("lr_e2", os.path.join("assets", "Sounds", "leaf_ranger", "E_2.mp3"))
        success &= self.load_sound("lr_on_hit", os.path.join("assets", "Sounds", "leaf_ranger", "on_hit.mp3"))
        success &= self.load_sound("lr_normal_attack", os.path.join("assets", "Sounds", "leaf_ranger", "normal_attack.ogg"))
        
        # Movement sounds
        success &= self.load_sound("player_walk", os.path.join("assets", "Sounds", "player-walk.mp3"))
        success &= self.load_sound("player_run", os.path.join("assets", "Sounds", "run.mp3"))
        
        # Jump sounds
        success &= self.load_sound("player_jump", os.path.join("assets", "Sounds", "jump-1.ogg"))
        success &= self.load_sound("player_land", os.path.join("assets", "Sounds", "jump-2.mp3"))
        
        # Damage sounds
        success &= self.load_sound("player_hit", os.path.join("assets", "Sounds", "hit-1.mp3"))
        success &= self.load_sound("player_hurt", os.path.join("assets", "Sounds", "hit-2.ogg"))

        # Press to activating the statue
        success &= self.load_sound("statue_click", os.path.join("assets", "Sounds", "press_F_activate.mp3"))

        success &= self.load_sound("arrow_shoot", os.path.join("assets", "Sounds", "arrow_hit.mp3"))
        self.set_sound_volume("arrow_shoot", 0.7)

        return success
    
    def load_game_sounds(self):
        """
        Load general game sounds (chest, items, game states).
        
        Returns:
            bool: True if all sounds loaded successfully
        """
        success = True
        
        # Game state sounds
        success &= self.load_sound("game_over", os.path.join("assets", "Sounds", "game-over.mp3"))
        success &= self.load_sound("victory", os.path.join("assets", "Sounds", "victory.mp3"))
        
        # Item sounds
        success &= self.load_sound("item_pickup", os.path.join("assets", "Sounds", "item-pickup.mp3"))
        success &= self.load_sound("item_pop", os.path.join("assets", "Sounds", "item-pop.mp3"))
        
        # Chest sound
        success &= self.load_sound("chest_open", os.path.join("assets", "Sounds", "chest-open.mp3"))
        
        # Activating statue sound
        success &= self.load_sound("statue_process", os.path.join("assets", "Sounds", "activating_statue.mp3"))

        return success
    
    def load_npc_sounds(self):
        """
        Load all NPC attack sounds.
        
        Returns:
            bool: True if all sounds loaded successfully
        """
        success = True
        
        # Ghost attack sound
        success &= self.load_sound("ghost_attack", os.path.join("assets", "NPC", "Ghost", "attack_sound.mp3"))
        
        # Shooter attack sound
        success &= self.load_sound("shooter_attack", os.path.join("assets", "NPC", "Shooter", "attack_sound.mp3"))
        
        # Onre attack sounds (3 variants)
        success &= self.load_sound("onre_attack1", os.path.join("assets", "NPC", "Onre", "attack_sound_1.mp3"))
        success &= self.load_sound("onre_attack2", os.path.join("assets", "NPC", "Onre", "attack_sound_2.mp3"))
        success &= self.load_sound("onre_attack3", os.path.join("assets", "NPC", "Onre", "attack_sound_3.mp3"))
        
        return success
    
    def load_boss_sounds(self):
        """
        Load all boss-related sounds (attacks, skills, hurt states).
        
        Returns:
            bool: True if all sounds loaded successfully
        """
        success = True
        
        # Boss projectile sounds
        success &= self.load_sound("boss_explosion", os.path.join("assets", "Projectile", "Boss", "Explosion", "sound.mp3"))
        success &= self.load_sound("boss_flame", os.path.join("assets", "Projectile", "Boss", "Flame", "sound.mp3"))
        success &= self.load_sound("boss_kamehameha", os.path.join("assets", "Projectile", "Boss", "Kamekameha", "sound.mp3"))
        success &= self.load_sound("boss_melee", os.path.join("assets", "Projectile", "Boss", "Melee", "sound.mp3"))
        success &= self.load_sound("boss_meteor", os.path.join("assets", "Projectile", "Boss", "Meteor", "sound.mp3"))
        
        # Boss skill casting sound (for circular shooting and summon minions)
        success &= self.load_sound("boss_casting", os.path.join("assets", "Boss", "Boss", "Casting Spells", "sound.mp3"))
        
        # Boss hurt sounds
        success &= self.load_sound("boss_on_hit", os.path.join("assets", "Boss", "Boss", "Hurt", "on_hit.mp3"))
        success &= self.load_sound("boss_hurt", os.path.join("assets", "Boss", "Boss", "Hurt", "hurt.mp3"))
        
        return success
    
    def load_background_music(self):
        """
        Load background music tracks.
        Helper to manage which track is loaded.
        
        Returns:
            bool: True if normal background music loaded successfully
        """
        # Load normal background music initially
        return self.load_music(os.path.join("assets", "Sounds", "background-normal.mp3"))
    
    def switch_to_boss_music(self, fade_out_ms=1000, fade_in_ms=1000):
        if self.music:
            sdl2.sdlmixer.Mix_FreeMusic(self.music)
            self.music = None
        
        # Stop current music with fade out
        self.stop_music(fade_out_ms)
        
        # Load boss music
        if self.load_music(os.path.join("assets", "Sounds", "background-boss.mp3")):
            self.play_music(loops=-1, fade_in_ms=fade_in_ms)
    
    def switch_to_normal_music(self, fade_out_ms=1000, fade_in_ms=1000):
        """Switch from boss music back to normal background music."""
        if self.music:
            sdl2.sdlmixer.Mix_FreeMusic(self.music)
            self.music = None
        
        # Stop current music with fade out
        self.stop_music(fade_out_ms)
        
        # Load normal background music
        if self.load_music(os.path.join("assets", "Sounds", "background-normal.mp3")):
            self.play_music(loops=-1, fade_in_ms=fade_in_ms)

    def load_item_sounds(self):
        """
        Load all item-related sounds (pickup, use, drop).
        
        Returns:
            bool: True if all sounds loaded successfully
        """
        success = True
        success &= self.load_sound("HOURGLASS", os.path.join("assets", "Map", "LOL_Equipment", "Zhonyas-sound.mp3"))
        success &= self.load_sound("TEAR", os.path.join("assets", "Map", "LOL_Equipment", "mana-sound.mp3"))
        success &= self.load_sound("HEALTH_POTION", os.path.join("assets", "Map", "LOL_Equipment", "heal-sound.mp3"))
        
        return success
    
    def cleanup(self):
        """Clean up all loaded sounds and close audio."""
        if not self.initialized:
            return
        
        # Free all sound chunks
        for sound_id, sound_chunk in self.sounds.items():
            if sound_chunk:
                sdl2.sdlmixer.Mix_FreeChunk(sound_chunk)
        
        self.sounds.clear()
        
        # Close audio
        sdl2.sdlmixer.Mix_CloseAudio()
        self.initialized = False

    def set_sound_volume(self, name, volume_percent):
        """
        Chỉnh âm lượng cho một âm thanh cụ thể.
        :param name: Tên âm thanh (ví dụ: "arrow_shoot")
        :param volume_percent: Tỷ lệ phần trăm từ 0.0 đến 1.0 (ví dụ: 30% là 0.3)
        """
        import sdl2.sdlmixer
        
        if name in self.sounds:
            # Chuyển đổi tỷ lệ 0.0 -> 1.0 sang thang điểm 0 -> 128 của SDL2
            vol = int(sdl2.sdlmixer.MIX_MAX_VOLUME * volume_percent)
            
            # Gắn âm lượng vào file âm thanh đang lưu trong RAM
            sdl2.sdlmixer.Mix_VolumeChunk(self.sounds[name], vol)
        else:
            print(f"[CẢNH BÁO] Không tìm thấy âm thanh '{name}' để chỉnh âm lượng.")
        
    def set_all_sfx_volume(self, volume_percent=0.2):
        vol = int(sdl2.sdlmixer.MIX_MAX_VOLUME * volume_percent)
        
        for sound in self.sounds.values():
            if sound:
                sdl2.sdlmixer.Mix_VolumeChunk(sound, vol)


# Global sound manager instance (singleton pattern)
_sound_manager = None


def get_sound_manager():
    """
    Get the global SoundManager instance.
    
    Returns:
        SoundManager: The global sound manager instance
    """
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
