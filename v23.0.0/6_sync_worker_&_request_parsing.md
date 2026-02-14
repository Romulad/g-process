
17 - A closer look at `gunicorn.workers.sync.SyncWorker`

`gunicorn.workers.sync.SyncWorker` is the default worker used by gunicorn when no worker is specified.
It subclasses the base worker `gunicorn.workers.base.Worker` we just saw in the previous step and implement the `run` method, the one needed to accept and handle incomming request.

The `run` method of `gunicorn.workers.sync.SyncWorker` starts by making all our listeners (server sockets) no blocking meaning when we will call `accept` method on a listener(socket), it won't block waiting for a request to be available, instead it will return immediatly by either throwing an error or with a client request data (client socket and address). 

We then enter in the main loop, where gunicorn continously accept and process requests.

The main loop is design for two cases:
    - when we only have one listener:
        - In this case the worker starts processing request if available and after a request/response lifecycle, it updates its tempory file to tell the master process it still alive, then without waiting (meaning no call to `select.select`), the worker continously processes more requests if available until no request is waiting for processing. The worker then wait for `timeout --timeout` using `select.select` to free up the CPU before the next iteration and continue with the next iteration if `timeout` complete or new request arrives. 
    - when we have more than one listener:
        - The worker starts by checking listeners (server sockets) readability using `select.select` with `timeout`, if one or more listener (server socket) are readable, the worker then processes one request over each readable listeners then continues with the next iteration in the main loop using the same process again.

In other words, for each iteration in the main loop:
    - the worker notify the master process it's alive, 
    - check if there is request to process and processes it 
    - wait for `timeout` or new request
    - and restart the same process in the next iteration

**Note**: The worker notify the master process before starting to wait for `timeout` or new request.

Also during each iteration in the main loop, the worker check if its parent has changed, if so, meaning it's an orphan process, the worker breaks from the main loop and exits the process.

During the main loop execution, the worker instance method `accept` is called with a listener (server socket) on which socket `accept` method is called.

When a request is available the call to `accept` on the listener(server socket) return a new socket to interact with the client and the client address info (address, port).

The client socket is set to blocking (e.g read operation will wait untill data is available) and close on exec flag is apply to it, then the worker instance method `handle` is called with:
    - the server socket, the listener
    - the socket to use to interact with the client
    - and the client address, a tuple in form (address, port).

The `handle` method starts by checking whether the communication with the client should be done over ssl based on `--keyfile` and `--certfile` options. If `--keyfile` or `--certfile` is specified, a new secure socket is created from the client socket and will be used to handle the communication over SSL/TLS.

The worker handles the client Http request in two phases:
    - Parsing the client request
    - Process the request after parsing by calling the wsgi application and send its response to the client

### Parsing the client request
As I am writting this, Gunicorn uses Http/1 and parses the http message according to that specification.
In the `handle` method, after deciding wether or not to use ssl/tls, the worker creates a parser object that takes as arguments the client socket, address and the server configuration. 

The parser object is an intance of `gunicorn.http.parser.RequestParser`. Let's call the instance created `parser`.

During the parser initialization:
    - the config object is set on the parser instance as an attribute named `cfg`
    - based on the client info, an attribute `unreader` is set on the parser instance `parser` and contains an object that wrap the client socket or data source in order to provide a convinent way to read the data.
    The unreader can be of two types `gunicorn.http.unreader.SocketUnreader` or `gunicorn.http.unreader.IterUnreader`, both sharing a common parent class `gunicorn.http.unreader.Unreader`. 
    Instance of `gunicorn.http.unreader.SocketUnreader` is created when the client socket or data source has the `recv` method otherwhise `gunicorn.http.unreader.IterUnreader` is created.
    So far, from my understanding, the unreader object wrap the client socket, then is used to read from it an amount `Q` of data and if we get more than `Q`, the remaining data is kept in memory for reference later to potentially avoid data lost.
    In fact during unreader initialization, it creates an in memory byte buffer using python `io` 
    module
    - then an attribute named `mesg` is set on `parser`, which represent a request object `gunicorn.http.message.Request` and will contain the parsed data from the Http message
    - `source_addr`, an instance attribute is set containing the client address on `parser`
    -  and at the end `req_count` attribute is set on `parser`, gunicorn says it used when we have the `Connection` header with `keep-alive` value

`gunicorn.http.parser.RequestParser` provides a python iterator interface, so after `parser` is created, python bultin `next` function is executed on it leading to the execution of the `__next__` method. 

The execution flow of `__next__` method from `parser` create a request object `R`(just a name, nothing more) which is an instance of `gunicorn.http.message.Request`. The request object `R` created is set in `mesg` attribute on `parser` and that attribute is then returned from the `__next__` method. 

