# AI Scene Generation System

## Overview

The AI Scene Generation System provides dynamic, AI-generated scenes with controlled choice mapping for the Telegram RPG game bot. This system generates immersive 3-5 sentence scene descriptions and maps AI-generated choices to predefined action IDs.

## Key Features

### 1. AI Scene Generation
- **Dynamic Content**: Generates unique 3-5 sentence scene descriptions using OpenAI
- **Immersive Descriptions**: Includes environmental details, dangers, and opportunities
- **Multilingual Support**: Supports English and Ukrainian languages
- **Contextual Generation**: Scenes are generated based on fantasy RPG context

### 2. Controlled Choice Mapping
- **Predefined Actions**: Maps AI choices to 5 core action types:
  - `SCOUT` - Gather information and assess risks
  - `FIGHT` - Engage in combat or aggressive action
  - `RETREAT` - Withdraw from dangerous situations
  - `TALK` - Engage in diplomatic or social interaction
  - `PICKLOCK` - Attempt to open locks or bypass barriers

- **Smart Keyword Matching**: Uses keyword-based mapping with priority scoring
- **Fallback Mapping**: Provides default mapping if no keywords match
- **Consistent Actions**: Ensures all choices map to valid game actions

### 3. Integration with Game Systems
- **Action Processing**: Integrated with existing action consequence system
- **Energy Management**: AI scenes consume energy and affect player stats
- **Risk System**: Actions affect risk levels and player progression
- **FSM Integration**: Works with the existing finite state machine

## Implementation Details

### Core Components

#### 1. AISceneGenerationService (`app/services/ai/scene_generation_service.py`)
- Main service for generating AI scenes
- Handles OpenAI API communication
- Manages choice parsing and mapping
- Provides fallback mechanisms

#### 2. Enhanced Prompts (`app/prompts.py`)
- Added scene and choices prompt types
- Multilingual support for Ukrainian
- Optimized for 3-5 sentence descriptions
- Structured choice generation prompts

#### 3. New Action Types (`app/game/actions.py`)
- Added `SCOUT`, `FIGHT`, `PICKLOCK` actions
- Defined action consequences and effects
- Integrated with existing action processing system

#### 4. Scene System Integration (`app/game/scenes.py`)
- Added `AI_GENERATED` scene type
- Integrated AI scene generation into scene graph
- Maintains compatibility with existing scene system

#### 5. Game Handler (`app/handlers/game.py`)
- Added `/ai_scene` command
- Handles AI scene action processing
- Provides seamless integration with adventure system

### Choice Mapping Algorithm

The system uses a sophisticated keyword-based mapping approach:

1. **Keyword Detection**: Scans choice text for action-related keywords
2. **Priority Scoring**: Longer keywords get higher priority
3. **Best Match Selection**: Chooses the action with the highest score
4. **Fallback Mapping**: Uses position-based mapping if no keywords match

### Example Choice Mappings

```
"Scout the area" -> SCOUT
"Investigate carefully" -> SCOUT
"Fight the enemy" -> FIGHT
"Attack boldly" -> FIGHT
"Retreat safely" -> RETREAT
"Talk to the guard" -> TALK
"Pick the lock" -> PICKLOCK
```

## Usage

### For Players
- Use `/ai_scene` command to generate AI-powered scenes
- Choose from 3 dynamically generated options
- Each choice maps to a specific game action
- Actions affect energy, stats, and risk levels

### For Developers
- Extend choice mapping by adding keywords to `CHOICE_MAPPING`
- Modify prompts in `app/prompts.py` for different content styles
- Add new action types in `app/game/actions.py`
- Customize scene generation parameters

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for AI generation
- Language settings via i18n service

### Prompt Configuration
- Scene generation: 200 max tokens, 0.8 temperature
- Choice generation: 100 max tokens, 0.7 temperature
- Optimized for concise, engaging content

## Error Handling

- **API Failures**: Graceful fallback to regular scenes
- **Empty Responses**: Fallback choice generation
- **Parsing Errors**: Default choice mapping
- **Network Issues**: Retry logic with exponential backoff

## Testing

Run the test script to verify functionality:
```bash
python test_ai_scene.py
```

## Future Enhancements

1. **Context Awareness**: Use previous scene context for better generation
2. **Player Stats Integration**: Incorporate player stats into scene generation
3. **Dynamic Difficulty**: Adjust scene complexity based on player level
4. **Custom Themes**: Allow players to choose scene themes or settings
5. **Choice History**: Learn from player choices to improve generation

## Technical Notes

- Uses OpenAI GPT-4o-mini for cost efficiency
- Implements retry logic for API reliability
- Maintains backward compatibility with existing systems
- Follows existing code patterns and architecture
- Includes comprehensive logging and error handling
