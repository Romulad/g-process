# From Arbiter Initialization to Server Boot

Once the [Arbiter](./source_ref/arbiter.py) instance has been created, its [run()](./source_ref/arbiter.md#arbiter-class-run-method) method is invoked.

This is the moment you see:

```
Starting gunicorn <version>
```

From here, the master process begins coordinating everything.

---

## What Happens Inside [Arbiter.run()](./source_ref/arbiter.md#arbiter-class-run-method)

The [run()](./source_ref/arbiter.md#arbiter-class-run-method) method is responsible for preparing the master process, binding sockets, spawning workers, and supervising them throughout the server’s lifetime.

It performs the following major operations.

---

### PID File Creation

If the `--pid` option is provided, Gunicorn creates a PID file containing the master process ID.

* The object managing this file is stored in the `pidfile` attribute.

---

### Server Hooks: `on_starting`

Before proceeding further, Gunicorn invokes the `on_starting` server hook (if defined in the configuration).

* The hook receives the `Arbiter` instance.
* It runs in the **master process**.
* This is typically used for custom initialization logic.

---

### Signal Handlers Registration

Gunicorn sets up handlers for several Unix signals. These signals allow runtime control of the server.

* **SIGHUP**
  Reload configuration, start new workers with updated settings, and gracefully shut down old workers.

* **SIGQUIT, SIGINT**
  Immediate shutdown.

* **SIGTERM**
  Graceful shutdown. Workers are allowed to finish ongoing requests up to the `--graceful-timeout`.

* **SIGTTIN**
  Increase the number of workers by one.

* **SIGTTOU**
  Decrease the number of workers by one.

* **SIGUSR1**
  Reopen log files.

* **SIGUSR2**
  Upgrade Gunicorn on the fly (zero-downtime binary upgrade). The old master should later receive `SIGTERM`.

* **SIGWINCH**
  Gracefully stop workers when running in daemon mode.

* **SIGCHLD**
  Sent when a worker exits or stops. Used by the master to monitor worker processes.

This signal system is central to how Gunicorn manages process lifecycle dynamically.

---

### Socket Creation and Binding

Gunicorn then creates socket objects for the configured addresses.

Socket sources may include:

* `--bind` (e.g., `127.0.0.1:8000`, `unix:/tmp/app.sock`)
* `fd://<FD>` file descriptors
* `systemd` socket activation
* `GUNICORN_FD` environment variable

Gunicorn automatically determines the socket type (TCP, IPv6, or Unix socket).
Socket wrapper classes are located in [gunicorn.sock](./source_ref/sock.py):

* [TCPSocket](./source_ref/sock.md#tcpsocket-class)
* [TCP6Socket](./source_ref/sock.md#tcp6socket-class)
* [UnixSocket](./source_ref/sock.md#unixsocket-class)

If SSL is configured, Gunicorn validates:

* `--keyfile`
* `--certfile`

It ensures files exist and are usable before proceeding.

If running under systemd, Gunicorn may notify systemd that it has successfully booted.

At this stage:

* Sockets are bound
* Sockets are listening
* But **no requests are accepted yet**

The bound sockets are stored in `Arbiter.LISTENERS`.

You now see messages like:

```
Listening at: http://127.0.0.1:8000 (pid)
```

Before spawning workers, Gunicorn:

* Calls the worker class `check_config()` method (if implemented)
* Invokes the `when_ready` server hook with the `Arbiter` instance

The master process is now fully initialized.

---

### Spawning Worker Processes

Still inside [Arbiter.run()](./source_ref/arbiter.md#arbiter-class-run-method), Gunicorn proceeds to create worker processes.

If `--workers 4` is specified, four child processes will be forked.

If `setproctitle` is installed, Gunicorn sets a readable process title.

**Each worker follows this creation steps:**

---

#### Worker Initialization and Forking

The worker class is instantiated in the master process.

Before forking:

* The `pre_fork` server hook is executed with:

  * The `Arbiter` instance
  * The initialized worker instance

Gunicorn then calls `os.fork()`.


#### In the Master Process

After forking:

* The worker instance is stored in the `WORKERS` dictionary.
* The key is the worker PID.
* The value is the worker instance.

The master now tracks the worker.


#### In the Worker Process (Child Process)

The child process performs several steps:

* Closes temporary files inherited from other workers.

* Sets the process title (if `setproctitle` is available).

* Logs:
You see message like:

  ```
  Booting worker with pid: <worker_pid>
  ```

* Executes the `post_fork` server hook.

* Calls the worker’s [init_process()](./source_ref/base_worker.md#base-worker-init_process-method) method.

Inside [init_process()](./source_ref/base_worker.md#base-worker-init_process-method):

* The worker sets up its internal state.
* Loads the WSGI application (if not preloaded).
* Starts its request handling loop.

At this point, the worker is fully operational and begins accepting client connections.

---

### Master Supervision Loop

After spawning all workers, the master process enters an infinite supervision loop.

This loop runs continuously until shutdown.

**Inside this loop, Gunicorn:**

---

#### Detects Orphaned Master Processes

In upgrade scenarios (such as `SIGUSR2` zero-downtime reload), a master process may become an orphan if its parent exits.

Gunicorn checks whether it has become orphaned and updates its metadata if necessary.

A process can be:

* A master of workers
* And simultaneously a child of another Gunicorn master (during binary upgrades)


#### Processes Pending Signals

Gunicorn maintains a `SIG_QUEUE`, which stores up to five pending signals.

If a signal exists:

* It is processed in FIFO order.
* The corresponding handler is executed.
* The master process is awakened via a pipe write operation.

If no signals are pending:

* The master sleeps for one second using `select()` on the pipe.

This mechanism avoids busy waiting while remaining responsive to signals.


#### Manages Worker Health

During each loop iteration, Gunicorn checks worker health.

If a worker dies or becomes unresponsive:

* The master terminates it.
* A replacement worker is spawned.

Worker liveness is monitored using a temporary file heartbeat mechanism:

* Each worker periodically updates the file’s timestamp.
* The master checks the last modification time.
* If the timestamp exceeds the configured timeout, the worker is considered stalled and is killed.

The worker’s `aborted` attribute helps determine whether the shutdown was expected or abnormal.


#### Maintains Desired Worker Count

Gunicorn ensures the number of active workers matches the configured `--workers` value.

If too few workers are running:

* New ones are spawned.

If too many:

* Extra workers are terminated.

---

This supervision cycle repeats continuously.

The master process listens, monitors, replaces, upgrades, reloads, and gracefully shuts down workers — all driven by signals and internal health checks.

[Next: signal handling](./4_signal_handling.md)
