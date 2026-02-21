# Worker Initialization and Execution

This is where Gunicorn transitions from *process management* to *application serving*.

---

## Spawning a Worker

When Gunicorn creates a new worker process, the following sequence occurs:

* The worker class is instantiated in the master process.
* After [fork()](./source_ref/3_server_init_code.md#arbiter-class-spawn_worker-method), the worker’s [init_process()](./source_ref/base_worker.md#base-worker-init_process-method) method is executed inside the child process.
* [init_process()](./source_ref/base_worker.md#base-worker-init_process-method)  performs setup and finally calls the worker’s `run()` method.
* The worker enters its main loop and begins accepting client connections.

From this point onward, the worker process is responsible for handling HTTP requests.

---

## The Base Worker Class

To understand worker behavior, we begin with the base implementation located at:

```
gunicorn.workers.base.Worker
```

Specific worker types — such as the synchronous worker (`gunicorn.workers.sync.SyncWorker`) — extend this base class and specialize the request handling strategy.

---

## Base Worker Initialization [`Worker.__init__`](./source_ref/base_worker.md#base-worker-__init__-method)

When the worker class is instantiated (in the master process), several attributes are initialized.

### Core identity attributes

* **age**
  Represents the order in which the worker was spawned.
  If three workers are created, their ages will be 1, 2, and 3 respectively.
  The master process increments this value before passing it to each worker.

* **pid**
  Initially set to `"[booting]"`.
  Updated after the fork to reflect the actual process ID.

* **ppid**
  The PID of the master process.

---

### Runtime configuration

* **sockets**
  A list of listener sockets inherited from the master process (`Arbiter.LISTENERS`).

* **app**
  The `WsgiAppInstance`, passed from the master.

* **cfg**
  The configuration object.

* **timeout**
  The maximum time allowed without notifying the master before the worker is considered unresponsive.

* **max_requests**
  Maximum number of requests the worker will process before restarting.
  Controlled by `--max-requests`. Defaults to `sys.maxsize`.

---

### Lifecycle and state flags

* **booted**
  Indicates whether the worker finished initialization and is ready to accept requests. Defaults to `False`.

* **aborted**
  Indicates whether the worker exited unexpectedly. Defaults to `False`.

* **alive**
  Indicates whether the worker should continue processing requests. Defaults to `True`.

* **nr**
  Tracks the number of handled requests. Starts at `0`.

---

### Logging and monitoring

* **log**
  Logger instance provided by the master process.

* **tmp**
  An instance of [WorkerTmp](./source_ref/worker_temp.py), which manages the worker’s temporary heartbeat file.

This temporary file is periodically updated by the worker.
The master process checks its modification timestamp to determine whether the worker is still alive.
If the timestamp exceeds the configured `timeout`, the master terminates the worker.

---

### Optional components

* **reloader**
  Stores the reloader engine when `--reload` is enabled.

---

## The [init_process()](./source_ref/base_worker.md#base-worker-init_process-method) Method

The [init_process()](./source_ref/base_worker.md#base-worker-init_process-method) method is executed inside the worker process (after forking).
It is responsible for preparing the worker runtime before entering the request loop.

If a subclass overrides this method, it should call:

```python
super().init_process()
```

as the final step to ensure the base initialization and `run()` loop are executed.

---

### What [init_process()](./source_ref/base_worker.md#base-worker-init_process-method) Does

Inside the base worker implementation, [init_process()](./source_ref/base_worker.md#base-worker-init_process-method) performs the following tasks:

---

### Environment Setup

* Updates environment variables using values provided via `--env`.
* Drops privileges if configured, changing user and group via `--user` and `--group`.

---

### Pipe Creation for Signal Wake-Up

* Creates a pipe used to wake up the worker when signals arrive.
* File descriptors are set to:

  * Non-blocking
  * Close-on-exec

This prevents unnecessary delays in signal processing.

---

### File Descriptor Hygiene

To prevent descriptor leakage:

* Applies the close-on-exec flag to inherited sockets.
* Applies it to the temporary heartbeat file.
* Applies it to log file descriptors.

This ensures that if `exec()` is used later (e.g. upgrade), descriptors are not unintentionally inherited.

---

### Signal Reconfiguration

* Clears inherited signal handlers.
* Registers worker-specific signal handlers.

Workers do not handle signals the same way the master does; their responsibilities differ.

---

### Reload Mechanism (`--reload`)

If `--reload` is enabled:

* Gunicorn initializes a reloader engine.
* If `inotify` is available, it is used.
* Otherwise, filesystem polling is used to check file modification times.

The reloader runs in a separate thread from the main request loop.

When file changes are detected:

* The worker sets `alive = False`.
* The `worker_int` server hook is called.
* The worker exits.
* The master spawns a new worker with updated code.

This mechanism enables automatic development-time reloads.

---

### Application Loading

If the WSGI application was not preloaded in the master process:

* The worker loads the WSGI callable now.

---

### Post-Initialization Hook

The `post_worker_init` server hook is executed.

This allows custom logic to run after the worker is fully initialized but before serving requests.

---

### Final Step: Entering the Main Loop

* The `booted` flag is set to `True`.
* The worker’s `run()` method is invoked.

At this moment, the worker is fully operational.

It now enters its request-processing loop and begins accepting client connections through the inherited listener sockets.

---

The [next step](./6_sync_worker_&_request_parsing.md) is to examine how a specific worker implementation — such as the synchronous worker — parses HTTP requests and invokes the WSGI application.
