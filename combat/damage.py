
class DamageSystem:
    """
    Hệ thống tính toán sát thương và hồi máu.
    """
    @staticmethod
    def calculate_damage(attacker, defender, base_damage):
        """
        Tính sát thương gây ra.
        Có thể mở rộng thêm giáp, kháng phép sau này.
        """
        final_damage = base_damage
        # Ví dụ: final_damage = base_damage * (100 / (100 + defender.armor))
        return int(final_damage)

    @staticmethod
    def apply_lifesteal(damage_dealt, lifesteal_percent):
        """
        Tính lượng máu hồi phục dựa trên sát thương gây ra (Hút máu).
        """
        return int(damage_dealt * (lifesteal_percent / 100.0))
