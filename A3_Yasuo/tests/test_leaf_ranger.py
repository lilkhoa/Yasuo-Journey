import unittest
from entities.leaf_ranger import LeafRanger
from combat.player_2.skill_q import SkillQLaser
from combat.player_2.skill_w import SkillW
from combat.player_2.skill_e import SkillE

class TestLeafRanger(unittest.TestCase):
    
    def setUp(self):
        self.leaf_ranger = LeafRanger(world=None, factory=None, x=100, y=200)

    def test_initial_attributes(self):
        self.assertEqual(self.leaf_ranger.health, 100)
        self.assertEqual(self.leaf_ranger.stamina, 100)
        self.assertEqual(self.leaf_ranger.state, 'idle')

    def test_skill_q(self):
        self.leaf_ranger.start_q(direction=1)
        self.assertIsInstance(self.leaf_ranger.skill_q, SkillQLaser)
        self.assertEqual(self.leaf_ranger.state, 'casting_q')

    def test_skill_w(self):
        self.leaf_ranger.start_w(direction=1)
        self.assertIsInstance(self.leaf_ranger.skill_w, SkillW)
        self.assertTrue(self.leaf_ranger.w_buff_active)

    def test_skill_e(self):
        self.leaf_ranger.start_e()
        self.assertIsInstance(self.leaf_ranger.skill_e, SkillE)
        self.assertEqual(self.leaf_ranger.state, 'dashing_e')

    def test_attack(self):
        self.leaf_ranger.attack()
        self.assertEqual(self.leaf_ranger.state, 'attacking')

    def test_die(self):
        self.leaf_ranger.die()
        self.assertEqual(self.leaf_ranger.health, 0)
        self.assertEqual(self.leaf_ranger.state, 'dead')

if __name__ == '__main__':
    unittest.main()