class CooldownManager:
    """
    Quản lý thời gian hồi chiêu (Cooldown) cho các phím kỹ năng.
    Tách biệt với internal cooldown của từng Object Skill.
    """
    def __init__(self):
        self.cooldowns: dict[str, float] = {} 

    def start_cooldown(self, skill_name: str, duration: float):
        """Bắt đầu tính hồi chiêu cho kỹ năng"""
        self.cooldowns[skill_name] = float(duration)

    def is_ready(self, skill_name: str) -> bool:
        """Kiểm tra xem kỹ năng đã sẵn sàng để bấm chưa"""
        return self.cooldowns.get(skill_name, 0.0) <= 0.0

    def update(self, dt: float = 1.0):
        """
        Cập nhật đếm ngược thời gian hồi chiêu.
        - Nếu tính bằng Frame: dt = 1
        - Nếu tính bằng Giây: dt = delta_time
        """
        for skill in list(self.cooldowns.keys()):
            if self.cooldowns[skill] > 0:
                self.cooldowns[skill] -= dt
                if self.cooldowns[skill] < 0:
                    self.cooldowns[skill] = 0.0
    
    def reset(self):
        """Xóa toàn bộ hồi chiêu (dùng khi nhân vật hồi sinh)"""
        self.cooldowns.clear()