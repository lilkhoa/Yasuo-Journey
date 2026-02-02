import sdl2

class CooldownManager:
    """
    Quản lý thời gian hồi chiêu (Cooldown) cho các kỹ năng.
    """
    def __init__(self):
        self.cooldowns = {} # Dictionary lưu: { "skill_name": time_remaining }

    def start_cooldown(self, skill_name, duration_frames):
        """Bắt đầu tính hồi chiêu cho kỹ năng"""
        self.cooldowns[skill_name] = duration_frames

    def is_ready(self, skill_name):
        """Kiểm tra xem kỹ năng đã sẵn sàng chưa"""
        return self.cooldowns.get(skill_name, 0) <= 0

    def update(self, dt=1.0):
        """
        Cập nhật giảm thời gian hồi chiêu.
        dt: delta time (hoặc frame count nếu dùng frame-based)
        Ở đây ta giả sử update theo frame, nên truyền vào 1.
        """
        for skill in list(self.cooldowns.keys()):
            if self.cooldowns[skill] > 0:
                self.cooldowns[skill] -= dt
                if self.cooldowns[skill] < 0:
                    self.cooldowns[skill] = 0
