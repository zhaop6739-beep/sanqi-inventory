from app import create_app

# Vercel expects a WSGI callable named 'app'
app = create_app()

# For local development
if __name__ == '__main__':
    app.run(debug=True)