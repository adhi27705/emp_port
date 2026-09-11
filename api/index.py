import sys
import os

# Add parent directory and app directory to path for Vercel Python runtime
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

app_dir = os.path.join(parent_dir, 'app')
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Import Flask application instance
from app.app import app

# Export app for Vercel serverless handler
app.debug = False
