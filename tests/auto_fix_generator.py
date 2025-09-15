# tests/auto_fix_generator.py
"""
Auto-Fix Generator for Refiloe
Analyzes test failures and generates automated fixes
"""

import json
import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import ast
import traceback


class AutoFixGenerator:
    """Generates fixes for common test failures"""
    
    def __init__(self):
        self.test_results = self.load_test_results()
        self.fixes = []
        self.fix_patterns = self.load_fix_patterns()
    
    def load_test_results(self) -> Dict:
        """Load test results from pytest json report"""
        try:
            with open('test-results.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("No test results found")
            return {}
    
    def load_fix_patterns(self) -> Dict:
        """Load common error patterns and their fixes"""
        return {
            # Database errors
            r"invalid input syntax for type numeric.*['\"]R?(\d+)['\"]": {
                "type": "currency_parsing",
                "diagnosis": "Trying to save currency string in numeric field",
                "fix_template": """
# Extract numeric value from currency string
import re
price_text = re.sub(r'[^\\d.]', '', {variable})
{target} = float(price_text) if price_text else {default}
"""
            },
            
            r"column .* cannot be null": {
                "type": "null_value",
                "diagnosis": "Required field is missing",
                "fix_template": """
# Ensure field has a value
if not {variable}:
    {variable} = {default}
"""
            },
            
            r"duplicate key value violates unique constraint": {
                "type": "duplicate",
                "diagnosis": "Trying to create duplicate record",
                "fix_template": """
# Check if record exists before creating
existing = self.db.table('{table}').select('*').eq('{field}', {value}).execute()
if existing.data and len(existing.data) > 0:
    # Update existing instead of creating new
    result = self.db.table('{table}').update(data).eq('{field}', {value}).execute()
else:
    result = self.db.table('{table}').insert(data).execute()
"""
            },
            
            # Registration errors
            r"Error saving information|Error completing registration": {
                "type": "registration_save",
                "diagnosis": "Registration data not being saved correctly",
                "fix_template": """
# Ensure all data is properly formatted before saving
trainer_data = {{
    'whatsapp': phone,
    'name': data.get('name', ''),
    'business_name': data.get('business_name'),
    'email': data.get('email', ''),
    'specialization': data.get('specialization'),
    'years_experience': int(data.get('experience', 0)) if data.get('experience') else 0,
    'location': data.get('location'),
    'pricing_per_session': self._parse_currency(data.get('pricing', 400)),
    'status': 'active',
    'created_at': datetime.now(self.sa_tz).isoformat()
}}

def _parse_currency(self, value):
    '''Parse currency value to numeric'''
    if isinstance(value, (int, float)):
        return value
    import re
    cleaned = re.sub(r'[^\\d.]', '', str(value))
    return float(cleaned) if cleaned else 400
"""
            },
            
            # Natural language processing
            r"Invalid command|type 'help' for commands": {
                "type": "rigid_commands",
                "diagnosis": "System using rigid command matching instead of AI",
                "fix_template": """
# Use AI intent handler first, fall back to commands only if needed
try:
    # Try AI understanding first
    ai_response = self.ai_handler.understand_message(
        message=text,
        sender_type=sender_type,
        sender_data=user_data,
        conversation_history=self.get_recent_messages(phone)
    )
    
    if ai_response.get('confidence', 0) > 0.6:
        return ai_response
except Exception as e:
    log_error(f"AI handler error: {{str(e)}}")

# Only fall back to rigid commands if AI didn't understand
if text.lower() in self.COMMANDS:
    return self.handle_command(text.lower())

# Default to friendly response, not error
return {{
    'message': "I'm not sure what you mean. Could you rephrase that? Or type 'help' to see what I can do.",
    'success': True
}}
"""
            },
            
            # Step progression errors
            r"Step (\d+) of (\d+).*not progressing": {
                "type": "step_progression",
                "diagnosis": "Registration step not advancing correctly",
                "fix_template": """
# Ensure step increments after successful validation
if validated['valid']:
    data[field] = validated['value']
    self.save_session(phone, data, current_step + 1)  # Increment step
    return self.get_next_step_response(phone, current_step + 1, data)
"""
            }
        }
    
    def analyze_failure(self, test_failure: Dict) -> Optional[Dict]:
        """Analyze a test failure and generate fix"""
        
        test_name = test_failure.get('nodeid', '')
        error_message = test_failure.get('call', {}).get('longrepr', '')
        
        # Extract file and line number from traceback if available
        file_info = self.extract_file_info(error_message)
        
        # Match against known patterns
        for pattern, fix_info in self.fix_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return self.generate_fix(
                    test_name=test_name,
                    error_message=error_message,
                    fix_info=fix_info,
                    file_info=file_info
                )
        
        # If no pattern matches, try to generate generic fix
        return self.generate_generic_fix(test_name, error_message, file_info)
    
    def extract_file_info(self, error_message: str) -> Dict:
        """Extract file path and line number from error"""
        
        file_info = {}
        
        # Try to find file references in traceback
        file_pattern = r'File ["\'](.*?)["\'], line (\d+)'
        matches = re.findall(file_pattern, error_message)
        
        if matches:
            # Get the last match (usually the actual error location)
            file_path, line_no = matches[-1]
            file_info['file'] = file_path
            file_info['line'] = int(line_no)
            
            # Try to get the actual code at that line
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    if line_no <= len(lines):
                        file_info['code'] = lines[line_no - 1].strip()
                        # Get surrounding context
                        start = max(0, line_no - 3)
                        end = min(len(lines), line_no + 2)
                        file_info['context'] = ''.join(lines[start:end])
            except:
                pass
        
        return file_info
    
    def generate_fix(self, test_name: str, error_message: str, 
                     fix_info: Dict, file_info: Dict) -> Dict:
        """Generate a specific fix based on pattern"""
        
        fix = {
            'test': test_name,
            'error': error_message[:200],  # Truncate long errors
            'diagnosis': fix_info['diagnosis'],
            'type': fix_info['type'],
            'file': file_info.get('file', 'Unknown'),
            'line': file_info.get('line', 0),
            'original_code': file_info.get('code', ''),
            'fixed_code': self.apply_fix_template(
                fix_info['fix_template'],
                file_info,
                error_message
            )
        }
        
        return fix
    
    def apply_fix_template(self, template: str, file_info: Dict, 
                           error_message: str) -> str:
        """Apply fix template with context-specific values"""
        
        # Extract variable names and values from context
        context = file_info.get('context', '')
        
        # Smart replacements based on context
        replacements = {
            '{variable}': self.extract_variable_name(context),
            '{target}': self.extract_target_variable(context),
            '{default}': self.extract_default_value(error_message),
            '{table}': self.extract_table_name(error_message),
            '{field}': self.extract_field_name(error_message),
            '{value}': self.extract_value(context)
        }
        
        fixed_code = template
        for placeholder, value in replacements.items():
            fixed_code = fixed_code.replace(placeholder, value)
        
        return fixed_code
    
    def extract_variable_name(self, context: str) -> str:
        """Extract variable name from context"""
        # Look for common patterns
        patterns = [
            r"(\w+)\s*=\s*message",
            r"data\['(\w+)'\]",
            r"\.get\('(\w+)'"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        
        return "value"
    
    def extract_target_variable(self, context: str) -> str:
        """Extract target variable for assignment"""
        pattern = r"(\w+)\['(\w+)'\]\s*="
        match = re.search(pattern, context)
        if match:
            return f"{match.group(1)}['{match.group(2)}']"
        
        return "data['field']"
    
    def extract_default_value(self, error_message: str) -> str:
        """Extract appropriate default value based on error"""
        
        if 'numeric' in error_message or 'price' in error_message.lower():
            return "400"  # Default price
        elif 'email' in error_message.lower():
            return "''"
        elif 'name' in error_message.lower():
            return "'Guest'"
        
        return "None"
    
    def extract_table_name(self, error_message: str) -> str:
        """Extract table name from error"""
        
        patterns = [
            r"table[:\s]+['\"]?(\w+)['\"]?",
            r"INTO\s+(\w+)",
            r"FROM\s+(\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "table_name"
    
    def extract_field_name(self, error_message: str) -> str:
        """Extract field name from error"""
        
        patterns = [
            r"column[:\s]+['\"]?(\w+)['\"]?",
            r"field[:\s]+['\"]?(\w+)['\"]?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "field_name"
    
    def extract_value(self, context: str) -> str:
        """Extract value being used"""
        
        pattern = r"=\s*['\"]([^'\"]+)['\"]"
        match = re.search(pattern, context)
        if match:
            return f"'{match.group(1)}'"
        
        return "value"
    
    def generate_generic_fix(self, test_name: str, error_message: str, 
                            file_info: Dict) -> Dict:
        """Generate generic fix when no pattern matches"""
        
        return {
            'test': test_name,
            'error': error_message[:200],
            'diagnosis': "Unrecognized error pattern - needs manual review",
            'type': 'generic',
            'file': file_info.get('file', 'Unknown'),
            'line': file_info.get('line', 0),
            'original_code': file_info.get('code', ''),
            'fixed_code': """
# TODO: Manual fix needed
# Error: {error}
# Please review the error and apply appropriate fix
""".format(error=error_message[:100])
        }
    
    def process_all_failures(self):
        """Process all test failures and generate fixes"""
        
        if not self.test_results:
            print("No test results to process")
            return
        
        # Get failed tests
        failed_tests = [
            test for test in self.test_results.get('tests', [])
            if test.get('outcome') == 'failed'
        ]
        
        print(f"Found {len(failed_tests)} failed tests")
        
        for test in failed_tests:
            fix = self.analyze_failure(test)
            if fix:
                self.fixes.append(fix)
        
        # Save fixes to file
        self.save_fixes()
    
    def save_fixes(self):
        """Save generated fixes to file"""
        
        with open('generated_fixes.json', 'w') as f:
            json.dump(self.fixes, f, indent=2)
        
        print(f"Generated {len(self.fixes)} fixes")
        
        # Also create a human-readable report
        with open('fix_report.md', 'w') as f:
            f.write("# Auto-Generated Fixes\n\n")
            
            for i, fix in enumerate(self.fixes, 1):
                f.write(f"## Fix {i}: {fix['test']}\n\n")
                f.write(f"**Error:** {fix['error']}\n\n")
                f.write(f"**Diagnosis:** {fix['diagnosis']}\n\n")
                f.write(f"**File:** {fix['file']} (Line {fix['line']})\n\n")
                
                if fix['original_code']:
                    f.write(f"**Original Code:**\n```python\n{fix['original_code']}\n```\n\n")
                
                f.write(f"**Fixed Code:**\n```python\n{fix['fixed_code']}\n```\n\n")
                f.write("---\n\n")


if __name__ == "__main__":
    generator = AutoFixGenerator()
    generator.process_all_failures()
