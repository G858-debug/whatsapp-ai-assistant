# tests/apply_fixes.py
"""
Apply generated fixes to the codebase
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List
import shutil
from datetime import datetime


class FixApplier:
    """Applies generated fixes to code files"""
    
    def __init__(self):
        self.fixes = self.load_fixes()
        self.backup_dir = f"backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.applied_fixes = []
        self.failed_fixes = []
    
    def load_fixes(self) -> List[Dict]:
        """Load fixes from generated file"""
        try:
            with open('generated_fixes.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("No fixes found")
            return []
    
    def create_backup(self, file_path: str):
        """Create backup of file before modifying"""
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Copy file to backup
        if os.path.exists(file_path):
            backup_path = os.path.join(self.backup_dir, 
                                      os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"Backed up {file_path}")
    
    def apply_fix(self, fix: Dict) -> bool:
        """Apply a single fix to a file"""
        
        file_path = fix.get('file')
        line_no = fix.get('line', 0)
        fixed_code = fix.get('fixed_code', '')
        original_code = fix.get('original_code', '')
        
        if not file_path or not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
        
        # Create backup
        self.create_backup(file_path)
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Apply fix based on type
            if fix['type'] == 'currency_parsing':
                success = self.apply_currency_fix(file_path, lines, fix)
            elif fix['type'] == 'registration_save':
                success = self.apply_registration_fix(file_path, lines, fix)
            elif fix['type'] == 'rigid_commands':
                success = self.apply_ai_priority_fix(file_path, lines, fix)
            elif fix['type'] == 'null_value':
                success = self.apply_null_check_fix(file_path, lines, fix)
            else:
                success = self.apply_generic_fix(file_path, lines, line_no, 
                                                fixed_code)
            
            if success:
                print(f"✅ Applied fix to {file_path}:{line_no}")
                self.applied_fixes.append(fix)
            else:
                print(f"❌ Failed to apply fix to {file_path}:{line_no}")
                self.failed_fixes.append(fix)
            
            return success
            
        except Exception as e:
            print(f"Error applying fix: {str(e)}")
            self.failed_fixes.append(fix)
            return False
    
    def apply_currency_fix(self, file_path: str, lines: List[str], 
                          fix: Dict) -> bool:
        """Apply currency parsing fix"""
        
        # Find the line that needs fixing
        for i, line in enumerate(lines):
            if 'pricing' in line and ('=' in line or 'insert' in line):
                # Check if it's already parsing currency
                if 're.sub' in line or '_parse_currency' in line:
                    continue
                
                # Apply the fix
                indent = len(line) - len(line.lstrip())
                
                # Add import if needed
                if 'import re' not in ''.join(lines[:20]):
                    lines.insert(0, 'import re\n')
                
                # Replace the line
                new_code = ' ' * indent + fix['fixed_code'].strip() + '\n'
                lines[i] = new_code
                
                # Save file
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                
                return True
        
        return False
    
    def apply_registration_fix(self, file_path: str, lines: List[str], 
                               fix: Dict) -> bool:
        """Apply registration save fix"""
        
        # Find the complete_registration method
        for i, line in enumerate(lines):
            if 'def _complete_registration' in line or 'def complete_registration' in line:
                # Find where trainer_data is being built
                for j in range(i, min(i + 50, len(lines))):
                    if 'trainer_data = {' in lines[j]:
                        # Check if pricing is already being parsed
                        for k in range(j, min(j + 20, len(lines))):
                            if 'pricing_per_session' in lines[k]:
                                if 'parse' not in lines[k] and 'float' not in lines[k]:
                                    # Fix the pricing line
                                    lines[k] = re.sub(
                                        r"'pricing_per_session':\s*data\.get\('pricing'[^,]*\),?",
                                        "'pricing_per_session': self._parse_currency(data.get('pricing', 400)),",
                                        lines[k]
                                    )
                                    
                                    # Add the parse method if not exists
                                    self.add_parse_currency_method(lines, i)
                                    
                                    # Save file
                                    with open(file_path, 'w') as f:
                                        f.writelines(lines)
                                    
                                    return True
        
        return False
    
    def add_parse_currency_method(self, lines: List[str], class_start: int):
        """Add currency parsing method to class"""
        
        # Check if method already exists
        for line in lines:
            if 'def _parse_currency' in line:
                return
        
        # Find end of class or good insertion point
        indent = '    '
        method_code = f'''
{indent}def _parse_currency(self, value):
{indent}    """Parse currency value to numeric"""
{indent}    if isinstance(value, (int, float)):
{indent}        return value
{indent}    import re
{indent}    cleaned = re.sub(r'[^\\d.]', '', str(value))
{indent}    return float(cleaned) if cleaned else 400

'''
        
        # Find a good place to insert (before the last method)
        for i in range(len(lines) - 1, class_start, -1):
            if lines[i].strip() and not lines[i].strip().startswith('#'):
                lines.insert(i + 1, method_code)
                break
    
    def apply_ai_priority_fix(self, file_path: str, lines: List[str], 
                              fix: Dict) -> bool:
        """Apply fix to prioritize AI over rigid commands"""
        
        # Find the handle_message method
        for i, line in enumerate(lines):
            if 'def handle_message' in line:
                # Look for command checking logic
                for j in range(i, min(i + 100, len(lines))):
                    if 'if text' in lines[j] and 'COMMANDS' in lines[j]:
                        # Found rigid command checking
                        # Replace with AI-first approach
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        
                        # Insert AI handling before command check
                        ai_code = f'''
{' ' * indent}# Try AI understanding first
{' ' * indent}try:
{' ' * (indent + 4)}ai_response = self.ai_handler.understand_message(
{' ' * (indent + 8)}message=text,
{' ' * (indent + 8)}sender_type='trainer' if trainer else 'client',
{' ' * (indent + 8)}sender_data=user_data,
{' ' * (indent + 8)}conversation_history=[]
{' ' * (indent + 4)})
{' ' * (indent + 4)}
{' ' * (indent + 4)}if ai_response.get('confidence', 0) > 0.6:
{' ' * (indent + 8)}return ai_response
{' ' * indent}except Exception as e:
{' ' * (indent + 4)}log_error(f"AI handler error: {{str(e)}}")
{' ' * indent}
'''
                        lines.insert(j, ai_code)
                        
                        # Save file
                        with open(file_path, 'w') as f:
                            f.writelines(lines)
                        
                        return True
        
        return False
    
    def apply_null_check_fix(self, file_path: str, lines: List[str], 
                             fix: Dict) -> bool:
        """Apply null check fix"""
        
        line_no = fix.get('line', 0)
        if line_no > 0 and line_no <= len(lines):
            # Add null check before the problematic line
            indent = len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())
            
            null_check = f"{' ' * indent}{fix['fixed_code']}\n"
            lines.insert(line_no - 1, null_check)
            
            # Save file
            with open(file_path, 'w') as f:
                f.writelines(lines)
            
            return True
        
        return False
    
    def apply_generic_fix(self, file_path: str, lines: List[str], 
                         line_no: int, fixed_code: str) -> bool:
        """Apply generic fix by replacing line"""
        
        if line_no > 0 and line_no <= len(lines):
            # Replace the line
            indent = len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())
            lines[line_no - 1] = ' ' * indent + fixed_code.strip() + '\n'
            
            # Save file
            with open(file_path, 'w') as f:
                f.writelines(lines)
            
            return True
        
        return False
    
    def apply_all_fixes(self):
        """Apply all generated fixes"""
        
        if not self.fixes:
            print("No fixes to apply")
            return
        
        print(f"Applying {len(self.fixes)} fixes...")
        
        for fix in self.fixes:
            self.apply_fix(fix)
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate summary of applied fixes"""
        
        summary = {
            'total_fixes': len(self.fixes),
            'applied': len(self.applied_fixes),
            'failed': len(self.failed_fixes),
            'backup_location': self.backup_dir,
            'applied_fixes': [
                {
                    'file': f['file'],
                    'line': f['line'],
                    'type': f['type'],
                    'diagnosis': f['diagnosis']
                }
                for f in self.applied_fixes
            ],
            'failed_fixes': [
                {
                    'file': f['file'],
                    'line': f['line'],
                    'error': f['error'][:100]
                }
                for f in self.failed_fixes
            ]
        }
        
        with open('fix_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Applied {len(self.applied_fixes)} fixes")
        print(f"❌ Failed {len(self.failed_fixes)} fixes")
        print(f"📁 Backups saved to {self.backup_dir}")
    
    def rollback(self):
        """Rollback all changes using backups"""
        
        if not os.path.exists(self.backup_dir):
            print("No backup found")
            return
        
        for backup_file in os.listdir(self.backup_dir):
            backup_path = os.path.join(self.backup_dir, backup_file)
            
            # Find original file location
            for fix in self.applied_fixes:
                if os.path.basename(fix['file']) == backup_file:
                    shutil.copy2(backup_path, fix['file'])
                    print(f"Rolled back {fix['file']}")
                    break


if __name__ == "__main__":
    applier = FixApplier()
    applier.apply_all_fixes()

if __name__ == "__main__":
    applier = FixApplier()
    
    if not applier.fixes:
        print("⚠️ No fixes to apply")
        sys.exit(1)
    
    applier.apply_all_fixes()
    
    # Verify changes were made
    import subprocess
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True)
    
    if result.stdout.strip():
        print(f"✅ Files changed:\n{result.stdout}")
        sys.exit(0)
    else:
        print("❌ No files were changed")
        sys.exit(1)
