"""
Test script to verify all imports work correctly
"""
import sys
import traceback

def test_import(module_path, item_name=None):
    """Test importing a module or item from a module"""
    try:
        if item_name:
            print(f"✓ Testing: from {module_path} import {item_name}")
            module = __import__(module_path, fromlist=[item_name])
            item = getattr(module, item_name)
            print(f"  ✅ SUCCESS: {item}")
        else:
            print(f"✓ Testing: import {module_path}")
            module = __import__(module_path)
            print(f"  ✅ SUCCESS: {module}")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {str(e)}")
        print(f"  Traceback: {traceback.format_exc()}")
        return False

print("=" * 60)
print("TESTING IMPORTS")
print("=" * 60)

# Test 1: Profile commands
print("\n1. Testing profile_commands imports:")
test_import("services.commands.common.profile_commands", "handle_view_profile")
test_import("services.commands.common.profile_commands", "handle_edit_profile")
test_import("services.commands.common.profile_commands", "handle_delete_account")

# Test 2: Commands __init__
print("\n2. Testing services.commands imports:")
test_import("services.commands", "handle_view_profile")
test_import("services.commands", "handle_edit_profile")
test_import("services.commands", "handle_delete_account")

# Test 3: ProfileViewer
print("\n3. Testing ProfileViewer import:")
test_import("services.profile_viewer", "ProfileViewer")

# Test 4: Common commands handler
print("\n4. Testing CommonCommandHandler:")
test_import("services.message_router.handlers.commands.common_commands", "CommonCommandHandler")

# Test 5: Role command handler
print("\n5. Testing RoleCommandHandler:")
test_import("services.message_router.handlers.commands.role_command_handler", "RoleCommandHandler")

# Test 6: Logged in user handler
print("\n6. Testing LoggedInUserHandler:")
test_import("services.message_router.handlers.logged_in_user_handler", "LoggedInUserHandler")

print("\n" + "=" * 60)
print("IMPORT TEST COMPLETE")
print("=" * 60)
