#!/usr/bin/env python3
"""
Pre-commit security check script
Run this before committing to ensure no sensitive data is included
"""

import os
import sys
import re

def check_for_sensitive_patterns():
    """Check for common sensitive data patterns in tracked files"""
    
    sensitive_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
        (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
        (r'postgresql://[^:]+:[^@]+@', 'Database URL with credentials'),
        (r'M3rcury1', 'Specific password found'),
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API key pattern'),
        (r'gsk_[a-zA-Z0-9]{52}', 'Groq API key pattern'),
    ]
    
    issues_found = []
    
    # Get list of tracked files
    import subprocess
    try:
        result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True)
        tracked_files = result.stdout.strip().split('\n')
    except:
        print("⚠️  Not a git repository or git not available")
        return []
    
    for filepath in tracked_files:
        if not os.path.exists(filepath):
            continue
            
        # Skip binary files and certain extensions
        if filepath.endswith(('.db', '.sqlite', '.pyc', '.pyo', '.jpg', '.png', '.gif', '.pdf')):
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for pattern, description in sensitive_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Skip documentation files
                    if any(doc in filepath for doc in ['README.md', '.env.example', 'SECURITY.md', 'SECURITY_FIXES_APPLIED.md', 'MAKE_PUBLIC_CHECKLIST.md']):
                        continue
                    
                    # Check if match is in a comment
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_content = content[line_start:content.find('\n', match.start())]
                    if line_content.strip().startswith('#') or '# Example:' in line_content:
                        continue
                    
                    line_num = content[:match.start()].count('\n') + 1
                    issues_found.append({
                        'file': filepath,
                        'line': line_num,
                        'description': description,
                        'match': match.group()[:50]  # First 50 chars
                    })
        except Exception as e:
            continue
    
    return issues_found

def check_sensitive_files():
    """Check if sensitive files are being tracked"""
    
    sensitive_files = [
        '.env',
        'token.json',
        '*.pem',
        '*.key',
        '*.db',
        '*.sqlite',
        'secrets/',
    ]
    
    issues = []
    
    import subprocess
    try:
        result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True)
        tracked_files = result.stdout.strip().split('\n')
    except:
        return []
    
    for filepath in tracked_files:
        for pattern in sensitive_files:
            if pattern.endswith('/'):
                if filepath.startswith(pattern):
                    issues.append(f"Sensitive directory tracked: {filepath}")
            elif '*' in pattern:
                ext = pattern.replace('*', '')
                if filepath.endswith(ext):
                    issues.append(f"Sensitive file tracked: {filepath}")
            elif filepath == pattern:
                issues.append(f"Sensitive file tracked: {filepath}")
    
    return issues

def main():
    print("Running security checks...\n")
    
    # Check for sensitive patterns
    pattern_issues = check_for_sensitive_patterns()
    
    # Check for sensitive files
    file_issues = check_sensitive_files()
    
    if pattern_issues:
        print("SENSITIVE DATA PATTERNS FOUND:\n")
        for issue in pattern_issues:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    {issue['description']}: {issue['match']}")
            print()
    
    if file_issues:
        print("SENSITIVE FILES TRACKED:\n")
        for issue in file_issues:
            print(f"  {issue}")
        print()
    
    if pattern_issues or file_issues:
        print("SECURITY ISSUES DETECTED!")
        print("   Please remove sensitive data before committing.\n")
        return 1
    else:
        print("No obvious security issues detected")
        print("   Remember to:")
        print("   - Review changes carefully")
        print("   - Ensure .env is not committed")
        print("   - Check for any hardcoded credentials\n")
        return 0

if __name__ == "__main__":
    sys.exit(main())
