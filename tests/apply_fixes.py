#!/usr/bin/env python3
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
        os.makedirs(self.backup_dir, exist_ok=True)
        
        if os.path.exists(file_path):
            backup_path = os.path.join(self.backup_dir, 
                                      os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"Backed up {file_path}")
    
    def add_parse_currency_method(self, file_path: str):
        """Add the _parse_currency method if it doesn't exist"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        if '_parse_currency' not in content:
            # Find the class definition
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'class TrainerRegistrationHandler' in line:
                    # Find the __init__ method
                    for j in range(i, min(i+50, len(lines))):
                        if 'def __init__' in lines[j]:
                            # Find the end of __init__
                            indent_count = len(lines[j]) - len(lines[j].lstrip())
                            for k in range(j+1, len(lines)):
                                if lines[k].strip() and not lines[k].startswith(' ' * (indent_count + 4)):
                                    # Insert the method here
                                    method_code = '''
    def _parse_currency(self, value):
        """Parse currency value to numeric"""
        if isinstance(value, (int, float)):
            return value
        
        import re
        # Remove R, spaces, commas
        cleaned = re.sub(r'[Rr,\s]', '', str(value))
        # Remove any text like "per session"
        cleaned = re.sub(r'per.*', '', cleaned, flags=re.IGNORECASE)
        
        try:
            return float(cleaned) if cleaned else 400
        except:
            return 400  # Default value
'''
                                    lines.insert(k, method_code)
                                    content = '\n'.join(lines)
                                    with open(file_path, 'w') as f:
                                        f.write(content)
                                    return True
        return False
    
    def apply_fix(self, fix: Dict) -> bool:
        """Apply a single fix to a file"""
        
        file_path = fix.get('file')
        
        if not file_path or not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
        
        # Create backup
        self.create_backup(file_path)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            modified = False
            
            # Apply different fix types
            if fix.get('search_pattern') and fix.get('fixed_code'):
                # Simple replacement
                if fix['search_pattern'] in content:
                    content = content.replace(fix['search_pattern'], fix['fixed_code'])
                    modified = True
                    
                    # For currency parsing, also add the method
                    if fix['type'] == 'currency_parsing':
                        self.add_parse_currency_method(file_path)
            
            elif fix.get('add_method') and fix.get('method_code'):
                # Add a new method
                if 'validate_time_format' not in content:
                    # Find a good place to add the method
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'def validate_time(' in line:
                            # Add after this method
                            for j in range(i+1, len(lines)):
                                if lines[j].strip() and not lines[j].startswith(' '):
                                    lines.insert(j, fix['method_code'])
                                    content = '\n'.join(lines)
                                    modified = True
                                    break
                            break
            
            elif fix.get('add_check') and fix.get('check_code'):
                # Add duplicate check
                if 'already registered' not in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'def start_registration' in line:
                            # Add check at the beginning of the method
                            lines.insert(i+2, fix['check_code'])
                            content = '\n'.join(lines)
                            modified = True
                            break
            
            if modified:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Applied fix to {file_path}")
                self.applied_fixes.append(fix)
                return True
            else:
                print(f"⚠️ Could not apply fix to {file_path}")
                self.failed_fixes.append(fix)
                return False
            
        except Exception as e:
            print(f"Error applying fix: {str(e)}")
            self.failed_fixes.append(fix)
            return False
    
    def apply_all_fixes(self):
        """Apply all generated fixes"""
        
        if not self.fixes:
            print("No fixes to apply")
            return False
        
        print(f"Applying {len(self.fixes)} fixes...")
        
        for fix in self.fixes:
            self.apply_fix(fix)
        
        # Generate summary
        self.generate_summary()
        
        return len(self.applied_fixes) > 0
    
    def generate_summary(self):
        """Generate summary of applied fixes"""
        
        summary = {
            'total_fixes': len(self.fixes),
            'applied': len(self.applied_fixes),
            'failed': len(self.failed_fixes),
            'applied_fixes': self.applied_fixes,
            'failed_fixes': self.failed_fixes
        }
        
        with open('fix_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Applied {len(self.applied_fixes)} fixes")
        print(f"❌ Failed {len(self.failed_fixes)} fixes")


if __name__ == "__main__":
    import sys
    applier = FixApplier()
    success = applier.apply_all_fixes()
    sys.exit(0 if success else 1)
