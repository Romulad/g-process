## WSGI object create

**Path:** `gunicorn.http.wsgi.create` [Full file source code](./wsgi_object.py)

```python
def create(req, sock, client, server, cfg):
    resp = Response(req, sock, cfg)

    # set initial environ
    environ = default_environ(req, sock, cfg)

    # default variables
    host = None
    script_name = os.environ.get("SCRIPT_NAME", "")

    # add the headers to the environ
    for hdr_name, hdr_value in req.headers:
        if hdr_name == "EXPECT":
            # handle expect
            if hdr_value.lower() == "100-continue":
                sock.send(b"HTTP/1.1 100 Continue\r\n\r\n")
        elif hdr_name == 'HOST':
            host = hdr_value
        elif hdr_name == "SCRIPT_NAME":
            script_name = hdr_value
        elif hdr_name == "CONTENT-TYPE":
            environ['CONTENT_TYPE'] = hdr_value
            continue
        elif hdr_name == "CONTENT-LENGTH":
            environ['CONTENT_LENGTH'] = hdr_value
            continue

        # do not change lightly, this is a common source of security problems
        # RFC9110 Section 17.10 discourages ambiguous or incomplete mappings
        key = 'HTTP_' + hdr_name.replace('-', '_')
        if key in environ:
            hdr_value = "%s,%s" % (environ[key], hdr_value)
        environ[key] = hdr_value

    # set the url scheme
    environ['wsgi.url_scheme'] = req.scheme

    # set the REMOTE_* keys in environ
    # authors should be aware that REMOTE_HOST and REMOTE_ADDR
    # may not qualify the remote addr:
    # http://www.ietf.org/rfc/rfc3875
    if isinstance(client, str):
        environ['REMOTE_ADDR'] = client
    elif isinstance(client, bytes):
        environ['REMOTE_ADDR'] = client.decode()
    else:
        environ['REMOTE_ADDR'] = client[0]
        environ['REMOTE_PORT'] = str(client[1])

    # handle the SERVER_*
    # Normally only the application should use the Host header but since the
    # WSGI spec doesn't support unix sockets, we are using it to create
    # viable SERVER_* if possible.
    if isinstance(server, str):
        server = server.split(":")
        if len(server) == 1:
            # unix socket
            if host:
                server = host.split(':')
                if len(server) == 1:
                    if req.scheme == "http":
                        server.append(80)
                    elif req.scheme == "https":
                        server.append(443)
                    else:
                        server.append('')
            else:
                # no host header given which means that we are not behind a
                # proxy, so append an empty port.
                server.append('')
    environ['SERVER_NAME'] = server[0]
    environ['SERVER_PORT'] = str(server[1])

    # set the path and script name
    path_info = req.path
    if script_name:
        if not path_info.startswith(script_name):
            raise ConfigurationProblem(
                "Request path %r does not start with SCRIPT_NAME %r" %
                (path_info, script_name))
        path_info = path_info[len(script_name):]
    environ['PATH_INFO'] = util.unquote_to_wsgi_str(path_info)
    environ['SCRIPT_NAME'] = script_name

    # override the environ with the correct remote and server address if
    # we are behind a proxy using the proxy protocol.
    environ.update(proxy_environ(req))
    return resp, environ
```


## WSGI start_response

**Path:** `gunicorn.http.wsgi.Response.start_response` [Full file source code](./wsgi_object.py)

```python
def start_response(self, status, headers, exc_info=None):
    if exc_info:
        try:
            if self.status and self.headers_sent:
                util.reraise(exc_info[0], exc_info[1], exc_info[2])
        finally:
            exc_info = None
    elif self.status is not None:
        raise AssertionError("Response headers already set!")

    self.status = status

    # get the status code from the response here so we can use it to check
    # the need for the connection header later without parsing the string
    # each time.
    try:
        self.status_code = int(self.status.split()[0])
    except ValueError:
        self.status_code = None

    self.process_headers(headers)
    self.chunked = self.is_chunked()
    return self.write
```


## WSGI FileWrapper

**Path:** `gunicorn.http.wsgi.FileWrapper` [Full file source code](./wsgi_object.py)

```python
class FileWrapper:

    def __init__(self, filelike, blksize=8192):
        self.filelike = filelike
        self.blksize = blksize
        if hasattr(filelike, 'close'):
            self.close = filelike.close

    def __getitem__(self, key):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise IndexError
```