# filepath: /A3_Yasuo/A3_Yasuo/combat/utils.py

def load_image_sequence(factory, folder, prefix, count, size=None, zero_pad=False):
    """
    Load a sequence of images as sprites from a specified folder.

    Args:
        factory: Sprite factory for creating sprites.
        folder: Folder containing the images.
        prefix: Prefix for the image filenames.
        count: Number of images to load.
        size: Optional size to scale the images.
        zero_pad: Whether to zero-pad the filenames.

    Returns:
        List of loaded sprites.
    """
    sprites = []
    for i in range(1, count + 1):
        filename = f"{prefix}{str(i).zfill(2) if zero_pad else i}.png"
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            sprite = factory.from_surface(sdl2.ext.load_image(filepath))
            if size:
                sprite.size = size
            sprites.append(sprite)
        else:
            print(f"[WARNING] Missing image: {filepath}")
    return sprites

def flip_sprites_horizontal(factory, sprites):
    """
    Flip a list of sprites horizontally.

    Args:
        factory: Sprite factory for creating flipped sprites.
        sprites: List of sprites to flip.

    Returns:
        List of flipped sprites.
    """
    flipped_sprites = []
    for sprite in sprites:
        flipped_sprite = factory.from_surface(sprite.surface)
        flipped_sprite.flip_horizontal()
        flipped_sprites.append(flipped_sprite)
    return flipped_sprites

def load_animation_frames(factory, folder, prefix, count):
    """
    Load animation frames from a specified folder.

    Args:
        factory: Sprite factory for creating sprites.
        folder: Folder containing the animation frames.
        prefix: Prefix for the image filenames.
        count: Number of frames to load.

    Returns:
        List of loaded animation frames.
    """
    return load_image_sequence(factory, folder, prefix, count)