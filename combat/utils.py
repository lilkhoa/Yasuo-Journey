import sdl2
import sdl2.ext
import ctypes
import os

def get_surface_struct_and_ptr(surface):
    if hasattr(surface, "contents"):
        return surface.contents, surface
    else:
        return surface, ctypes.byref(surface)

def get_cropped_surface(source_surface, x, y, w, h):
    src, src_ptr = get_surface_struct_and_ptr(source_surface)
    fmt = src.format.contents
    dst_surface_ptr = sdl2.SDL_CreateRGBSurface(0, w, h, 
                                            fmt.BitsPerPixel, 
                                            fmt.Rmask, fmt.Gmask, fmt.Bmask, fmt.Amask)
    src_rect = sdl2.SDL_Rect(x, y, w, h)
    dst_rect = sdl2.SDL_Rect(0, 0, w, h)
    sdl2.SDL_BlitSurface(src_ptr, src_rect, dst_surface_ptr, dst_rect)
    return dst_surface_ptr

def scale_surface(src_surface, target_width, target_height):
    src, src_ptr = get_surface_struct_and_ptr(src_surface)
    fmt = src.format.contents
    dst_surface_ptr = sdl2.SDL_CreateRGBSurface(0, target_width, target_height,
                                            fmt.BitsPerPixel,
                                            fmt.Rmask, fmt.Gmask, fmt.Bmask, fmt.Amask)
    src_rect = sdl2.SDL_Rect(0, 0, src.w, src.h)
    dst_rect = sdl2.SDL_Rect(0, 0, target_width, target_height)
    sdl2.SDL_UpperBlitScaled(src_ptr, src_rect, dst_surface_ptr, dst_rect)
    return dst_surface_ptr

def load_grid_sprite_sheet(factory, filepath, cols, rows, target_size=None):
    if not os.path.exists(filepath):
        print(f"LỖI: Không tìm thấy file {filepath}")
        return []

    full_surface = sdl2.ext.load_image(filepath)
    full_src, _ = get_surface_struct_and_ptr(full_surface)
    
    frame_w = full_src.w // cols
    frame_h = full_src.h // rows
    
    sprites = []
    print(f"Đang xử lý tài nguyên: {os.path.basename(filepath)}...")

    for row in range(rows):
        for col in range(cols):
            x = col * frame_w
            y = row * frame_h
            cropped_ptr = get_cropped_surface(full_surface, x, y, frame_w, frame_h)
            final_ptr = cropped_ptr
            
            if target_size:
                tw, th = target_size
                scaled_ptr = scale_surface(cropped_ptr, tw, th)
                sdl2.SDL_FreeSurface(cropped_ptr)
                final_ptr = scaled_ptr

            if hasattr(final_ptr, "contents"):
                sprite = factory.from_surface(final_ptr.contents)
            else:
                sprite = factory.from_surface(final_ptr)
            sprites.append(sprite)
            
    return sprites

def load_first_frame_cropped(factory, filepath, num_frames):
    if not os.path.exists(filepath):
        return None
    full_surface = sdl2.ext.load_image(filepath)
    src, _ = get_surface_struct_and_ptr(full_surface)
    frame_w = src.w // num_frames
    frame_h = src.h
    cropped_ptr = get_cropped_surface(full_surface, 0, 0, frame_w, frame_h)
    return cropped_ptr

def load_image_sequence(factory, folder_path, prefix, count, target_size=None, zero_pad=True):
    """
    Load chuỗi ảnh.
    - zero_pad=True: CS001.png, CS002.png...
    - zero_pad=False: fire_column_medium_1.png, fire_column_medium_2.png...
    """
    if not os.path.exists(folder_path):
        print(f"LỖI: Không tìm thấy thư mục {folder_path}")
        return []

    sprites = []
    print(f"Đang load chuỗi ảnh từ: {os.path.basename(folder_path)}...")

    for i in range(1, count + 1):
        if zero_pad:
            filename = f"{prefix}{i:03d}.png"
        else:
            filename = f"{prefix}{i}.png"   
            
        filepath = os.path.join(folder_path, filename)
        
        if not os.path.exists(filepath):
            print(f"Cảnh báo: Không tìm thấy {filename} tại {filepath}")
            continue

        surface = sdl2.ext.load_image(filepath)
        final_ptr = surface

        if target_size:
            tw, th = target_size
            scaled_ptr = scale_surface(surface, tw, th)
            final_ptr = scaled_ptr

        src, ptr = get_surface_struct_and_ptr(final_ptr)
        if hasattr(ptr, "contents"):
            sprite = factory.from_surface(ptr.contents)
        else:
            sprite = factory.from_surface(ptr)
            
        sprites.append(sprite)
    
    print(f"Đã load {len(sprites)} frame cho Skill.")
    return sprites

def flip_sprites_horizontal(factory, original_sprites):
    flipped_sprites = []
    
    for sprite in original_sprites:
        dup_surface_ptr = sdl2.SDL_DuplicateSurface(sprite.surface)
        
        if not dup_surface_ptr:
            continue
        new_sprite = factory.from_surface(dup_surface_ptr, free=True)

        dup_surface = dup_surface_ptr.contents
        
        dst_px = sdl2.ext.pixels3d(dup_surface)

        dst_px[:] = dst_px[::-1, ...]
        
        flipped_sprites.append(new_sprite)
        
    return flipped_sprites