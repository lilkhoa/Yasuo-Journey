"""
Game Settings and Configuration
Centralized configuration for the A3 Yasuo game project.
"""

# Display settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60
FULLSCREEN = False
SCALE_FACTOR = 4
TILE_SIZE_RAW = 24
TILE_SIZE = TILE_SIZE_RAW * SCALE_FACTOR
SOLID_TILES = ['(', '-', ')', '[', '=', ']', '0', '1', '2', '3', '4', '5', '6', '7', '8']

# Game settings
GAME_TITLE = "Yasuo's Journey"

# Asset paths
ASSETS_PATH = "assets"
NPC_PATH = "assets/NPC"
PLAYER_PATH = "assets/Player"
MAP_PATH = "assets/Map"
SKILLS_PATH = "assets/Skills"

# Debug settings
DEBUG_COLLISION_BOXES = False  # Set to True to see collision boxes and hitboxes

# Sound settings
MUSIC_VOLUME = 50
SFX_VOLUME = 50

# NPC Settings
NPC_GHOST_HEALTH = 50
NPC_GHOST_DAMAGE = 25
NPC_GHOST_ATTACK_RANGE = 100
NPC_GHOST_SPEED = 2
NPC_GHOST_DETECTION_RANGE = 260
NPC_GHOST_PATROL_RADIUS = 160
NPC_GHOST_ATTACK_COOLDOWN = 60
NPC_GHOST_PROJECTILE_SPEED = 8

NPC_SHOOTER_HEALTH = 75
NPC_SHOOTER_DAMAGE = 25
NPC_SHOOTER_ATTACK_RANGE = 200
NPC_SHOOTER_SPEED = 1.5
NPC_SHOOTER_DETECTION_RANGE = 400
NPC_SHOOTER_PATROL_RADIUS = 150
NPC_SHOOTER_ATTACK_COOLDOWN = 40
NPC_SHOOTER_PROJECTILE_SPEED = 12

NPC_ONRE_HEALTH = 100
NPC_ONRE_DAMAGE = 50
NPC_ONRE_ATTACK_RANGE = 50
NPC_ONRE_SPEED = 2.5
NPC_ONRE_DETECTION_RANGE = 200
NPC_ONRE_PATROL_RADIUS = 140
NPC_ONRE_ATTACK_COOLDOWN = 40

# Boss Settings
BOSS_HEALTH = 30000
BOSS_SPEED = 10

BOSS_MELEE_DAMAGE = 75
BOSS_MELEE_RANGE = 200
BOSS_MELEE_COOLDOWN = 45
BOSS_MELEE_HIT_FRAME = 2

BOSS_RANGED_DAMAGE = 50
BOSS_PROJECTILE_SPEED = 15
BOSS_RANGED_COOLDOWN = 60

BOSS_LASER_DAMAGE = 40
BOSS_LASER_WIDTH = 1500
BOSS_LASER_HEIGHT = 100
BOSS_METEOR_DAMAGE = 80
BOSS_SKILL_COOLDOWN = 600 

# Boss Circular Shooting Skill Settings
CIRCULAR_CHARGE_DURATION = 60
CIRCULAR_SHOOT_DURATION = 180
CIRCULAR_PROJECTILES_PER_STREAM = 12
CIRCULAR_VELOCITY_MULTIPLIER = 0.6

# Boss Meteor Skill Settings
METEOR_CHARGE_DURATION = 60
METEOR_DURATION = 180
METEOR_SPAWN_INTERVAL = 15
METEOR_SIZE_WIDTH = 128
METEOR_SIZE_HEIGHT = 72
METEOR_EXPLOSION_SIZE = 128
METEOR_VELOCITY_X_MIN = -6 
METEOR_VELOCITY_X_MAX = -2
METEOR_VELOCITY_Y_MIN = 8
METEOR_VELOCITY_Y_MAX = 12
METEOR_GROUND_Y = 600

