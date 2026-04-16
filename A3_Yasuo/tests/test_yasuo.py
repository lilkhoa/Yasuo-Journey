import unittest
from entities.yasuo import Yasuo

class TestYasuo(unittest.TestCase):
    
    def setUp(self):
        self.yasuo = Yasuo(world=None, factory=None, x=100, y=200)

    def test_initial_attributes(self):
        self.assertEqual(self.yasuo.health, 100)
        self.assertEqual(self.yasuo.stamina, 100)
        self.assertEqual(self.yasuo.state, 'idle')

    def test_attack(self):
        initial_health = 100
        damage = 10
        self.yasuo.attack()
        self.assertEqual(self.yasuo.health, initial_health - damage)

    def test_skill_q(self):
        self.yasuo.start_q(direction=1)
        self.assertEqual(self.yasuo.state, 'casting_q')

    def test_skill_w(self):
        self.yasuo.start_w(direction=1)
        self.assertTrue(self.yasuo.w_buff_active)

    def test_skill_e(self):
        self.yasuo.start_e()
        self.assertEqual(self.yasuo.state, 'dashing_e')

if __name__ == '__main__':
    unittest.main()