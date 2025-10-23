import os
import sys

def debug_print(*args, **kwargs):
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    if DEBUG:
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            # Handle unicode encoding issues on Windows console
            safe_args = []
            for arg in args:
                if isinstance(arg, str):
                    # Replace problematic unicode characters
                    safe_arg = arg.replace('✓', '[OK]').replace('⚠️', '[WARN]').replace('❌', '[ERROR]')
                    safe_args.append(safe_arg)
                else:
                    safe_args.append(arg)
            print(*safe_args, **kwargs)