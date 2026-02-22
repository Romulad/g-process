# A Closer Look at the Synchronous Worker

The default worker used by Gunicorn is:

```python
gunicorn.workers.sync.SyncWorker
```

It subclasses:

```python
gunicorn.workers.base.Worker
```

Unlike the [base class](./5_base_worker.md), which mainly provides lifecycle and process management logic, [SyncWorker](./source_ref/sync_worker.py) implements the actual request-processing loop through its [run()](./source_ref/sync_worker.md#sync-worker-run-method) method.

This is where connections are accepted, HTTP messages are parsed, and your WSGI application is invoked.

---

## The [run()](./source_ref/sync_worker.md#sync-worker-run-method) Method

At startup, the synchronous worker configures all inherited listener sockets (server sockets) to **non-blocking mode**.

This means that when [accept()](./source_ref/sync_worker.md#sync-worker-accept-method) is called:

* It does not block waiting for a connection.
* It immediately returns:

  * A client socket (if a connection is ready), or
  * An error indicating that no connection is available.

After this setup, the worker enters its main loop.

---

## The Main Loop Strategy

The synchronous worker handles two scenarios depending on the number of listener sockets.

### When There Is Only [One Listener](./source_ref/sync_worker.md#sync-worker-run_for_one-method)

* The worker attempts to accept a connection.
* If a request is available, it processes the full request–response lifecycle.
* After completing a request, it updates its temporary heartbeat file to notify the master process that it is still alive.
* It continues processing additional queued requests immediately without calling `select()`, until no more are ready.
* When no request is pending, it waits using `select.select()` with the configured `timeout` to avoid busy-waiting and CPU exhaustion.

---

### When There Are [Multiple Listeners](./source_ref/sync_worker.md#sync-worker-run_for_multiple-method)

* The worker uses `select.select()` to check which listener sockets are readable.
* For each readable listener, it processes one request.
* It then loops again and repeats the same process.

---

### What Happens in Each Loop Iteration

Each iteration of the worker loop follows this pattern:

* Notify the master process that the worker is alive (by updating the temporary file).
* Check for incoming connections.
* Process available requests.
* Wait for either:
  * A new request, or
  * The timeout to expire.
* Repeat.

The heartbeat update occurs **before** waiting, ensuring the master does not mistakenly consider the worker unresponsive.

Additionally, the worker checks whether its parent PID has changed.
If the parent process is no longer the expected master, the worker exits to avoid becoming an orphan.

---

## Accepting a Connection

When a connection is available:

```python
client_socket, client_address = listener.accept()
```

The worker then:

* Sets the client socket to **blocking mode** (reads will wait for data).
* Applies the close-on-exec flag.
* Calls its internal [handle()](./source_ref/sync_worker.md#sync-worker-handle-method) method with:

  * The listener socket,
  * The client socket,
  * The client address.

---

## Inside the [handle()](./source_ref/sync_worker.md#sync-worker-handle-method) Method

The first step is to determine whether SSL/TLS should be used.

If `--keyfile` or `--certfile` is configured:

* The client socket is wrapped in a secure SSL socket.
* All further communication occurs over TLS.

From there, request handling proceeds in two phases:

* Parsing the HTTP request
* Processing the parsed request (calling the WSGI application)

---

## Parsing the HTTP Request

Gunicorn use HTTP/1.x parsing.

To parse a request, the worker creates a parser object:

```python
gunicorn.http.parser.RequestParser
```

Let’s call this instance `parser`.

---

### Parser Initialization

When [RequestParser](./source_ref/request-parser.md#parser-__init__-method) is created:

* The configuration object (`cfg`) is attached.
* An **unreader** object is created.

The unreader abstracts how data is read from the client socket.

It can be:

* [gunicorn.http.unreader.SocketUnreader](./source_ref/unreader.py)
* [gunicorn.http.unreader.IterUnreader](./source_ref/unreader.py)

Both inherit from a common base class.

If the data source exposes a `.recv()` method (like a socket), `SocketUnreader` is used.

The unreader:

* Wraps the client socket.
* Reads a chunk of bytes.
* Buffers any excess bytes in memory.
* Uses an in-memory buffer from Python’s `io` module.

This prevents data loss and allows partial reads.

The parser also sets:

* `mesg` — which will hold the parsed request object
* `source_addr` — the client address
* `req_count` — useful for `keep-alive` handling

---

### The Iterator Interface

[RequestParser](./source_ref/request-parser.py) implements the iterator protocol.

Calling:

```python
next(parser)
```

triggers [__next__()](./source_ref/request-parser.md#parser-__next__-method).

Inside [__next__()](./source_ref/request-parser.md#parser-__next__-method):

* A new request object is created:

  ```python
  gunicorn.http.message.Request
  ```
* That object is stored in `parser.mesg`.
* The parsed request object is returned.

We’ll call this object **R**.

---

### Inside [gunicorn.http.message.Request](./source_ref/message-parser.py)

The actual HTTP parsing happens during initialization of this object.

It receives:

* The server configuration
* The unreader
* The client address
* The request count

---

### Example HTTP Request

```
GET / HTTP/1.1\r\n
Host: localhost:8000\r\n
User-Agent: example\r\n
Connection: keep-alive\r\n
\r\n
```

---

### Parsing Flow

#### Request Line

The parser reads up to the first `\r\n`.

Example:

```
GET / HTTP/1.1
```

If `--proxy-protocol` is enabled, Gunicorn first checks for a PROXY line such as:

```
PROXY TCP4 203.0.113.10 203.0.113.20 56324 80
```

If present, it parses and validates that line before reading the actual HTTP request line.

The request line is validated:

* Method must contain valid characters.
* Length must be within bounds.
* URI must not be empty.
* HTTP version must be valid.
* Must respect `--limit-request-line`.

Any violation results in an error response.

---

#### Header Parsing

After the request line, Gunicorn reads until `\r\n\r\n`.

Header validation includes:

* Total header count must not exceed `--limit-request-fields`.
* Each header size must not exceed `--limit-request-field_size`.
* Each header must follow `name: value` format.
* Header names must contain valid characters.
* Header values must not contain dangerous characters like `\0`, `\r`, or `\n`.
* Underscore handling depends on configuration.

If no headers are present, parsing stops immediately.

Any unread bytes remain buffered in the unreader.

---

#### Determining the Body Reader

After headers are parsed, Gunicorn decides how to read the body.

This depends on:

* `Content-Length`
* `Transfer-Encoding`

If `Transfer-Encoding: chunked` is present:

* A `ChunkedReader` is used.

If `Content-Length` is present:

* A `LengthReader` is used.

If neither is present:

* An `EOFReader` may be used.

If both are present simultaneously:

* An error is raised to prevent request smuggling attacks.

All body readers are wrapped by:

```python
gunicorn.http.body.Body
```

Each reader uses the unreader internally to safely retrieve bytes.

---

### Final Result of Parsing

At this stage:

* The request line is validated.
* Headers are parsed and validated.
* The appropriate body reader is selected.
* Unused bytes remain buffered.

The [Request](./source_ref/message-parser.py) object (R) now represents a fully parsed HTTP request.

It contains:

* Method
* Path
* Query string
* Version
* Headers
* Body reader
* Client address

The worker can now move to the next stage:

[Calling the WSGI application and generating the HTTP response.](./7_wsgi_handling.md)