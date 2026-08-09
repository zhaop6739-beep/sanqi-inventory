import sys
import os

# Add the current directory to Python path so 'app' can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Vercel expects a WSGI callable named 'app'
app = create_app()

# For local development
if __name__ == '__main__':
    app.run(debug=True)