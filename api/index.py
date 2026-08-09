from app import create_app
app = create_app()

# Vercel serverless entry point
from vercel_wsgi import make_venvwsgi_app
handler = make_venvwsgi_app(app)