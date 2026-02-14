### Request handling
This is where the client request is processed and a response is returned to the client. Mainly the [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary for the request is created then the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) is called and the data returned by the wsgi app is sent to the client.

#### Environ dictionary and response object
This step start with call to the server hook `pre_request`, then the [environ](https://peps.python.org/pep-3333/#environ-variables) and a response object(`gunicorn.http.wsgi.Response`) are created using the client socket and address, the request object created in the last step, the server config and the server address.

The response object `gunicorn.http.wsgi.Response` is intialized using the request object, the client socket and the server configuration, then the worker starts building the [environ variables](https://peps.python.org/pep-3333/#environ-variables) along with headers parsed in the request object. 

The worker also responds to the [Expect header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Expect#large_message_body) and normalize headers by replacing `-` by `_` for consistency. Request headers are also prefixed with  `HTTP_` before being set in the [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary except `CONTENT_TYPE` and `CONTENT_LENGTH`.

The client and server addresses and ports are set in the [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary using `REMOTE_ADDR`, `REMOTE_PORT`, `SERVER_NAME`, `SERVER_PORT` along with the `url_scheme` `http` or `https` determined during request parsing.

If `SCRIPT_NAME` is available, the url part containing it, is cut from the parsed path in the request object. The remaining part is set in the [environ](https://peps.python.org/pep-3333/#environ-variables) as `PATH_INFO` along with script name itself `SCRIPT_NAME`.

If gunicorn is running behind a proxy that support protocol proxy and you enable protocol proxy through `--protocol-poxy` then the client info `REMOTE_ADDR`, `REMOTE_PORT` are updated in the [environ](https://peps.python.org/pep-3333/#environ-variables).

At the end an [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary can looks like this:
```python
{
    "wsgi.errors": <gunicorn.http.wsgi.WSGIErrorsWrapper object at address>, 
    "wsgi.version": (1, 0), 
    "wsgi.multithread": False, 
    "wsgi.multiprocess": False, 
    "wsgi.run_once": False, 
    "wsgi.file_wrapper": <class "gunicorn.http.wsgi.FileWrapper">, 
    "wsgi.input_terminated": True, 
    "SERVER_SOFTWARE": "gunicorn/23.0.0", 
    "wsgi.input": <gunicorn.http.body.Body object at address>, 
    "gunicorn.socket": <socket.socket fd=9, family=2, type=1, proto=0, laddr=("127.0.0.1", 8000), raddr=("127.0.0.1", 54810)>, 
    "REQUEST_METHOD": "GET", 
    "QUERY_STRING": "", 
    "RAW_URI": "/", 
    "SERVER_PROTOCOL": "HTTP/1.1", 
    "HTTP_HOST": "localhost:8000", 
    "HTTP_USER_AGENT": "user-agent", 
    "HTTP_ACCEPT": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "HTTP_ACCEPT_LANGUAGE": "fr-FR,fr;q=0.5", 
    "HTTP_ACCEPT_ENCODING": "gzip, deflate, br, zstd", 
    "HTTP_DNT": "1", 
    "HTTP_SEC_GPC": "1", 
    "HTTP_CONNECTION": "keep-alive", 
    "HTTP_COOKIE": "csrftoken=csrf-value", 
    "HTTP_UPGRADE_INSECURE_REQUESTS": "1", 
    "HTTP_SEC_FETCH_DEST": "document", 
    "HTTP_SEC_FETCH_MODE": "navigate", 
    "HTTP_SEC_FETCH_SITE": "none", 
    "HTTP_SEC_FETCH_USER": "?1", 
    "HTTP_PRIORITY": "u=0, i", 
    "wsgi.url_scheme": "http", 
    "REMOTE_ADDR": "127.0.0.1", 
    "REMOTE_PORT": "54810", 
    "SERVER_NAME": "127.0.0.1", 
    "SERVER_PORT": "8000", 
    "PATH_INFO": "/", 
    "SCRIPT_NAME": ""
}
```

#### WSGI app call
Before calling the wsgi application callable the worker increment it instance attribute `nr` that keep track on the number of request handle so far. If after incrementation, `nr` value is greater that `--max-requests` option then the worker will restart(exit and a new one will be created) after handling the current request.

Then the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) is called with [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary created and the response object instance (`gunicorn.http.wsgi.Response`) [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method. 

The [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) do it magic and return the data that should be sent to client as an iterable of bytes. But before returning the data it must call the response object [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method with the response status like `201 Created` and the response headers as collection of tuple `(header_name, header_value)` along with an optional arg `exc_info`. See [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) for more info.

Mainly, the response object [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method mark the start of the http response, it:
    - parsed the status code provide by the wsgi application
    - processes the headers provided by the wsgi application, validate each of them and ignore [hop-by-hop headers](https://datatracker.ietf.org/doc/html/rfc2616.html#section-13.5.1) 
    - determine how data should be sent to client:
        - in chuck, when content length is not provided, http version support chunked body and the response status code/request method support sending a body in the response data
        - directly up to content length when `CONTENT-LENGTH` is not `None`

The data returned by the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) are sent to client up to `CONTENT-LENGTH` or if not `CONTENT-LENGTH` in chucked if client support it.

If the returned object is an intance of `gunicorn.http.wsgi.FileWrapper` then based on `--no-sendfile` and ssl not being enabled, gunicorn use `socket.socket.sendfile` for data transmission to client otherwhise fallback to the default sending mechanisme (iterate and send returned data to client).

Once data are sent to client, `post_request` server hook is called and no matter `--keep-alive`, the connection is closed with the client since we are use using `gunicorn.workers.sync.SyncWorker` worker.

We are just done handling a request with `gunicorn.workers.sync.SyncWorker`.