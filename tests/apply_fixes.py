#!/usr/bin/env python3
"""
Improved Apply Fixes Script - Better pattern matching and fix application
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil
from datetime import datetime


class ImprovedFixApplier:
    """Enhanced fix applier with better pattern matching"""
    
    def __init__(self):
        self.fixes = self.load_fixes()
        self.backup_dir = f"backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.applied_fixes = []
        self.failed_fixes = []
        self.verbose = True  # For debugging
    
    def load_fixes(self) -> List[Dict]:
        """Load fixes from generated file"""
        try:
            with open('generated_fixes.json', 'r') as f:
                fixes = json.load(f)
                print(f"📥 Loaded {len(fixes)} fixes from generated_fixes.json")
                return fixes
        except FileNotFoundError:
            print("❌ No generated_fixes.json found")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing generated_fixes.json: {e}")
            return []
    
    def create_backup(self, file_path: str):
        """Create backup of file before modifying"""
        os.makedirs(self.backup_dir, exist_ok=True)
        
        if os.path.exists(file_path):
            backup_path = os.path.join(self.backup_dir, 
                                      os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"💾 Backed up {file_path}")
            return True
        return False
    
    def find_insertion_point(self, lines: List[str], after_pattern: str, 
                           class_name: Optional[str] = None) -> Optional[int]:
        """Find where to insert code based on patterns"""
        for i, line in enumerate(lines):
            if after_pattern in line:
                # If we're looking for a class method, ensure we're in the right class
                if class_name:
                    # Search backwards to find the class definition
                    for j in range(i, -1, -1):
                        if f'class {class_name}' in lines[j]:
                            # We're in the right class
                            return i
                else:
                    return i
        return None
    
    def find_method_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a method definition"""
        if start_idx >= len(lines):
            return start_idx
        
        # Get the indentation of the method definition
        method_line = lines[start_idx]
        base_indent = len(method_line) - len(method_line.lstrip())
        
        # Find where the method ends
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Non-empty line
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= base_indent:
                    # Found a line at same or lower indentation
                    return i
        
        # If we reach the end of file
        return len(lines)
    
    def apply_duplicate_check_fix(self, fix: Dict, file_path: str, content: str) -> Tuple[bool, str]:
        """Apply duplicate registration check fix"""
        print(f"  🔍 Applying duplicate check fix to {file_path}")
        
        lines = content.split('\n')
        
        # Look for the start_registration method
        insert_idx = None
        for i, line in enumerate(lines):
            if 'def start_registration' in line or 'def handle_registration' in line:
                # Find the first line after the method definition
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith('"""'):
                        insert_idx = j
                        break
                break
        
        if insert_idx:
            # Get proper indentation
            indent = '        '  # Standard method indentation
            check_code = fix.get('check_code', '').replace('\n', f'\n{indent}')
            
            # Insert the duplicate check
            lines.insert(insert_idx, f'{indent}# Check for existing registration')
            lines.insert(insert_idx + 1, check_code)
            
            print(f"  ✅ Added duplicate check at line {insert_idx}")
            return True, '\n'.join(lines)
        
        print(f"  ⚠️ Could not find registration method")
        return False, content
    
    def apply_phone_format_fix(self, fix: Dict, file_path: str, content: str) -> Tuple[bool, str]:
        """Apply phone number format fix"""
        print(f"  🔍 Applying phone format fix to {file_path}")
        
        # Look for the return statement with phone number
        patterns = [
            (r"return True, f'\+\{phone_digits\}', None", "return True, phone_digits, None"),
            (r"return True, f\"\+\{phone_digits\}\", None", "return True, phone_digits, None"),
            (r"return.*\+.*phone", "return True, phone_digits, None"),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                modified = True
                print(f"  ✅ Fixed phone number format")
                break
        
        if not modified:
            print(f"  ⚠️ Phone format pattern not found")
        
        return modified, content
    
    def apply_ai_intent_fix(self, fix: Dict, file_path: str, content: str) -> Tuple[bool, str]:
        """Apply AI intent recognition fix"""
        print(f"  🔍 Applying AI intent fix to {file_path}")
        
        lines = content.split('\n')
        
        # Find where to add the command patterns
        insert_idx = None
        for i, line in enumerate(lines):
            if 'def analyze_intent' in line or 'def process_message' in line:
                # Insert after the method definition
                insert_idx = i + 1
                break
        
        if insert_idx and fix.get('pattern_code'):
            indent = '        '
            pattern_code = fix['pattern_code'].replace('\n', f'\n{indent}')
            
            # Check if patterns already exist
            if 'command_patterns' not in content:
                lines.insert(insert_idx, pattern_code)
                print(f"  ✅ Added command patterns")
                return True, '\n'.join(lines)
        
        print(f"  ⚠️ Could not add AI patterns")
        return False, content
    
    def apply_client_registration_fix(self, fix: Dict, file_path: str, content: str) -> Tuple[bool, str]:
        """Apply client registration welcome message fix"""
        print(f"  🔍 Applying client registration fix to {file_path}")
        
        # Look for the return statement in registration completion
        if 'return {' in content and 'success' in content:
            # Find and enhance the return statement
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'return {' in line and i + 1 < len(lines):
                    # Check if it's a success return
                    if '"success": True' in lines[i+1] or "'success': True" in lines[i+1]:
                        # Add or update the message
                        message_found = False
                        for j in range(i, min(i + 5, len(lines))):
                            if 'message' in lines[j]:
                                # Update existing message
                                lines[j] = re.sub(
                                    r'["\']message["\']\s*:\s*["\'].*?["\']',
                                    '"message": f"Great! {client_name} has been added as your client."',
                                    lines[j]
                                )
                                message_found = True
                                break
                        
                        if not message_found:
                            # Add message line
                            indent = '            '
                            lines.insert(i + 2, f'{indent}"message": f"Great! {{client_name}} has been added as your client.",')
                        
                        print(f"  ✅ Fixed client welcome message")
                        return True, '\n'.join(lines)
        
        print(f"  ⚠️ Could not fix client message")
        return False, content
    
    def apply_missing_method_fix(self, fix: Dict, file_path: str, content: str) -> Tuple[bool, str]:
        """Add missing methods like validate_time_format"""
        print(f"  🔍 Adding missing method to {file_path}")
        
        if fix.get('method_code'):
            method_name = re.search(r'def (\w+)', fix['method_code'])
            if method_name:
                method_name = method_name.group(1)
                
                # Check if method already exists
                if f'def {method_name}' not in content:
                    lines = content.split('\n')
                    
                    # Find a good place to add the method (after __init__ or at end of class)
                    insert_idx = None
                    for i, line in enumerate(lines):
                        if 'def __init__' in line:
                            # Find the end of __init__
                            end_idx = self.find_method_end(lines, i)
                            insert_idx = end_idx
                            break
                    
                    if insert_idx:
                        # Add the method
                        lines.insert(insert_idx, '')
                        lines.insert(insert_idx + 1, fix['method_code'])
                        
                        print(f"  ✅ Added method {method_name}")
                        return True, '\n'.join(lines)
        
        print(f"  ⚠️ Could not add missing method")
        return False, content
    
    def apply_fix(self, fix: Dict) -> bool:
        """Apply a single fix to a file"""
        file_path = fix.get('file')
        
        if not file_path:
            print(f"❌ No file path in fix: {fix}")
            self.failed_fixes.append(fix)
            return False
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            self.failed_fixes.append(fix)
            return False
        
        # Create backup
        if not self.create_backup(file_path):
            print(f"❌ Could not backup {file_path}")
            self.failed_fixes.append(fix)
            return False
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            modified = False
            
            # Apply fix based on type
            fix_type = fix.get('type')
            print(f"\n📝 Processing {fix_type} fix for {file_path}")
            
            if fix_type == 'duplicate_check':
                modified, content = self.apply_duplicate_check_fix(fix, file_path, content)
            
            elif fix_type == 'phone_format':
                modified, content = self.apply_phone_format_fix(fix, file_path, content)
            
            elif fix_type == 'ai_intent':
                modified, content = self.apply_ai_intent_fix(fix, file_path, content)
            
            elif fix_type == 'client_registration':
                modified, content = self.apply_client_registration_fix(fix, file_path, content)
            
            elif fix_type == 'trainer_recognition':
                # Similar to duplicate check
                modified, content = self.apply_duplicate_check_fix(fix, file_path, content)
            
            elif fix_type == 'missing_method':
                modified, content = self.apply_missing_method_fix(fix, file_path, content)
            
            elif fix_type == 'currency_parsing':
                # Add the currency parsing method and update calls
                if '_parse_currency' not in content:
                    # Add the method
                    currency_method = '''
    def _parse_currency(self, value):
        """Parse currency value to numeric"""
        if isinstance(value, (int, float)):
            return value
        
        import re
        # Remove R, spaces, commas
        cleaned = re.sub(r'[Rr,\\s]', '', str(value))
        # Remove any text like "per session"
        cleaned = re.sub(r'per.*', '', cleaned, flags=re.IGNORECASE)
        
        try:
            return float(cleaned) if cleaned else 400
        except:
            return 400  # Default value
'''
                    lines = content.split('\n')
                    # Find where to add it
                    for i, line in enumerate(lines):
                        if 'def __init__' in line:
                            end_idx = self.find_method_end(lines, i)
                            lines.insert(end_idx, currency_method)
                            content = '\n'.join(lines)
                            modified = True
                            break
                
                # Update pricing calls
                if modified or '_parse_currency' in content:
                    content = re.sub(
                        r"'pricing_per_session':\s*data\.get\('pricing',\s*\d+\)",
                        "'pricing_per_session': self._parse_currency(data.get('pricing', 300))",
                        content
                    )
                    print(f"  ✅ Added currency parsing")
            
            # Write the modified content if changed
            if modified and content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Successfully applied {fix_type} fix to {file_path}")
                self.applied_fixes.append(fix)
                return True
            else:
                print(f"⚠️ No changes made to {file_path}")
                self.failed_fixes.append(fix)
                return False
            
        except Exception as e:
            print(f"❌ Error applying fix: {str(e)}")
            self.failed_fixes.append(fix)
            return False
    
    def apply_all_fixes(self):
        """Apply all generated fixes"""
        if not self.fixes:
            print("❌ No fixes to apply")
            return False
        
        print(f"\n🔧 Starting to apply {len(self.fixes)} fixes...\n")
        print("=" * 60)
        
        for i, fix in enumerate(self.fixes, 1):
            print(f"\n[{i}/{len(self.fixes)}] Applying fix...")
            self.apply_fix(fix)
            print("-" * 40)
        
        # Generate summary
        self.generate_summary()
        
        print("\n" + "=" * 60)
        print(f"📊 Summary:")
        print(f"  ✅ Applied: {len(self.applied_fixes)} fixes")
        print(f"  ❌ Failed: {len(self.failed_fixes)} fixes")
        
        return len(self.applied_fixes) > 0
    
    def generate_summary(self):
        """Generate summary of applied fixes"""
        summary = {
            'total_fixes': len(self.fixes),
            'applied': len(self.applied_fixes),
            'failed': len(self.failed_fixes),
            'applied_fixes': self.applied_fixes,
            'failed_fixes': self.failed_fixes,
            'timestamp': datetime.now().isoformat()
        }
        
        with open('fix_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📝 Summary saved to fix_summary.json")


if __name__ == "__main__":
    import sys
    
    print("🚀 Refiloe Auto-Fix Applier v2.0")
    print("=" * 60)
    
    applier = ImprovedFixApplier()
    success = applier.apply_all_fixes()
    
    sys.exit(0 if success else 1)
