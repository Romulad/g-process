import sys

from gunicorn.app.wsgiapp import WSGIApplication

def app(environ, start_response):
    """Simplest possible application object"""
    with open("./app.html", "r") as f:
        content = f.read()
    data = content.encode("latin-1")
    status = '200 Ok'
    if environ['REQUEST_METHOD'] == "POST":
        status = '201 Created'
    response_headers = [
        ('Content-type','text/html'),
        ('Content-Length', str(len(data)))
    ]   
    start_response(status, response_headers)
    return [data]


if __name__ == "__main__":
    options = [
        '--bind', '127.0.0.1:8000',
        '--workers', '1',
        '--access-logfile', '-',
        'app:app',
        '--reload',
    ]
    sys.argv.extend(options)
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
