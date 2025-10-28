# AI Intent Handler Package

This package contains the refactored AI intent detection system, split from the monolithic `ai_intent_handler_phase1.py` into maintainable, modular components.

## Structure

```
services/ai_intent/
├── __init__.py                    # Package entry point
├── ai_intent_handler.py           # Main coordinator
├── README.md                      # This documentation
├── core/                          # Core AI functionality
│   ├── __init__.py
│   ├── ai_client.py              # Claude API management
│   ├── context_builder.py        # Context building logic
│   ├── intent_detector.py        # AI intent detection
│   └── response_generator.py     # Response generation
├── handlers/                      # Intent-specific handlers
│   ├── __init__.py
│   ├── common_intent_handler.py  # Common intents (both roles)
│   ├── trainer_intent_handler.py # Trainer-specific intents
│   └── client_intent_handler.py  # Client-specific intents
└── utils/                         # Utilities
    ├── __init__.py
    ├── fallback_responses.py      # Fallback logic
    ├── intent_types.py           # Intent type definitions
    └── prompt_builder.py         # AI prompt construction
```

## Components

### Main Coordinator (`ai_intent_handler.py`)

- **Purpose**: Main entry point that coordinates all AI intent processing
- **Responsibilities**:
  - Preserve backward compatibility with existing API
  - Coordinate between core components
  - Handle initialization for different calling conventions

### Core Components (`core/`)

#### AIClient (`core/ai_client.py`)

- **Purpose**: Manage Claude API client and interactions
- **Responsibilities**: Initialize Claude client, send messages, handle API errors

#### ContextBuilder (`core/context_builder.py`)

- **Purpose**: Build context information for AI intent detection
- **Responsibilities**: Gather user data, recent tasks, chat history, role-specific context

#### IntentDetector (`core/intent_detector.py`)

- **Purpose**: Handle AI-powered intent detection using Claude
- **Responsibilities**: Build prompts, call AI API, parse responses, handle fallbacks

#### ResponseGenerator (`core/response_generator.py`)

- **Purpose**: Generate appropriate responses based on detected intent
- **Responsibilities**: Route to handlers, manage confidence levels, provide responses

### Intent Handlers (`handlers/`)

#### CommonIntentHandler (`handlers/common_intent_handler.py`)

- **Purpose**: Handle intents available to both trainers and clients
- **Supported Intents**: view_profile, edit_profile, delete_account, logout, switch_role, help

#### TrainerIntentHandler (`handlers/trainer_intent_handler.py`)

- **Purpose**: Handle trainer-specific intents (Phase 2 & 3)
- **Supported Intents**:
  - Phase 2: invite_trainee, create_trainee, view_trainees, remove_trainee
  - Phase 3: create_habit, edit_habit, delete_habit, assign_habit, view_habits, view_trainee_progress, trainee_report

#### ClientIntentHandler (`handlers/client_intent_handler.py`)

- **Purpose**: Handle client-specific intents (Phase 2 & 3)
- **Supported Intents**:
  - Phase 2: search_trainer, invite_trainer, view_trainers, remove_trainer
  - Phase 3: view_my_habits, log_habits, view_progress, weekly_report, monthly_report

### Utilities (`utils/`)

#### PromptBuilder (`utils/prompt_builder.py`)

- **Purpose**: Construct AI prompts for intent detection
- **Responsibilities**: Build role-specific prompts, format context, define examples

#### IntentTypes (`utils/intent_types.py`)

- **Purpose**: Define and manage available intent types
- **Responsibilities**: Categorize intents by role, validate intents, provide intent lists

#### FallbackResponseHandler (`utils/fallback_responses.py`)

- **Purpose**: Provide responses when AI is unavailable
- **Responsibilities**: Generate role-appropriate fallback messages

## Usage

### Basic Usage (Unchanged)

```python
from services.ai_intent import AIIntentHandler

# Initialize (backward compatible)
handler = AIIntentHandler(db, whatsapp)

# Handle intent
result = handler.handle_intent(phone, message, role, user_id, recent_tasks, chat_history)
```

### App Core Usage (Unchanged)

```python
from services.ai_intent import AIIntentHandler

# Initialize with config
handler = AIIntentHandler(Config, supabase, services_dict)

# Handle intent
result = handler.handle_intent(phone, message, role, user_id, recent_tasks, chat_history)
```

## Benefits of This Split

### 🎯 Maintainability

- **Single Responsibility**: Each module has one clear purpose
- **Easy Navigation**: Find specific functionality quickly
- **Reduced Complexity**: Smaller, focused files (~50-150 lines each)

### 🚀 Scalability

- **Easy Extension**: Add new intent types easily
- **Modular Growth**: Each component can grow independently
- **Better Testing**: Test components in isolation

### 🔧 Developer Experience

- **Faster Development**: Clear structure speeds up development
- **Better Debugging**: Easier to isolate issues
- **Improved Collaboration**: Multiple developers can work on different components

### 📊 Performance

- **Lazy Loading**: Only load needed components
- **Better Caching**: Cache at component level
- **Optimized Imports**: Reduced import overhead

## Migration Notes

- **Backward Compatibility**: All existing imports continue to work
- **Same API**: No changes to external interface
- **Functionality Preserved**: All original logic maintained
- **Enhanced Features**: Better error handling and logging

## Adding New Intents

### 1. Define Intent Type

```python
# In utils/intent_types.py
self.trainer_intents.append('new_intent_type')
```

### 2. Add Handler Method

```python
# In handlers/trainer_intent_handler.py
def _handle_new_intent(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
    # Implementation here
    pass
```

### 3. Update Prompt

```python
# In utils/prompt_builder.py
# Add to available features description
```

## Testing

The package includes comprehensive error handling and fallback mechanisms:

- AI client unavailable → Fallback responses
- Invalid JSON response → Default intent
- Handler errors → Error responses
- Network issues → Graceful degradation

## Future Enhancements

- **Intent Caching**: Cache frequent intents
- **A/B Testing**: Test different prompt strategies
- **Analytics**: Track intent detection accuracy
- **Multi-language**: Support multiple languages
- **Custom Intents**: Allow custom intent definitions

This modular structure transforms the monolithic AI intent handler into a clean, maintainable architecture that supports rapid development of new AI features while preserving all existing functionality.
