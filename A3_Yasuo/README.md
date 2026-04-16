# A3 Yasuo Game Project

## Overview
A3 Yasuo is a character-based game where players can choose between different characters, each with unique skills and abilities. The project is structured to allow easy expansion and modification of character classes and combat mechanics.

## Project Structure
```
A3_Yasuo
├── entities
│   ├── __init__.py
│   ├── base_char.py          # Base class for all characters
│   ├── yasuo.py              # Yasuo character class
│   ├── leaf_ranger.py        # Leaf Ranger character class
│   └── player_2_projectile.py # Projectile definitions
├── combat
│   ├── __init__.py
│   ├── player_2
│   │   ├── skill_q.py        # Q skill implementation for Leaf Ranger
│   │   ├── skill_w.py        # W skill implementation for Leaf Ranger
│   │   └── skill_e.py        # E skill implementation for Leaf Ranger
│   └── utils.py              # Utility functions for combat
├── assets                     # Directory for asset files (images, sounds)
├── tests
│   ├── test_base_char.py      # Unit tests for BaseChar
│   ├── test_yasuo.py          # Unit tests for Yasuo
│   └── test_leaf_ranger.py    # Unit tests for Leaf Ranger
├── settings.py                # Configuration settings for the project
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd A3_Yasuo
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
- Run the game by executing the main script (to be defined).
- Choose your character (Yasuo or Leaf Ranger) and utilize their unique skills in combat.

## Characters
### Yasuo
- A swift and agile character with skills focused on quick attacks and mobility.
- Skills include:
  - Q: A powerful attack that deals damage to enemies.
  - W: A defensive skill that provides a temporary shield.
  - E: A mobility skill that allows Yasuo to dash to a target.

### Leaf Ranger
- A ranged character that excels in dealing damage from a distance.
- Skills include:
  - Q: A skill that launches a projectile at enemies.
  - W: A skill that enhances normal attacks with special effects.
  - E: An area-of-effect skill that damages multiple enemies.

## Testing
- Unit tests are provided for each character class to ensure functionality.
- Run tests using a testing framework like `pytest`:
  ```
  pytest tests/
  ```

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.