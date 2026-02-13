import sdl2

class ItemNotification:
    def __init__(self, item_name, texture, start_time, text_renderer):
        self.name = item_name
        self.texture = texture
        self.start_time = start_time
        self.duration = 3000 #  3 second
        self.alpha = 255
        self.y_offset = 0   # using for sliding animation

        # Tạo texture chữ 1 lần để tối ưu hiệu năng
        self.name_texture, self.name_w, self.name_h = text_renderer.create_text_texture(item_name, (255, 255, 255))

    def cleanup(self):
        if self.name_texture:
            sdl2.SDL_DestroyTexture(self.name_texture)

class ItemNotificationSystem:
    def __init__(self, text_renderer):
        self.text_renderer = text_renderer
        self.notifications = []     # list of all ItemNotification
        self.start_x = 20
        self.start_y = 100          # starting at the left

    def add_notification(self, item_name, texture):
        current_time = sdl2.SDL_GetTicks()
        notif = ItemNotification(item_name, texture, current_time, self.text_renderer)
        # adding into list
        self.notifications.append(notif)

    def update(self):
        current_time = sdl2.SDL_GetTicks()
        # remove outdated notif
        self.notifications = [n for n in self.notifications if current_time - n.start_time < n.duration]

        # Calculate alpha (faded out)
        for n in self.notifications:
            elapsed = current_time - n.start_time
            if elapsed < n.duration:
                if elapsed > 2000:  # faded out at last 1 sec
                    n.alpha = int(255 * (1 - (elapsed - 2000)/1000))
                else:
                    n.alpha = 255
            else:
                n.cleanup()

    def render(self, renderer):
        for i, notif in enumerate(self.notifications):
            y_pos = self.start_y + (i * 10) # Stack mỗi dòng cách nhau 10px
            
            # Set Alpha cho cả icon và text
            sdl2.SDL_SetTextureAlphaMod(notif.texture, notif.alpha)
            if notif.name_texture:
                sdl2.SDL_SetTextureAlphaMod(notif.name_texture, notif.alpha)
            
            # 1. Vẽ Icon (32x32)
            icon_rect = sdl2.SDL_Rect(self.start_x, y_pos, 32, 32)
            sdl2.SDL_RenderCopy(renderer, notif.texture, None, icon_rect)
            
            # 2. Vẽ Tên Item (Bên phải icon)
            if notif.name_texture:
                text_rect = sdl2.SDL_Rect(self.start_x + 40, y_pos + 8, notif.name_w, notif.name_h) # +8 để căn giữa dọc với icon
                sdl2.SDL_RenderCopy(renderer, notif.name_texture, None, text_rect)
            
            # Reset Alpha
            sdl2.SDL_SetTextureAlphaMod(notif.texture, 255)
            if notif.name_texture:
                sdl2.SDL_SetTextureAlphaMod(notif.name_texture, 255)