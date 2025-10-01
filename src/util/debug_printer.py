import os
def debug_print(*args, **kwargs):
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    if DEBUG:
        print(*args, **kwargs)