So, the `mesg` attribute on `parser` will contain an instance of `gunicorn.http.message.Request`. 

`R` represents the object containing the parsed http message for a request.

**Parsed http message?**

Yes! And the parsing is done during the intialization of `gunicorn.http.message.Request` resulted to `R`

During the intialization of `gunicorn.http.message.Request` the Http message request line, headers are parsed and the body object or mechanism that will be use to read payload sent by the client is determined.

Before we look at the parsing process, here is an example of a Http GET message:
```bash
GET / HTTP/1.1\r\n
Host: localhost:8000\r\n
User-Agent: user-agent-value\r\n
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n
Accept-Language: fr-FR,fr;q=0.5\r\n
Accept-Encoding: gzip, deflate, br, zstd\r\n
DNT: 1\r\n
Sec-GPC: 1\r\n
Connection: keep-alive\r\n
Cookie: csrftoken=csrtoken-value\r\n
Upgrade-Insecure-Requests: 1\r\n
Sec-Fetch-Dest: document\r\n
Sec-Fetch-Mode: navigate\r\n
Sec-Fetch-Site: none\r\n
Sec-Fetch-User: ?1\r\n
Priority: u=0, i\r\n\r\n
[body]
```
`gunicorn.http.message.Request` for initialization takes as args the server config object, the unreader created earlier, the client address and the request count (usefull with `keep-alive` connection) then:
    - Setup the class state with a set of instance variables like `method` `uri` `path` `query`, `limit_request_line`, `limit_request_fields`, `limit_request_field_size` among others
    - Executes the `parse` method:
        - The request line is read from the http message, that's up to the first occurence of `\r\n`.
        In the example provided, it's this: `GET / HTTP/1.1`. If gunicorn is running behind a server proxy that support protocol proxy and you enable it with the config option `--proxy-protocol`, then it checks if the first line read is the protocol proxy line. If so, which can looks like this `PROXY TCP4 203.0.113.10 203.0.113.20 56324 80`, it parses it, validate it, extracts the necessary informations like the client IP and Port from it and then read again up to the next occurence of `\r\n` to now get the request line. Gunicorn while reading the request line ensure it size is not larger than the config option `--limit-request-line`
        - After the request line is read, for example `GET / HTTP/1.1`, it's parsed, validate and the request **method**, **path**, **query**, **fragment** and Http **version** are extract from it. If any error occures during parsing like:
            - the request method contains not allowed characteres like lower case letters, # etc...
            - the request method length is too large or less, must be between 3 or 20, no more, no less
            - the request uri is empty or is invalid
            - the http version specified in the message is invalid or not the version 1
        then the request processing stops and the client get an error message. 
        - Now come the request headers parsing part, from the remaining data after reading the request line, the worker reads from the socket/data source untill it find the fisrt occurence of `\r\n\r\n` indicating the end of the request headers. The headers data size should be within a limit which is calculate using `--limit-request-fields` and `--limit-request-field_size` config options. In case of no request headers available, we immediatly return from the `parse` method. This can happen with a message like this : 
        ```bash
        GET / HTTP/1.1\r\n
        \r\n
        [body]
        ```
        - if headers exist then the worker parses them to get a list of tuple (name, value) pair. While parsing each header line, the worker ensure that the headers count does not exceed `--limit-request-fields` option value or an error occures. It also makes sure that each header line size is within `--limit-request-field_size` option value or an error occures. Other validations happen as well like :
            - validating that the header has this format `name:value` like `Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`
            - ensuring that the header `name` does not contain not allowed characteres
            - making sure that the header value does not contain invalid and dangerous characteres `\0\r\n`
            - validating whether to allow `_` or not in header name based on `--header-map` option.
        - The headers are successfully parsed, we return from the `parse` method with the remain/unused data as value. That value is keep in the `unreader` object buffer.
    - From here We've successfully parse the http message request line and headers, and the read but not used data is keep in the `unreader` object buffer. The next step is to determine how we will read the http message request body
    - The body reading mechanism is influenced by two headers : `CONTENT-LENGTH` and `TRANSFER-ENCODING`. The goal is to determine if the request body should be read in chunk with `TRANSFER-ENCODING` header containing `chunked` as value in the right order or directly using the `CONTENT-LENGTH` header. Only one should be specified at a time but if both exist in the request header which is uncommon, an error occures to avoid smuggling attack. The base object use to read the request payload is `gunicorn.http.body.Body` and it takes a reader object during initialization which can be `ChunkedReader`, `LengthReader` or `EOFReader`. The reader is a class that takes the `unreader` object intance and provide a `.read` method.

The initialization of `gunicorn.http.message.Request` is completed and we get an object (which we called `R`) that contains the http request message parsed.
