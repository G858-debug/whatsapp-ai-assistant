# Trainer-Client Features Implementation Plan

## Overview

Based on your current system analysis and established patterns, this plan covers three major features:

1. **Enhanced Habit Management System**
2. **Comprehensive Workout Management System**
3. **Fitness Assessment System with Photo Upload**

Each feature follows your established patterns:

- ✅ Both text-based and flow-based interfaces
- ✅ Text inputs managed via JSON configurations (like your `whatsapp_flows/` structure)
- ✅ AI-powered assistance and natural language processing
- ✅ Client-trainer linking with user IDs and privacy protection
- ✅ Reminder systems and progress tracking
- ✅ Comprehensive logging and analytics

## Current System Analysis

### ✅ **What's Already Working**

- Basic habit tracking system with flows (`trainer_habit_setup_flow.json`, `client_habit_logging_flow.json`)
- Database tables for habits, habit_tracking, workouts, assessments
- WhatsApp flow infrastructure
- AI intent detection system
- Client-trainer relationship management

### 🔧 **What Needs Enhancement**

- Text-based habit management (currently only flows)
- Complete workout management system
- Enhanced fitness assessment with photo upload
- Reminder systems for all features
- AI-powered assistance for all operations
- JSON-based text input configurations

---

## Feature 1: Enhanced Habit Management System

### Current State Analysis

- ✅ Flow-based habit setup exists (`trainer_habit_setup_flow.json`)
- ✅ Flow-based habit logging exists (`client_habit_logging_flow.json`)
- ✅ Database tables: `habits`, `habit_tracking`
- ❌ No text-based habit management
- ❌ No JSON configurations for text inputs
- ❌ Limited reminder system
- ❌ No AI assistance for habit operations

### Enhanced Implementation Plan

#### A. Database Schema Enhancements

