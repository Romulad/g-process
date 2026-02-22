# Request Handling

This is the stage where the parsed HTTP request is turned into a WSGI call and an HTTP response is sent back to the client.

At a high level, the worker:

* Builds the WSGI [environ](https://peps.python.org/pep-3333/#environ-variables) dictionary.
* Instantiates a response object.
* Calls the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side).
* Streams the returned data to the client.

---

## Building the [environ](./source_ref/wsgi_object.md#wsgi-object-create) and the Response Object

[Request handling](./source_ref/sync_worker.md#sync-worker-handle_request-method) begins by invoking the server hook `pre_request`.

Next, the worker creates:

* The WSGI [environ](https://peps.python.org/pep-3333/#environ-variables).
* A response object: [gunicorn.http.wsgi.Response](./source_ref/wsgi_object.py).

The response object is initialized with:

* The parsed request object.
* The client socket.
* The server configuration.

While the response object is being prepared, the worker builds the [environ](https://peps.python.org/pep-3333/#environ-variables)  dictionary using:

* Information extracted from the parsed request (method, headers, path, version, etc.).
* Client and server socket details.
* Configuration values.

---

### Header Normalization

During this process:

* All incoming HTTP headers are normalized by replacing `-` with `_`.
* Most headers are prefixed with `HTTP_` before being inserted into [environ](https://peps.python.org/pep-3333/#environ-variables).

There are two important exceptions:

* `Content-Type` → `CONTENT_TYPE`
* `Content-Length` → `CONTENT_LENGTH`

If the request includes an [Expect header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Expect#large_message_body) (for example, `Expect: 100-continue`), the worker handles it appropriately before proceeding.

---

### Core WSGI Variables

The worker populates standard WSGI keys such as:

* `wsgi.version`
* `wsgi.url_scheme` (`http` or `https`, determined during parsing)
* `wsgi.input` (the request body wrapper)
* `wsgi.errors`
* `wsgi.multithread`
* `wsgi.multiprocess`
* `wsgi.run_once`

Network-related fields are also set:

* `REMOTE_ADDR`
* `REMOTE_PORT`
* `SERVER_NAME`
* `SERVER_PORT`

If `SCRIPT_NAME` is configured, the corresponding prefix is stripped from the request path:

* The prefix becomes `SCRIPT_NAME`
* The remainder becomes `PATH_INFO`

---

### Proxy Protocol Support

If Gunicorn is running behind a proxy that supports the PROXY protocol and the feature is enabled via `--proxy-protocol`, the worker updates:

* `REMOTE_ADDR`
* `REMOTE_PORT`

using the values provided by the proxy header rather than the raw socket values.

---

### Example `environ`

A simplified example of a fully built `environ` might look like:

```python
{
    "wsgi.errors": <gunicorn.http.wsgi.WSGIErrorsWrapper object>, 
    "wsgi.version": (1, 0), 
    "wsgi.multithread": False, 
    "wsgi.multiprocess": False, 
    "wsgi.run_once": False, 
    "wsgi.file_wrapper": <class "gunicorn.http.wsgi.FileWrapper">, 
    "wsgi.input_terminated": True, 
    "SERVER_SOFTWARE": "gunicorn/23.0.0", 
    "wsgi.input": <gunicorn.http.body.Body object>, 
    "gunicorn.socket": <socket.socket object>,
    "REQUEST_METHOD": "GET", 
    "QUERY_STRING": "", 
    "RAW_URI": "/", 
    "SERVER_PROTOCOL": "HTTP/1.1", 
    "HTTP_HOST": "localhost:8000", 
    "HTTP_USER_AGENT": "user-agent", 
    "HTTP_ACCEPT": "value", 
    "HTTP_ACCEPT_ENCODING": "gzip", 
    "HTTP_DNT": "value", 
    "HTTP_SEC_GPC": "value", 
    "HTTP_CONNECTION": "keep-alive", 
    "HTTP_COOKIE": "csrftoken=csrf-value", 
    "HTTP_UPGRADE_INSECURE_REQUESTS": "value", 
    "HTTP_SEC_FETCH_DEST": "value", 
    "HTTP_SEC_FETCH_MODE": "value", 
    "HTTP_SEC_FETCH_SITE": "value", 
    "HTTP_SEC_FETCH_USER": "value", 
    "HTTP_PRIORITY": "value", 
    "wsgi.url_scheme": "http", 
    "REMOTE_ADDR": "127.0.0.1", 
    "REMOTE_PORT": "54810", 
    "SERVER_NAME": "127.0.0.1", 
    "SERVER_PORT": "8000", 
    "PATH_INFO": "/", 
    "SCRIPT_NAME": ""
}
```

At this point, everything is ready to call the application.

---

## Calling the WSGI Application

Before invoking the WSGI application callable, the worker increments its internal counter `nr`, which tracks how many requests it has handled.

If `nr` exceeds the value configured via `--max-requests`, the worker will finish processing the current request and then exit gracefully. The master process will spawn a fresh worker to replace it. This mechanism helps mitigate memory leaks in long-running processes.

---

### The Application Call

The WSGI application callable is invoked with:

* The constructed `environ` dictionary.
* The response object’s [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method.

Conceptually:

```python
result = app(environ, response.start_response)
```

The WSGI application must:

* Call [start_response(status, response_headers, exc_info=None)](https://peps.python.org/pep-3333/#the-start-response-callable)
* Return an iterable yielding byte strings

---

## What `[start_response](./source_ref/wsgi_object.md#wsgi-start_response) Does

The [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method marks the beginning of the HTTP response.

It:

* Parses and validates the status line (e.g., `"201 Created"`).
* Validates response headers.
* Filters out [hop-by-hop headers](https://datatracker.ietf.org/doc/html/rfc2616.html#section-13.5.1) (such as `Connection`).
* Determines how the response body will be transmitted.

The transmission strategy depends on:

* Whether `Content-Length` is provided.
* The HTTP version.
* The response status code.
* The request method.

Possible outcomes:

* If `Content-Length` is set, the response body is sent up to that exact length.
* If no `Content-Length` is set and the protocol allows it (HTTP/1.1), chunked transfer encoding may be used.
* For status codes or methods that must not include a body (e.g., `HEAD`, `204`, `304`), no body is sent.

---

## Sending the Response Body

The iterable returned by the WSGI application is then consumed.

Each chunk of bytes is written to the client socket:

* Directly up to `Content-Length`, if defined.
* Using chunked transfer encoding when applicable.

If the returned object is an instance of [gunicorn.http.wsgi.FileWrapper](./source_ref/wsgi_object.md#wsgi-filewrapper), Gunicorn may optimize transmission:

* If `--no-sendfile` is not set and SSL is not enabled, it uses `socket.sendfile()` for zero-copy transfer.
* Otherwise, it falls back to iterating over the file and sending chunks manually.

---

## Finalization

Once all response data has been transmitted:

* The `post_request` server hook is called.
* The connection is closed.

With [gunicorn.workers.sync.SyncWorker](./source_ref/sync_worker.py), connections are not kept alive for reuse; the client connection is closed after each request cycle.

At this point, one complete request–response lifecycle has finished under the synchronous worker model.

[Next: Thanks](./next_step.md)
