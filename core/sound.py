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
    
    def play_sound(self, sound_id, loops=0, channel=-1):
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
