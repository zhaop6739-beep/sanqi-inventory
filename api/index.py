from app import create_app
app = create_app()

# Vercel serverless entry point using ASGI adapter
def handler(request):
    """Vercel serverless handler"""
    from flask import Request
    from io import BytesIO
    
    # Convert Vercel request to WSGI environ
    environ = {
        'REQUEST_METHOD': request.get('method', 'GET'),
        'SCRIPT_NAME': '',
        'PATH_INFO': request.get('path', '/'),
        'QUERY_STRING': request.get('query', ''),
        'SERVER_NAME': 'vercel',
        'SERVER_PORT': '443',
        'HTTP_HOST': request.get('headers', {}).get('host', 'localhost'),
        'CONTENT_TYPE': request.get('headers', {}).get('content-type', ''),
        'CONTENT_LENGTH': str(len(request.get('body', b''))),
        'wsgi.input': BytesIO(request.get('body', b'')),
        'wsgi.errors': BytesIO(),
        'wsgi.version': (1, 0),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'wsgi.url_scheme': 'https',
    }
    
    # Add headers
    for key, value in request.get('headers', {}).items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = 'HTTP_' + key
        environ[key] = value
    
    response_body = []
    
    def start_response(status, headers):
        response_body.append((status, headers))
    
    result = app(environ, start_response)
    body = b''.join(result)
    
    status = response_body[0][0] if response_body else '200 OK'
    headers = response_body[0][1] if response_body else []
    
    return {
        'statusCode': int(status.split()[0]),
        'headers': dict(headers),
        'body': body.decode('utf-8')
    }