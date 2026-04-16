import time

class BaseSkill:
    """
    Lớp cơ sở (Base Class) cho MỌI kỹ năng trong game.
    Áp dụng Strategy/Command Pattern để dễ dàng tái sử dụng và gán phím.
    """
    def __init__(self, owner, name="Unknown Skill", base_cooldown=0.0, stamina_cost=0):
        self.owner = owner
        self.name = name
        self.level = 0
        
        self.base_cooldown = base_cooldown
        self.current_cooldown = base_cooldown
        self.stamina_cost = stamina_cost
        
        self.last_cast_time = 0
        self.active = False
        self.damage_multiplier = 1.0
        
        # Khởi tạo chỉ số sức mạnh ở Level 0
        self.update_stats(0)

    def update_stats(self, level):
        """Cập nhật sức mạnh và thời gian hồi chiêu dựa trên Level và AD của chủ sở hữu"""
        from settings import SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN, SKILL_DAMAGE_GROWTH, SKILL_AD_RATIO
        
        self.level = level
        
        # 1. Tính toán hệ số sát thương (Damage Multiplier)
        level_scaling = SKILL_DAMAGE_GROWTH ** level
        
        if hasattr(self.owner, 'attack_damage') and hasattr(self.owner, 'base_attack_damage') and self.owner.base_attack_damage > 0:
            ad_scaling = (self.owner.attack_damage / self.owner.base_attack_damage) * SKILL_AD_RATIO
        else:
            ad_scaling = 1.0
            
        self.damage_multiplier = level_scaling * ad_scaling
        
        # 2. Tính toán giảm thời gian hồi chiêu (Iterative reduction)
        current_cd = self.base_cooldown
        for _ in range(level):
            reduction = max(current_cd * SKILL_CD_REDUCE_RATE, SKILL_CD_REDUCE_FLAT_MIN)
            current_cd -= reduction
            
        self.current_cooldown = max(0.1, current_cd) # Luôn giữ tối thiểu 0.1s để tránh bug game loop
        
        print(f"[SKILL] '{self.name}' upgraded to Lv.{level}. DmgMul: {self.damage_multiplier:.2f}, CD: {self.current_cooldown:.2f}s")

    def is_ready(self):
        """Kiểm tra xem chiêu thức đã hồi xong chưa (Tính theo thời gian thực)"""
        return (time.time() - self.last_cast_time) >= self.current_cooldown

    def cast(self, world_entities=None, factory=None, renderer=None, *args, **kwargs):
        """
        Hàm gọi công khai (Public Interface) khi ấn phím. 
        Class bên ngoài chỉ nên gọi hàm này.
        """
        self.last_cast_time = time.time()
        self.active = True
        return self.execute(world_entities, factory, renderer, *args, **kwargs)

    def execute(self, world_entities, factory, renderer, *args, **kwargs):
        """
        Hàm thực thi logic cốt lõi của chiêu.
        CÁC CLASS CON (Tornado, ArrowRain...) BẮT BUỘC PHẢI OVERRIDE HÀM NÀY.
        """
        raise NotImplementedError(f"Skill '{self.name}' chưa được implement hàm execute()!")

    def update(self, dt):
        """Dùng cho các chiêu thức có vòng đời kéo dài (như Buff Độc của LeafRanger)"""
        pass