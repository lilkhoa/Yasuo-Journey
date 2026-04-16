import unittest
from entities.base_char import BaseChar
from entities.yasuo import Yasuo
from entities.leaf_ranger import LeafRanger

class TestBaseChar(unittest.TestCase):

    def setUp(self):
        self.character = BaseChar(100, 50)  # Example health and stamina

    def test_initial_health(self):
        self.assertEqual(self.character.health, 100)

    def test_initial_stamina(self):
        self.assertEqual(self.character.stamina, 50)

    def test_take_damage(self):
        self.character.take_damage(20)
        self.assertEqual(self.character.health, 80)

    def test_attack(self):
        target = BaseChar(100, 50)
        self.character.attack(target, 10)
        self.assertEqual(target.health, 90)

    def test_is_alive(self):
        self.character.take_damage(100)
        self.assertFalse(self.character.is_alive())

    def test_yasuo_inheritance(self):
        yasuo = Yasuo(100, 50)
        self.assertIsInstance(yasuo, BaseChar)

    def test_leaf_ranger_inheritance(self):
        leaf_ranger = LeafRanger(100, 50)
        self.assertIsInstance(leaf_ranger, BaseChar)

if __name__ == '__main__':
    unittest.main()