```sql
-- Enhance existing habits table
ALTER TABLE habits ADD COLUMN IF NOT EXISTS habit_name VARCHAR(100);
ALTER TABLE habits ADD COLUMN IF NOT EXISTS target_value NUMERIC(10,2);
ALTER TABLE habits ADD COLUMN IF NOT EXISTS target_unit VARCHAR(20);
ALTER TABLE habits ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT true;
ALTER TABLE habits ADD COLUMN IF NOT EXISTS reminder_time TIME;
ALTER TABLE habits ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

-- Create habit assignments table for better client-trainer linking
CREATE TABLE IF NOT EXISTS habit_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    habit_id UUID NOT NULL REFERENCES habits(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed
    target_value NUMERIC(10,2),
    target_unit VARCHAR(20),
    reminder_enabled BOOLEAN DEFAULT true,
    reminder_time TIME DEFAULT '09:00:00',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### B. Text Input JSON Configurations

Following your `whatsapp_flows/` pattern, create `text_inputs/` folder:

```
text_inputs/habits/
├── trainer_habit_create_inputs.json
├── trainer_habit_edit_inputs.json
├── trainer_habit_assign_inputs.json
├── client_habit_log_inputs.json
├── habit_reminder_setup_inputs.json
└── habit_progress_view_inputs.json
```

**Example: `text_inputs/habits/trainer_habit_create_inputs.json`**

```json
{
  "version": "1.0",
  "feature_type": "habit_management",
  "operation": "create_habit",
  "description": "Text-based habit creation for trainers",
  "steps": [
    {
      "step": 0,
      "field": "habit_name",
      "question": "What habit would you like to create? 🎯\n\nExamples:\n• Daily Water Intake\n• Morning Exercise\n• Healthy Breakfast\n• Evening Walk\n\nType the habit name:",
      "validation": {
        "type": "text",
        "min_length": 3,
        "max_length": 100,
        "required": true
      },
      "success_response": "Great habit choice! 💪"
    },
    {
      "step": 1,
      "field": "habit_type",
      "question": "What type of habit is this? 📊\n\n1️⃣ Measurable (with numbers - water, steps, hours)\n2️⃣ Yes/No (completed or not - workout, meditation)\n3️⃣ Scale (1-10 rating - mood, energy)\n\nChoose 1, 2, or 3:",
      "validation": {
        "type": "choice",
        "choices": {
          "1": "measurable",
          "2": "boolean",
          "3": "scale"
        }
      },
      "success_response": "Perfect! 📈"
    },
    {
      "step": 2,
      "field": "target_value",
      "question": "What's the target for this habit? 🎯\n\n{conditional_text}\n\nEnter the target:",
      "conditional_text": {
        "measurable": "Examples: 8 (for 8 glasses of water), 10000 (for steps), 7.5 (for hours of sleep)",
        "boolean": "Enter 1 for daily completion goal",
        "scale": "Enter the target rating (1-10)"
      },
      "validation": {
        "type": "number",
        "min": 0.1,
        "max": 100000
      },
      "success_response": "Target set! 🎯"
    },
    {
      "step": 3,
      "field": "target_unit",
      "question": "What's the unit for this habit? 📏\n\n{conditional_options}\n\nType the unit or choose a number:",
      "conditional_options": {
        "measurable": "1️⃣ glasses\n2️⃣ liters\n3️⃣ steps\n4️⃣ hours\n5️⃣ minutes\n6️⃣ times\n7️⃣ kg\n8️⃣ Custom unit",
        "boolean": "1️⃣ completed\n2️⃣ done\n3️⃣ times",
        "scale": "1️⃣ rating\n2️⃣ score\n3️⃣ level"
      },
      "validation": {
        "type": "choice_or_text",
        "choices": {
          "1": "glasses",
          "2": "liters",
          "3": "steps",
          "4": "hours",
          "5": "minutes",
          "6": "times",
          "7": "kg",
          "8": "custom"
        }
      },
      "success_response": "Unit confirmed! 📊"
    },
    {
      "step": 4,
      "field": "reminder_time",
      "question": "When should clients get reminders? ⏰\n\n1️⃣ Morning (9:00 AM)\n2️⃣ Afternoon (2:00 PM)\n3️⃣ Evening (6:00 PM)\n4️⃣ Custom time (HH:MM format)\n5️⃣ No reminders\n\nChoose option or enter custom time:",
      "validation": {
        "type": "time_or_choice",
        "choices": {
          "1": "09:00",
          "2": "14:00",
          "3": "18:00",
          "5": "none"
        },
        "time_format": "HH:MM"
      },
      "success_response": "Reminder time set! ⏰"
    }
  ],
  "completion": {
    "message": "🎉 *Habit Created Successfully!*\n\n📋 **Habit Details:**\n• Name: {habit_name}\n• Type: {habit_type}\n• Target: {target_value} {target_unit}\n• Reminders: {reminder_time}\n\n🚀 **Next Steps:**\n• Use `/assign_habit {habit_name}` to assign to clients\n• Type `/habits` to view all your habits\n• Ask me to 'assign this habit to client C1234'\n\nGreat job creating healthy habits for your clients! 💪"
  }
}
```

#### C. Enhanced Habit Management Classes

```python
# services/habits/habit_manager.py
class HabitManager:
    def __init__(self, supabase_client, text_input_manager):
        self.db = supabase_client
        self.input_manager = text_input_manager

    def create_habit_text_based(self, trainer_phone: str) -> Dict:
        """Start text-based habit creation"""
        handler = self.input_manager.get_handler('trainer_habit_create')
        return handler.start_process()

    def assign_habit_to_client(self, trainer_id: str, habit_id: str, client_user_id: str) -> Dict:
        """Assign habit to client using user ID"""

    def get_client_habits(self, client_id: str) -> List[Dict]:
        """Get all active habits for a client"""

    def log_habit_completion(self, client_id: str, habit_id: str, value: float, date: str = None) -> Dict:
        """Log habit completion by client"""

    def send_habit_reminders(self, reminder_time: str) -> Dict:
        """Send habit reminders to clients at specified time"""

# services/habits/habit_text_handler.py
class HabitTextHandler:
    def __init__(self, supabase_client):
        self.db = supabase_client

    def handle_habit_creation_step(self, trainer_phone: str, step: int, response: str) -> Dict:
        """Handle each step of text-based habit creation"""

    def handle_habit_logging_text(self, client_phone: str, message: str) -> Dict:
        """Handle text-based habit logging by clients"""

    def handle_habit_assignment_text(self, trainer_phone: str, message: str) -> Dict:
        """Handle text-based habit assignment to clients"""
