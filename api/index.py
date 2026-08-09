from app import create_app

app = create_app()

# Vercel serverless entry point
def handler(request):
    """Vercel serverless handler"""
    with app.request_context(request.environ):
        return app(request.environ, lambda status, headers: None)