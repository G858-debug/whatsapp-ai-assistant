# Message Router Package

This package contains the refactored message routing system, split into highly maintainable modules organized by functionality.

## Structure

```
services/message_router/
├── __init__.py                     # Package initialization
├── message_router.py               # Main router class
├── README.md                       # This documentation
├── handlers/                       # Message handling logic
│   ├── __init__.py
│   ├── button_handler.py          # Button response delegation
│   ├── universal_command_handler.py # Universal commands (/help, /logout, etc.)
│   ├── new_user_handler.py        # New user registration flow
│   ├── login_handler.py           # Login flow for existing users
│   ├── logged_in_user_handler.py  # Authenticated user message routing
│   ├── role_command_handler.py    # Role command delegation
│   ├── task_handler.py            # Task continuation delegation
│   ├── ai_intent_handler.py       # AI intent determination
│   ├── buttons/                    # Button handling modules
│   │   ├── __init__.py
│   │   ├── button_handler.py      # Main button coordinator
│   │   ├── relationship_buttons.py # Trainer-client relationship buttons
│   │   ├── registration_buttons.py # Registration/login buttons
│   │   └── client_creation_buttons.py # New client creation buttons
│   ├── commands/                   # Command handling modules
│   │   ├── __init__.py
│   │   ├── role_command_handler.py # Main command coordinator
│   │   ├── common_commands.py     # Commands for both roles
│   │   ├── trainer_commands.py    # Trainer-specific commands
│   │   └── client_commands.py     # Client-specific commands
│   └── tasks/                      # Task handling modules
│       ├── __init__.py
│       ├── task_handler.py        # Main task coordinator
│       ├── core_tasks.py          # Registration, profile tasks
│       ├── relationship_tasks.py  # Phase 2 relationship tasks
│       └── habit_tasks.py         # Phase 3 habit tasks
└── utils/                          # Utility classes
    ├── __init__.py
    └── message_history.py          # Message history management
```

## Components

### Main Router (`message_router.py`)

- **Purpose**: Main entry point for message routing
- **Responsibilities**: Initial message routing logic, coordination between handlers, error handling

### Core Handlers

#### ButtonHandler (`handlers/button_handler.py`)

- **Purpose**: Delegate button interactions to specialized handlers
- **Delegates to**: `handlers/buttons/` modules

#### UniversalCommandHandler (`handlers/universal_command_handler.py`)

- **Purpose**: Handle commands that work in any authentication state
- **Responsibilities**: `/help`, `/logout`, `/switch-role`, `/register`, `/stop` commands

#### NewUserHandler, LoginHandler, LoggedInUserHandler

- **Purpose**: Handle different user authentication states
- **Responsibilities**: Route to appropriate flows based on user status

#### RoleCommandHandler (`handlers/role_command_handler.py`)

- **Purpose**: Delegate role-specific commands to specialized handlers
- **Delegates to**: `handlers/commands/` modules

#### TaskHandler (`handlers/task_handler.py`)

- **Purpose**: Delegate task continuation to specialized handlers
- **Delegates to**: `handlers/tasks/` modules

### Button Handlers (`handlers/buttons/`)

- **RelationshipButtonHandler**: Accept/decline trainer-client invitations
- **RegistrationButtonHandler**: Registration and login buttons
- **ClientCreationButtonHandler**: New client account creation approval

### Command Handlers (`handlers/commands/`)

- **CommonCommandHandler**: Commands for both roles (profile management)
- **TrainerCommandHandler**: Trainer-specific commands (relationships, habits)
- **ClientCommandHandler**: Client-specific commands (relationships, habits)

### Task Handlers (`handlers/tasks/`)

- **CoreTaskHandler**: Registration, profile editing, account deletion
- **RelationshipTaskHandler**: Phase 2 relationship management tasks
- **HabitTaskHandler**: Phase 3 habit creation, logging, and reporting

### Utils

- **MessageHistoryManager**: Chat history management for AI context

## Usage

```python
from services.message_router import MessageRouter

# Initialize router
router = MessageRouter(supabase_client, whatsapp_service)

# Route a message
result = router.route_message(phone, message, button_id=None)
```

## Benefits of This Structure

1. **Separation of Concerns**: Each handler has a single, clear responsibility
2. **Maintainability**: Easy to find and modify specific functionality
3. **Testability**: Each component can be tested independently
4. **Scalability**: Easy to add new handlers or extend existing ones
5. **Readability**: Clear structure makes the codebase easier to understand
6. **Reusability**: Handlers can be reused in different contexts

## Migration Notes

- The original `services/message_router.py` has been split but all functionality is preserved
- Import paths remain the same: `from services.message_router import MessageRouter`
- All existing code using the MessageRouter will continue to work without changes
- The original file can be safely removed after testing the new structure