```

#### D. AI Integration for Habits

```python
# Enhanced AI intents for habits
HABIT_AI_INTENTS = {
    'create_habit': {
        'patterns': ['create habit', 'new habit', 'add habit', 'setup habit'],
        'handler': 'habit_manager.create_habit_text_based',
        'user_type': 'trainer',
        'button_text': '🎯 Create Habit'
    },
    'assign_habit': {
        'patterns': ['assign habit to C1234', 'give habit to client', 'set habit for client'],
        'handler': 'habit_manager.assign_habit_to_client',
        'user_type': 'trainer',
        'button_text': '📋 Assign Habit'
    },
    'log_habit': {
        'patterns': ['log habit', 'record habit', 'mark habit done', 'habit completed'],
        'handler': 'habit_manager.log_habit_completion',
        'user_type': 'client',
        'button_text': '✅ Log Habit'
    },
    'view_habits': {
        'patterns': ['my habits', 'show habits', 'habit progress', 'habit status'],
        'handler': 'habit_manager.get_client_habits',
        'button_text': '📊 My Habits'
    }
}
```

---

## Feature 2: Comprehensive Workout Management System

### Current State Analysis

- ✅ Database table: `workouts` exists
- ❌ No workout management flows or text interface
- ❌ No workout assignment system
- ❌ No workout logging by clients
- ❌ No reminder system for workouts

### Enhanced Implementation Plan

#### A. Database Schema Enhancements

```sql
-- Enhance existing workouts table
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS workout_status VARCHAR(20) DEFAULT 'active';
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT true;
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS reminder_time TIME DEFAULT '08:00:00';
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS estimated_calories INTEGER;
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS equipment_needed JSONB DEFAULT '[]';
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS instructions TEXT;

