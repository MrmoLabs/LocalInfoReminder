import os
import sys
import logging

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    Handles 'assets/' folder being external to the EXE while other files might be internal.
    """
    try:
        # 1. Base directory logic
        if getattr(sys, 'frozen', False):
            # If application is compiled to EXE
            base_path = os.path.dirname(sys.executable)
        else:
            # If running from source (src/utils/resource_path.py)
            # Root is 2 levels up from src/utils
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 2. Join with relative path
        abs_path = os.path.abspath(os.path.join(base_path, relative_path))
        
        # 3. Log results for debugging
        if not os.path.exists(abs_path):
            logging.warning(f"Resource not found at: {abs_path}")
        else:
            logging.debug(f"Resource found: {abs_path}")
            
        return abs_path
    except Exception as e:
        logging.error(f"Error resolving resource path for {relative_path}: {e}")
        return relative_path