# Boss Summon Minions Skill Settings
SUMMON_CHARGE_DURATION = 60
SUMMON_WAIT_DURATION = 30

# Boss Minion Settings
BOSS_MINION_SIZE = 96
BOSS_MINION_HEALTH_BASE = 100
BOSS_MINION_SPEED = 3
BOSS_MINION_DETECTION_RANGE = 1000
BOSS_MINION_ATTACK_RANGE = 150
BOSS_MINION_ATTACK_COOLDOWN = 90
BOSS_MINION_DAMAGE = 25
BOSS_MINION_FIREBALL_SPEED = 10
BOSS_MINION_FIREBALL_SIZE = 32

# Player Settings
PLAYER_MAX_HEALTH = 75000
PLAYER_MAX_STAMINA = 150
PLAYER_SPEED_WALK = 200
PLAYER_SPEED_RUN = 300
PLAYER_JUMP_POWER = 12
PLAYER_MAX_JUMPS = 1

# Combat Settings
ATTACK_COOLDOWN = 60
SKILL_Q_COOLDOWN = 240
SKILL_W_COOLDOWN = 300
SKILL_E_COOLDOWN = 100

# Player 2 E Skill (Arrow Rain) Settings
SKILL_E_2_COOLDOWN = 12.0            # E skill cooldown (seconds)
SKILL_E_2_COST = 4                  # E skill stamina cost
SKILL_E_2_WIDTH = 350                # Arrow rain area width (pixels)
SKILL_E_2_HEIGHT = 600               # Arrow rain area height (pixels)
SKILL_E_2_ROOT_ZONE_HEIGHT = 100     # Bottom portion where roots appear (ground impact zone)
SKILL_E_2_DURATION = 2.5             # Arrow rain duration (seconds)
SKILL_E_2_SNARE_DURATION = 1.5       # Root duration for enemies hit (seconds)
SKILL_E_2_CAST_RANGE = 200           # Distance from player to spawn AoE center

# Damage Settings [MỚI]
PLAYER_ATTACK_DAMAGE = 25
DAMAGE_SKILL_E = 25
DAMAGE_SKILL_Q = 50
DAMAGE_SKILL_W = 25

# Player 2 (New Character) Damage Settings
DAMAGE_SKILL_Q_2 = 45  # Laser beam damage (slightly lower than tornado)
DAMAGE_SKILL_E_2 = 35  # Arrow Rain damage per enemy hit

# ── Leaf Ranger (Player 2) Character Stats ──────────────────────────────────
# All values are intentionally separated from Yasuo's stats so each character
# can be balanced independently.  Yasuo values (PLAYER_*, SKILL_*) are untouched.

LR_MAX_HEALTH         = 65000   # Less HP than Yasuo (75000) – ranged / squishier
LR_MAX_STAMINA        = 200     # More stamina than Yasuo (150) – spends it on arrows

LR_BASE_ATTACK_DAMAGE = 22      # Lower auto-attack AD than Yasuo (25) – ranged bonus in skills
LR_BASE_ARMOR         = 20      # Less armour than Yasuo (30) – lighter build
LR_BASE_LIFESTEAL     = 0.08    # Slightly higher lifesteal (vs 0.05) to compensate lower armour
LR_SPEED_WALK         = 220     # Slightly faster than Yasuo (200)
LR_ATTACK_RANGE       = 350     # Long-range bow attacks (vs Yasuo's 150)

# Leaf Ranger cooldowns – stored in **frames** (CooldownManager uses update(1) per tick)
LR_SKILL_Q_COOLDOWN  = 180   #  3.0 s at 60 FPS  (Yasuo Q = 240 frames / 4.0 s)
LR_SKILL_W_COOLDOWN  = 90   #  6.0 s at 60 FPS  (Yasuo W = 300 frames / 5.0 s)
LR_SKILL_E_COOLDOWN  = 210   # 12.0 s at 60 FPS  (Yasuo E = 100 frames / ~1.7 s)
LR_ATTACK_COOLDOWN   = 50    # ~0.83 s at 60 FPS (Yasuo A =  60 frames / 1.0 s)