-- Create workout assignments table
CREATE TABLE IF NOT EXISTS workout_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    workout_id UUID NOT NULL REFERENCES workouts(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed
    scheduled_date DATE,
    reminder_enabled BOOLEAN DEFAULT true,
    reminder_time TIME DEFAULT '08:00:00',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create workout logs table
CREATE TABLE IF NOT EXISTS workout_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    workout_id UUID NOT NULL REFERENCES workouts(id),
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_minutes INTEGER,
    difficulty_rating INTEGER CHECK (difficulty_rating >= 1 AND difficulty_rating <= 10),
    calories_burned INTEGER,
    notes TEXT,
    exercise_logs JSONB DEFAULT '[]', -- Individual exercise completion
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### B. Workout Text Input Configurations

```
text_inputs/workouts/
├── trainer_workout_create_inputs.json
├── trainer_workout_edit_inputs.json
├── trainer_workout_assign_inputs.json
├── client_workout_log_inputs.json
├── workout_reminder_setup_inputs.json
└── workout_progress_view_inputs.json
```

**Example: `text_inputs/workouts/trainer_workout_create_inputs.json`**

```json
{
  "version": "1.0",
  "feature_type": "workout_management",
  "operation": "create_workout",
  "description": "Text-based workout creation for trainers",
  "steps": [
    {
      "step": 0,
      "field": "workout_name",
      "question": "What's the name of this workout? 💪\n\nExamples:\n• Upper Body Strength\n• HIIT Cardio Blast\n• Morning Yoga Flow\n• Full Body Circuit\n\nEnter workout name:",
      "validation": {
        "type": "text",
        "min_length": 3,
        "max_length": 200,
        "required": true
      },
      "success_response": "Great workout name! 🔥"
    },
    {
      "step": 1,
      "field": "workout_type",
      "question": "What type of workout is this? 🏋️\n\n1️⃣ Strength Training\n2️⃣ Cardio\n3️⃣ Flexibility/Yoga\n4️⃣ HIIT\n5️⃣ General Fitness\n\nChoose 1-5:",
      "validation": {
        "type": "choice",
        "choices": {
          "1": "strength",
          "2": "cardio",
          "3": "flexibility",
          "4": "hiit",
          "5": "general"
        }
      },
      "success_response": "Workout type selected! 📋"
    },
    {
      "step": 2,
      "field": "difficulty_level",
      "question": "What's the difficulty level? 📊\n\n1️⃣ Beginner (New to exercise)\n2️⃣ Intermediate (Some experience)\n3️⃣ Advanced (Very experienced)\n\nChoose 1-3:",
      "validation": {
        "type": "choice",
        "choices": {
          "1": "beginner",
          "2": "intermediate",
          "3": "advanced"
        }
      },
      "success_response": "Difficulty set! 💯"
    },
    {
      "step": 3,
      "field": "duration_minutes",
      "question": "How long is this workout? ⏱️\n\nEnter duration in minutes (e.g., 30, 45, 60):",
      "validation": {
        "type": "number",
        "min": 5,
        "max": 180
      },
      "success_response": "Duration confirmed! ⏰"
    },
    {
      "step": 4,
      "field": "exercises",
      "question": "List the exercises in this workout: 📝\n\nFormat: Exercise Name - Sets x Reps\nExample:\n• Push-ups - 3 x 12\n• Squats - 3 x 15\n• Plank - 3 x 30 seconds\n\nEnter exercises (one per line):",
      "validation": {
        "type": "multiline_text",
        "min_lines": 1,
        "max_lines": 20
      },
      "success_response": "Exercises added! 💪"
    },
    {
      "step": 5,
      "field": "equipment_needed",
      "question": "What equipment is needed? 🏋️\n\n1️⃣ No equipment (bodyweight)\n2️⃣ Dumbbells\n3️⃣ Resistance bands\n4️⃣ Gym equipment\n5️⃣ Custom equipment list\n\nChoose option or list custom equipment:",
      "validation": {
        "type": "choice_or_text",
        "choices": {
          "1": "none",
          "2": "dumbbells",
          "3": "resistance_bands",
          "4": "gym_equipment"
        }
      },
      "success_response": "Equipment noted! 🛠️"
    }
  ],
  "completion": {
    "message": "🎉 *Workout Created Successfully!*\n\n💪 **Workout Details:**\n• Name: {workout_name}\n• Type: {workout_type}\n• Level: {difficulty_level}\n• Duration: {duration_minutes} minutes\n• Equipment: {equipment_needed}\n\n🚀 **Next Steps:**\n• Use `/assign_workout {workout_name}` to assign to clients\n• Type `/workouts` to view all your workouts\n• Ask me to 'assign this workout to client C1234'\n\nYour clients will love this workout! 🔥"
  }
}
```

#### C. Workout Management Classes

```python
# services/workouts/workout_manager.py
class WorkoutManager:
    def __init__(self, supabase_client, text_input_manager):
        self.db = supabase_client
        self.input_manager = text_input_manager

    def create_workout_text_based(self, trainer_phone: str) -> Dict:
        """Start text-based workout creation"""

    def assign_workout_to_client(self, trainer_id: str, workout_id: str, client_user_id: str, scheduled_date: str = None) -> Dict:
        """Assign workout to client using user ID"""

    def get_client_workouts(self, client_id: str) -> List[Dict]:
        """Get all assigned workouts for a client"""

    def log_workout_completion(self, client_id: str, workout_id: str, duration: int, difficulty_rating: int, notes: str = None) -> Dict:
        """Log workout completion by client"""

    def send_workout_reminders(self, reminder_time: str) -> Dict:
        """Send workout reminders to clients"""

# services/workouts/workout_text_handler.py
class WorkoutTextHandler:
    def handle_workout_creation_step(self, trainer_phone: str, step: int, response: str) -> Dict:
        """Handle each step of text-based workout creation"""

    def handle_workout_logging_text(self, client_phone: str, message: str) -> Dict:
        """Handle text-based workout logging by clients"""

    def parse_exercises_from_text(self, exercise_text: str) -> List[Dict]:
        """Parse exercise list from text input"""
```

---

## Feature 3: Fitness Assessment System with Photo Upload

### Current State Analysis

- ✅ Database table: `assessments` exists
- ❌ No assessment creation/management system
- ❌ No photo upload capability
- ❌ No assessment assignment to clients
- ❌ No client assessment completion interface

### Enhanced Implementation Plan

#### A. Database Schema Enhancements

```sql
-- Enhance existing assessments table
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS trainer_id UUID REFERENCES trainers(id);
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS assessment_name VARCHAR(200);
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft';
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS due_date DATE;
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT true;

-- Create assessment templates table
CREATE TABLE IF NOT EXISTS assessment_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id),
    template_name VARCHAR(200) NOT NULL,
    description TEXT,
    questions JSONB NOT NULL DEFAULT '[]',
    photo_requirements JSONB DEFAULT '[]', -- What photos are needed
    estimated_duration INTEGER DEFAULT 15, -- minutes
    category VARCHAR(50) DEFAULT 'general', -- initial, progress, final, custom
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create assessment assignments table
CREATE TABLE IF NOT EXISTS assessment_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    template_id UUID NOT NULL REFERENCES assessment_templates(id),
    assessment_id UUID REFERENCES assessments(id), -- Created when client starts
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date DATE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, in_progress, completed, overdue
    reminder_enabled BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create assessment photos table
CREATE TABLE IF NOT EXISTS assessment_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id),
    photo_type VARCHAR(50) NOT NULL, -- front, side, back, progress, custom
    photo_url TEXT NOT NULL, -- Supabase storage URL
    photo_description TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_size INTEGER, -- bytes
    file_type VARCHAR(20), -- jpg, png, etc
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### B. Assessment Text Input Configurations

```
text_inputs/assessments/
├── trainer_assessment_create_inputs.json
├── trainer_assessment_edit_inputs.json
├── trainer_assessment_assign_inputs.json
├── client_assessment_complete_inputs.json
├── assessment_photo_upload_inputs.json
└── assessment_progress_view_inputs.json
```

**Example: `text_inputs/assessments/trainer_assessment_create_inputs.json`**

```json
{
  "version": "1.0",
  "feature_type": "assessment_management",
  "operation": "create_assessment",
  "description": "Text-based fitness assessment creation for trainers",
  "steps": [
    {
      "step": 0,
      "field": "assessment_name",
      "question": "What's the name of this assessment? 📋\n\nExamples:\n• Initial Fitness Assessment\n• 30-Day Progress Check\n• Body Composition Analysis\n• Strength & Flexibility Test\n\nEnter assessment name:",
      "validation": {
        "type": "text",
        "min_length": 5,
        "max_length": 200,
        "required": true
      },
      "success_response": "Assessment name set! 📝"
    },
    {
      "step": 1,
      "field": "assessment_category",
      "question": "What type of assessment is this? 🎯\n\n1️⃣ Initial Assessment (new clients)\n2️⃣ Progress Check (ongoing clients)\n3️⃣ Final Assessment (program completion)\n4️⃣ Custom Assessment\n\nChoose 1-4:",
      "validation": {
        "type": "choice",
        "choices": {
          "1": "initial",
          "2": "progress",
          "3": "final",
          "4": "custom"
        }
      },
      "success_response": "Category selected! 📊"
    },
    {
      "step": 2,
      "field": "questions",
      "question": "Add assessment questions: ❓\n\nFormat each question on a new line:\n• Question Type: Question Text\n\nTypes available:\n• text: How do you feel about your current fitness?\n• number: What's your current weight in kg?\n• scale: Rate your energy level (1-10)\n• choice: Do you have any injuries? (Yes/No)\n\nEnter questions:",
      "validation": {
        "type": "multiline_text",
        "min_lines": 3,
        "max_lines": 20
      },
      "success_response": "Questions added! ❓"
    },
    {
      "step": 3,
      "field": "photo_requirements",
      "question": "What photos should clients upload? 📸\n\n1️⃣ No photos needed\n2️⃣ Progress photos (front, side, back)\n3️⃣ Specific body parts\n4️⃣ Custom photo requirements\n\nChoose option or describe custom requirements:",
      "validation": {
        "type": "choice_or_text",
        "choices": {
          "1": "none",
          "2": "progress_standard",
          "3": "body_parts"
        }
      },
      "success_response": "Photo requirements set! 📷"
    },
    {
      "step": 4,
      "field": "estimated_duration",
      "question": "How long should this assessment take? ⏱️\n\nEnter estimated duration in minutes (5-60):",
      "validation": {
        "type": "number",
        "min": 5,
        "max": 60
      },
      "success_response": "Duration estimated! ⏰"
    }
  ],
  "completion": {
    "message": "🎉 *Assessment Created Successfully!*\n\n📋 **Assessment Details:**\n• Name: {assessment_name}\n• Category: {assessment_category}\n• Questions: {question_count} questions\n• Photos: {photo_requirements}\n• Duration: ~{estimated_duration} minutes\n\n🚀 **Next Steps:**\n• Use `/assign_assessment {assessment_name}` to assign to clients\n• Type `/assessments` to view all your assessments\n• Ask me to 'assign this assessment to client C1234'\n\nYour assessment is ready to help track client progress! 📊"
  }
}
```

#### C. Assessment Management Classes

```python
# services/assessments/assessment_manager.py
class AssessmentManager:
    def __init__(self, supabase_client, text_input_manager, photo_handler):
        self.db = supabase_client
        self.input_manager = text_input_manager
        self.photo_handler = photo_handler

    def create_assessment_text_based(self, trainer_phone: str) -> Dict:
        """Start text-based assessment creation"""

    def assign_assessment_to_client(self, trainer_id: str, template_id: str, client_user_id: str, due_date: str = None) -> Dict:
        """Assign assessment to client using user ID"""

    def get_client_assessments(self, client_id: str) -> List[Dict]:
        """Get all assigned assessments for a client"""

    def start_assessment_completion(self, client_id: str, assignment_id: str) -> Dict:
        """Start assessment completion process for client"""

    def handle_photo_upload(self, client_id: str, assessment_id: str, photo_data: bytes, photo_type: str) -> Dict:
        """Handle photo upload to Supabase storage"""

# services/assessments/photo_handler.py
class AssessmentPhotoHandler:
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.storage = supabase_client.storage

    def upload_assessment_photo(self, client_id: str, assessment_id: str, photo_data: bytes, photo_type: str) -> Dict:
        """Upload photo to Supabase storage and save metadata"""

    def get_assessment_photos(self, assessment_id: str) -> List[Dict]:
        """Get all photos for an assessment"""

    def delete_assessment_photo(self, photo_id: str) -> Dict:
        """Delete photo from storage and database"""

# services/assessments/assessment_text_handler.py
class AssessmentTextHandler:
    def handle_assessment_creation_step(self, trainer_phone: str, step: int, response: str) -> Dict:
        """Handle each step of text-based assessment creation"""

    def handle_assessment_completion_step(self, client_phone: str, step: int, response: str) -> Dict:
        """Handle each step of client assessment completion"""

    def parse_questions_from_text(self, questions_text: str) -> List[Dict]:
        """Parse assessment questions from text input"""
```

---

## Integration with Existing Systems

### A. AI Intent Enhancements

```python
# Enhanced AI intents for all three features
COMPREHENSIVE_AI_INTENTS = {
    # Habit Management
    'create_habit': {
        'patterns': ['create habit', 'new habit', 'add habit for clients'],
        'handler': 'habit_manager.create_habit_text_based',
        'user_type': 'trainer'
    },
    'assign_habit_to_client': {
        'patterns': ['assign habit to C1234', 'give water habit to client', 'set habit for C5678'],
        'handler': 'habit_manager.assign_habit_to_client',
        'user_type': 'trainer'
    },
    'log_my_habits': {
        'patterns': ['log habits', 'record my habits', 'mark habits done'],
        'handler': 'habit_manager.log_habit_completion',
        'user_type': 'client'
    },

    # Workout Management
    'create_workout': {
        'patterns': ['create workout', 'new workout', 'design workout'],
        'handler': 'workout_manager.create_workout_text_based',
        'user_type': 'trainer'
    },
    'assign_workout_to_client': {
        'patterns': ['assign workout to C1234', 'give workout to client', 'schedule workout for C5678'],
        'handler': 'workout_manager.assign_workout_to_client',
        'user_type': 'trainer'
    },
    'log_my_workout': {
        'patterns': ['log workout', 'completed workout', 'finished exercise'],
        'handler': 'workout_manager.log_workout_completion',
        'user_type': 'client'
    },

    # Assessment Management
    'create_assessment': {
        'patterns': ['create assessment', 'new assessment', 'fitness test'],
        'handler': 'assessment_manager.create_assessment_text_based',
        'user_type': 'trainer'
    },
    'assign_assessment_to_client': {
        'patterns': ['assign assessment to C1234', 'send assessment to client'],
        'handler': 'assessment_manager.assign_assessment_to_client',
        'user_type': 'trainer'
    },
    'complete_my_assessment': {
        'patterns': ['complete assessment', 'fill assessment', 'do fitness test'],
        'handler': 'assessment_manager.start_assessment_completion',
        'user_type': 'client'
    }
}
```

### B. Reminder System Integration

```python
# services/reminders/reminder_scheduler.py
class ReminderScheduler:
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service

    def schedule_habit_reminders(self) -> Dict:
        """Send habit reminders based on scheduled times"""

    def schedule_workout_reminders(self) -> Dict:
        """Send workout reminders based on scheduled times"""

    def schedule_assessment_reminders(self) -> Dict:
        """Send assessment reminders for due/overdue assessments"""

    def send_progress_updates_to_trainers(self) -> Dict:
        """Send weekly progress summaries to trainers"""
```

### C. WhatsApp Flow Integration

Create corresponding flows for each text input:

```
whatsapp_flows/
├── trainer_habit_create_flow.json
├── trainer_workout_create_flow.json
├── trainer_assessment_create_flow.json
├── client_habit_log_flow.json
├── client_workout_log_flow.json
└── client_assessment_complete_flow.json
```

---

## Implementation Timeline

### **Phase 1: Enhanced Habit System (Week 1-2)**

1. ✅ Create habit text input JSON configurations
2. ✅ Develop HabitManager and HabitTextHandler classes
3. ✅ Enhance database schema for habit assignments
4. ✅ Add AI intents for habit operations
5. ✅ Create habit reminder system
6. ✅ Test habit creation, assignment, and logging

### **Phase 2: Workout Management System (Week 2-3)**

1. ✅ Create workout text input JSON configurations
2. ✅ Develop WorkoutManager and WorkoutTextHandler classes
3. ✅ Enhance database schema for workout assignments and logs
4. ✅ Add AI intents for workout operations
5. ✅ Create workout reminder system
6. ✅ Test workout creation, assignment, and logging

### **Phase 3: Assessment System with Photos (Week 3-4)**

1. ✅ Create assessment text input JSON configurations
2. ✅ Develop AssessmentManager and PhotoHandler classes
3. ✅ Enhance database schema for assessments and photos
4. ✅ Implement Supabase photo storage integration
5. ✅ Add AI intents for assessment operations
6. ✅ Create assessment reminder system
7. ✅ Test assessment creation, assignment, and completion

### **Phase 4: Integration & Testing (Week 4-5)**

1. ✅ Integrate all systems with existing AI and WhatsApp handlers
2. ✅ Create comprehensive reminder scheduler
3. ✅ Add progress tracking and analytics
4. ✅ Create corresponding WhatsApp flows
5. ✅ End-to-end testing of all features
6. ✅ Performance optimization and bug fixes

---

## Success Metrics

### **Habit Management**

- ✅ Trainers can create habits via text and flow
- ✅ Habits can be assigned to clients using user IDs
- ✅ Clients receive reminders and can log completion
- ✅ Progress tracking and streak monitoring

### **Workout Management**

- ✅ Trainers can create detailed workouts via text and flow
- ✅ Workouts can be assigned and scheduled for clients
- ✅ Clients can log workout completion with details
- ✅ Workout analytics and progress tracking

### **Assessment Management**

- ✅ Trainers can create custom assessments with photos
- ✅ Assessments can be assigned with due dates
- ✅ Clients can complete assessments and upload photos
- ✅ Photo storage and assessment analytics

This comprehensive plan follows your established patterns while adding the three major features you requested. Each system is designed to work seamlessly with your existing AI, privacy, and user ID systems.
