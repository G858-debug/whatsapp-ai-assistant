"""
Comprehensive Phase 3 Integration Verification
Checks all commands, flows, and integrations
"""

import json

def verify_phase3_integration():
    """Verify all Phase 3 components are properly integrated"""
    
    print("="*60)
    print("PHASE 3 INTEGRATION VERIFICATION")
    print("="*60)
    
    issues = []
    warnings = []
    
    # 1. Verify command_handlers.json
    print("\n1. Checking command_handlers.json...")
    try:
        with open('config/command_handlers.json', 'r') as f:
            config = json.load(f)
        
        # Check trainer commands
        trainer_commands = config.get('trainer_commands', {})
        expected_trainer = [
            '/create-habit', '/edit-habit', '/delete-habit', '/assign-habit',
            '/view-habits', '/view-trainee-progress', '/trainee-weekly-report',
            '/trainee-monthly-report'
        ]
        
        for cmd in expected_trainer:
            if cmd in trainer_commands:
                print(f"   ✓ {cmd} defined")
            else:
                issues.append(f"Missing trainer command: {cmd}")
        
        # Check client commands
        client_commands = config.get('client_commands', {})
        expected_client = [
            '/view-my-habits', '/log-habits', '/view-progress',
            '/weekly-report', '/monthly-report'
        ]
        
        for cmd in expected_client:
            if cmd in client_commands:
                print(f"   ✓ {cmd} defined")
            else:
                issues.append(f"Missing client command: {cmd}")
        
        # Check task types
        task_types = config.get('task_types', {})
        expected_tasks = [
            'create_habit', 'edit_habit', 'delete_habit', 'assign_habit',
            'view_trainee_progress', 'trainee_report', 'log_habits',
            'view_progress', 'weekly_report', 'monthly_report'
        ]
        
        for task in expected_tasks:
            if task in task_types:
                print(f"   ✓ {task} task type defined")
            else:
                issues.append(f"Missing task type: {task}")
        
        print("   ✓ command_handlers.json is valid")
        
    except Exception as e:
        issues.append(f"Error reading command_handlers.json: {e}")
    
    # 2. Verify imports
    print("\n2. Checking imports...")
    try:
        from services.habits import HabitService, AssignmentService, LoggingService, ReportService
        print("   ✓ Phase 3 services import successfully")
        
        from services.habits import HabitTrackingService
        print("   ✓ Legacy HabitTrackingService available")
        
        from services.commands.trainer_habit_commands import (
            handle_create_habit, handle_edit_habit, handle_delete_habit,
            handle_assign_habit, handle_view_habits, handle_view_trainee_progress,
            handle_trainee_report
        )
        print("   ✓ Trainer habit commands import successfully")
        
        from services.commands.client_habit_commands import (
            handle_view_my_habits, handle_log_habits, handle_view_progress,
            handle_weekly_report, handle_monthly_report
        )
        print("   ✓ Client habit commands import successfully")
        
        from services.flows.trainer_habit_flows import TrainerHabitFlows
        from services.flows.client_habit_flows import ClientHabitFlows
        print("   ✓ Phase 3 flow handlers import successfully")
        
    except ImportError as e:
        issues.append(f"Import error: {e}")
    
    # 3. Verify message_router integration
    print("\n3. Checking message_router.py integration...")
    try:
        with open('services/message_router.py', 'r', encoding='utf-8') as f:
            router_content = f.read()
        
        # Check command handlers
        phase3_commands = [
            'handle_create_habit', 'handle_edit_habit', 'handle_delete_habit',
            'handle_assign_habit', 'handle_view_habits', 'handle_view_trainee_progress',
            'handle_trainee_report', 'handle_view_my_habits', 'handle_log_habits',
            'handle_view_progress', 'handle_weekly_report', 'handle_monthly_report'
        ]
        
        for cmd in phase3_commands:
            if cmd in router_content:
                print(f"   ✓ {cmd} in message_router")
            else:
                issues.append(f"Missing in message_router: {cmd}")
        
        # Check flow handlers
        phase3_flows = [
            'continue_create_habit', 'continue_edit_habit', 'continue_delete_habit',
            'continue_assign_habit', 'continue_view_trainee_progress', 'continue_trainee_report',
            'continue_log_habits', 'continue_view_progress', 'continue_weekly_report',
            'continue_monthly_report'
        ]
        
        for flow in phase3_flows:
            if flow in router_content:
                print(f"   ✓ {flow} in message_router")
            else:
                issues.append(f"Missing flow in message_router: {flow}")
        
        # Check button handlers
        button_handlers = ['register_trainer', 'register_client', 'login_trainer', 'login_client']
        for btn in button_handlers:
            if f"button_id == '{btn}'" in router_content:
                print(f"   ✓ {btn} button handler present")
            else:
                warnings.append(f"Button handler may be missing: {btn}")
        
    except Exception as e:
        issues.append(f"Error checking message_router: {e}")
    
    # 4. Verify file existence
    print("\n4. Checking file existence...")
    import os
    
    required_files = [
        'services/habits/__init__.py',
        'services/habits/habit_service.py',
        'services/habits/assignment_service.py',
        'services/habits/logging_service.py',
        'services/habits/report_service.py',
        'services/commands/trainer_habit_commands.py',
        'services/commands/client_habit_commands.py',
        'services/flows/trainer_habit_flows.py',
        'services/flows/client_habit_flows.py',
        'config/habit_creation_inputs.json',
        'database_updates/phase3_habits_schema.sql'
    ]
    
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"   ✓ {filepath}")
        else:
            issues.append(f"Missing file: {filepath}")
    
    # 5. Verify help command
    print("\n5. Checking help command...")
    try:
        with open('services/commands/help_command.py', 'r', encoding='utf-8') as f:
            help_content = f.read()
        
        if 'Phase 3' in help_content or '/create-habit' in help_content:
            print("   ✓ Help command includes Phase 3 features")
        else:
            warnings.append("Help command may not include Phase 3 features")
        
    except Exception as e:
        warnings.append(f"Could not verify help command: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    if not issues and not warnings:
        print("\n✅ ALL CHECKS PASSED!")
        print("\nPhase 3 is fully integrated and ready for testing.")
        return True
    else:
        if issues:
            print(f"\n❌ FOUND {len(issues)} ISSUE(S):")
            for issue in issues:
                print(f"   • {issue}")
        
        if warnings:
            print(f"\n⚠️  FOUND {len(warnings)} WARNING(S):")
            for warning in warnings:
                print(f"   • {warning}")
        
        return False


if __name__ == "__main__":
    success = verify_phase3_integration()
    exit(0 if success else 1)
