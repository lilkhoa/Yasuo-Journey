# Yasuo's Journey

A 2D action platformer game featuring Yasuo from League of Legends. Built with Python and PySDL2, this game combines classic platforming mechanics with dynamic combat systems and RPG elements inspired by the League of Legends universe.

![Game Demo](demo.gif)

## Overview

Yasuo's Journey is a side-scrolling action platformer where players control Yasuo through challenging levels filled with enemies, environmental puzzles, and epic boss battles. The game features a sophisticated skill system with AD scaling mechanics, checkpoint-based progression, and interactive environmental elements.

## Key Features

### Combat System
- **Dynamic Skill Scaling**: All skills scale with both level upgrades and attack damage (AD) from equipment
- **Three Unique Skills**:
  - **Q (Steel Tempest)**: Fire a tornado projectile dealing 50 base damage with AD scaling
  - **W (Wind Wall)**: Create a barrier that blocks enemy projectiles for strategic defense
  - **E (Sweeping Blade)**: Dash through enemies dealing 25 base damage with AD scaling
- **Normal Attacks**: Basic melee attacks with 25 base damage, upgradeable through skill progression
- **Lifesteal Mechanic**: Heal with every successful hit (100% lifesteal)
- **Stamina System**: Manage stamina for running and skills, regenerate through combat rewards

### Progression System
- **Skill Upgrades**: Level up skills (max level 3) using coins collected from enemies
  - Each level increases damage by 20% multiplicatively
  - Cooldown reduction per level (25% of current cooldown or 0.2s minimum)
  - Damage scales dynamically with equipped items
- **Equipment System**: Collect powerful items like Bloodthirster (+10 AD) and Infinity Edge (+50 AD)
- **Gold Economy**: Earn gold from defeating enemies to upgrade skills and purchase items
- **Stat Growth**: Upgrade Yasuo's base attack damage through the "A" skill tree

### World & Enemies
- **Interactive Environment**: 
  - Push boxes and barrels to solve puzzles
  - Break destructible barrels for loot
  - Open treasure chests for rewards
  - Activate checkpoints to save progress
- **Diverse Enemy Types**:
  - **Ghost**: Ranged enemy with projectile attacks (50 HP, 25 damage)
  - **Shooter**: Long-range sniper enemy (75 HP, 25 damage, 400 detection range)
  - **Onre**: Melee bruiser with high damage (100 HP, 50 damage)
- **Epic Boss Battles**: Fight powerful bosses with multiple attack patterns:
  - Melee combos (75 damage)
  - Ranged projectiles (50 damage)  
  - Circular shooting patterns
  - Meteor showers (80 damage per meteor)
  - Kamehameha-style beam attacks (40 damage)
  - Minion summoning abilities

### Game Features
- **Checkpoint System**: Respawn at the last activated checkpoint with a 30% gold penalty
- **Physics-Based Movement**: Smooth platforming with gravity, jumping (max 1 double jump), and momentum
- **Block Mechanic**: Shield against attacks with 90% damage reduction at the cost of stamina
- **Sound Design**: Dynamic background music and sound effects for immersive gameplay
- **Polished UI**: Health bars, stamina meters, skill cooldown indicators, and item notifications

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lilkhoa/A3_Yasuo.git
   cd A3_Yasuo
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   Required packages:
   - `pysdl2`: SDL2 bindings for Python
   - `numpy`: Numerical computing library
   - `opencv-python`: Image processing utilities

3. **Install SDL2 library**:
   - **Windows**: Download SDL2.dll from [libsdl.org](https://www.libsdl.org/) and place it in the project directory
   - **Linux**: `sudo apt-get install libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0`
   - **macOS**: `brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf`

4. **Run the game**:
   ```bash
   python main.py
   ```

## Controls

### Movement
- **Arrow Left/Right**: Move Yasuo left or right
- **Arrow Up/Space**: Jump (can double jump once in the air)
- **Shift + Arrow Keys**: Run (consumes stamina)

### Combat
- **Z**: Normal attack (melee)
- **X**: Block (reduces damage by 90%, costs stamina per hit)
- **Q**: Steel Tempest - Launch a tornado projectile
- **W**: Wind Wall - Create a barrier to block projectiles
- **E**: Sweeping Blade - Dash through enemies

### Menu
- **Escape**: Pause menu
- **Enter**: Select menu option
- **Arrow Keys**: Navigate menu options

## Gameplay Guide

### Combat Tips
- **Combo System**: Chain normal attacks with skills for maximum damage
- **Stamina Management**: Running and blocking consume stamina; recover by landing hits or killing enemies
- **Lifesteal**: Every successful attack heals you for the full damage dealt
- **Wind Wall Strategy**: Time your W skill to block boss projectiles, but note that Kamehameha beams cannot be blocked
- **AD Scaling**: Equip items to boost your attack damage, which increases all skill damage

### Progression Strategy
1. **Early Game**: Focus on learning enemy patterns and collecting gold
2. **Mid Game**: Upgrade your most-used skills first (Q for damage, W for survival)
3. **Late Game**: Max out the "A" skill to boost base AD, amplifying all other skills
4. **Equipment Priority**: Bloodthirster (+10 AD) for early power, Infinity Edge (+50 AD) for late-game scaling

### Environmental Interactions
- **Boxes**: Push to create platforms or reach higher areas
- **Barrels**: Attack to break and reveal items (red potions, equipment)
- **Chests**: Interact to open and claim rewards
- **Checkpoints**: Activate statue checkpoints to set your respawn point

## Technical Details

### Project Structure
```
A3_Yasuo/
├── assets/              # Game assets (sprites, sounds, maps)
│   ├── Player/         # Yasuo animations
│   ├── NPC/            # Enemy sprites
│   ├── Boss/           # Boss and minion sprites
│   ├── Map/            # Tileset and decorations
│   ├── Skills/         # Skill effect animations
│   └── fonts/          # UI fonts
├── combat/             # Combat system modules
│   ├── skill_q.py     # Tornado skill
│   ├── skill_w.py     # Wind Wall skill
│   ├── skill_e.py     # Dash skill
│   └── damage.py      # Damage calculation
├── core/               # Core game systems
│   ├── game.py        # Main game loop
│   ├── camera.py      # Camera controller
│   ├── event.py       # Event system
│   └── sound.py       # Audio manager
├── entities/           # Game entities
│   ├── player.py      # Player controller
│   ├── npc.py         # Enemy AI
│   ├── boss.py        # Boss mechanics
│   └── projectile.py  # Projectile system
├── items/              # Item system
│   ├── item.py        # Item base class
│   ├── equipment.py   # Equipment items
│   └── consumable.py  # Consumable items
├── ui/                 # User interface
│   ├── hud.py         # HUD display
│   └── menu.py        # Menu system
├── world/              # World systems
│   ├── map.py         # Map rendering
│   ├── collision.py   # Collision detection
│   └── interactable.py # Interactive objects
├── main.py             # Entry point
├── settings.py         # Game configuration
└── requirements.txt    # Python dependencies
```

**Enjoy the game and may the wind guide your blade!**