# Leaf Ranger skill stamina costs
LR_SKILL_Q_COST = 80   # Laser beam
LR_SKILL_W_COST = 25   # Toxin Enhancement buff (Yasuo W costs 30)
LR_SKILL_E_COST = 40    # Arrow Rain (mirrors SKILL_E_2_COST)

# Player 2 W Skill Settings
SKILL_W_BUFF_DURATION = 5.0        # Duration of W buff in seconds
DAMAGE_W_POISON = 3               # Poison projectile base damage
POISON_TICK_RATE = 0.5             # Damage application frequency (seconds)
POISON_DURATION = 3.0              # Duration of poison effect on target
DAMAGE_W_PLANT = 2                # Plant/root projectile damage
W_PLANT_SNARE_DURATION = 1.5       # Root duration in seconds
HEAL_W_DUST = 50                   # Healing amount from dust projectile
W_PROJECTILE_SPEED = 8             # Base projectile speed (pixels per frame)

# Block Settings [MỚI]
BLOCK_DAMAGE_REDUCTION = 0.9
BLOCK_STAMINA_COST_PER_HIT = 20

PLAYER_STAMINA_REGEN_WALK = 0.05
PLAYER_HEALTH_REGEN = 0.02

PLAYER_RUN_COST = 0.2
SKILL_Q_COST = 20
SKILL_W_COST = 30
SKILL_E_COST = 15

# Skill Upgrade System
SKILL_MAX_LEVEL = 3
SKILL_UPGRADE_COSTS = {1: 1, 2: 2, 3: 3} # Cost to reach Level: Coin Amount
SKILL_DAMAGE_GROWTH = 1.2        # +20% damage per level
SKILL_AD_RATIO = 1.0             # Skill damage scales 100% with player AD
SKILL_CD_REDUCE_RATE = 0.25      # Giảm 25% cooldown hiện tại
SKILL_CD_REDUCE_FLAT_MIN = 0.2   # Giảm tối thiểu 0.2s
PLAYER_HURT_DURATION = 0.5 # Thời gian hiệu ứng Hurt
PLAYER_HITS_TO_STAGGER = 10 # Số lần bị đánh để kích hoạt Hurt stun

# Mechanisms
PLAYER_LIFESTEAL = 100          # Hút máu toàn phần (100%)

# Cơ chế thưởng (Reward)
Reward_Hit_Stamina = 5
Reward_Kill_Stamina = 30

# Physics
GRAVITY = 0.5
MAX_FALL_SPEED = 10
GROUND_Y = 480 # Mức đất tạm thời để test di chuyển (Row 5-6 * 96)

# Colors (R, G, B, A)
COLOR_BLACK = (0, 0, 0, 255)
COLOR_WHITE = (255, 255, 255, 255)
COLOR_RED = (255, 0, 0, 255)
COLOR_GREEN = (0, 255, 0, 255)
COLOR_BLUE = (0, 0, 255, 255)
COLOR_BACKGROUND = (20, 20, 30, 255)

# BOX SETTINGS
BOX_WIDTH = 44
BOX_HEIGHT = 44

# OPEN_COLLECTING_INTERVAL
COLLECT_INTERVAL = 0.05

# ── Multiplayer Network Settings ────────────────────────────────────────────
NETWORK_HOST        = "0.0.0.0"   # Server bind address
NETWORK_PORT        = 5555        # TCP port
NETWORK_TICK_RATE   = 20          # World-state broadcast rate (packets/sec)
NETWORK_INTERP_DELAY = 0.10       # Interpolation buffer depth (seconds)
NETWORK_RECV_BUFFER = 4096        # Socket receive buffer hint