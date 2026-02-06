import os
import sdl2
import sdl2.ext

os.environ["SDL_VIDEODRIVER"] = "dummy"

sdl2.ext.init()

assets_dir = r"d:\CS-HCMUT\Game_Dev\A3_Yasuo\assets\Player"
files = ["Dead.png", "Hurt.png", "Idle.png"]

for f in files:
    path = os.path.join(assets_dir, f)
    if os.path.exists(path):
        image = sdl2.ext.load_image(path)
        print(f"{f}: {image.w}x{image.h}")
        sdl2.SDL_FreeSurface(image)
    else:
        print(f"{f} not found")

sdl2.ext.quit()
