import sdl2
import sdl2.sdlmixer
import os
import sys
import ctypes

# [CHECK] Import OpenCV
try:
    import cv2
    import numpy as np
except ImportError:
    print("Warning: 'opencv-python' or 'numpy' not found. Mastery Emote video will not play.")
    cv2 = None

from settings import *

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)
PLAYER_ASSET_DIR = os.path.join(root_dir, 'assets', 'Player')

# ==============================================================================
# CLASS XỬ LÝ MASTERY EMOTE (Giữ nguyên từ code cũ)
# ==============================================================================
class MasteryEmote:
    def __init__(self, renderer):
        self.renderer = renderer
        self.active = False
        self.cap = None
        self.sound_chunk = None
        self.frame_texture = None
        
        self.video_path = os.path.join(PLAYER_ASSET_DIR, "videoplayback.mp4")
        self.audio_path = os.path.join(PLAYER_ASSET_DIR, "videoplayback.mp3")
        
        if os.path.exists(self.audio_path):
            try:
                self.sound_chunk = sdl2.sdlmixer.Mix_LoadWAV(self.audio_path.encode('utf-8'))
                if not self.sound_chunk:
                    print(f"[Mastery] Failed to load audio: {self.audio_path}")
                else:
                    print(f"[Mastery] Audio loaded successfully.")
            except Exception as e:
                print(f"[Mastery] Audio load error: {e}")
        else:
            print(f"[Mastery] Audio file missing: {self.audio_path}")
        
        self.target_width = 125
        self.target_height = 125

    def play(self):
        if not cv2: return
        if self.cap: self.cap.release()
        
        if os.path.exists(self.video_path):
            self.cap = cv2.VideoCapture(self.video_path)
            self.active = True
            
            if self.sound_chunk:
                sdl2.sdlmixer.Mix_PlayChannel(-1, self.sound_chunk, 0)
        else:
            print(f"[Mastery] Missing video: {self.video_path}")

    def update(self):
        if not self.active or not self.cap: return

        ret, frame = self.cap.read()
        if not ret:
            self.stop()
            return

        frame = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_NEAREST)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        lower_green = np.array([0, 150, 0])
        upper_green = np.array([40, 255, 40]) 
        mask = cv2.inRange(rgb_frame, lower_green, upper_green)

        frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        frame_rgba[mask > 0] = [0, 0, 0, 0]

        frame_rgba = np.rot90(frame_rgba, k=-1) 
        frame_rgba = np.flip(frame_rgba, axis=1)

        h, w, c = frame_rgba.shape 
        
        surface = sdl2.SDL_CreateRGBSurfaceFrom(
            frame_rgba.ctypes.data_as(ctypes.c_void_p),
            w, h, 32, 4 * w,
            0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000
        )
        
        if self.frame_texture:
            sdl2.SDL_DestroyTexture(self.frame_texture)
        self.frame_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        sdl2.SDL_FreeSurface(surface)

    def render(self, x, y, camera_x, camera_y):
        if not self.active or not self.frame_texture: return

        offset_x = 64 - (self.target_width // 2)
        dst_rect = sdl2.SDL_Rect(
            int(x - camera_x + offset_x-30), 
            int(y - camera_y - self.target_height + 70),
            self.target_width+60,
            self.target_height
        )
        sdl2.SDL_SetTextureBlendMode(self.frame_texture, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_RenderCopy(self.renderer, self.frame_texture, None, dst_rect)

    def stop(self):
        self.active = False
        if self.cap: self.cap.release(); self.cap = None
        if self.frame_texture: sdl2.SDL_DestroyTexture(self.frame_texture); self.frame_texture = None

    def cleanup(self):
        self.stop()
        if self.sound_chunk: sdl2.sdlmixer.Mix_FreeChunk(self.sound_chunk)