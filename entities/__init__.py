"""
Entities module - Contains all game entity classes.
"""

from .player import Player
from .boss import Boss, BossManager
from .npc import Ghost, Shooter, Onre, NPCManager
from .projectile import ProjectileManager

__all__ = [
    'Player',
    'Boss',
    'BossManager',
    'Ghost',
    'Shooter',
    'Onre',
    'NPCManager',
    'ProjectileManager',
]
