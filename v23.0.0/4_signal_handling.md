# Signal Handling in the Master Process

Gunicorn’s master process (the [Arbiter](./source_ref/arbiter.py)) is largely driven by Unix signals. Each signal triggers a specific handler that alters the server’s behavior — reloading configuration, scaling workers, shutting down, or performing zero-downtime upgrades.

Let’s walk through what each handler does and how it operates internally.

---

## `SIGHUP` — Reload Configuration

[Handler](./source_ref/4_signal_handling_code.md#sighup-signal-handler)

This signal tells Gunicorn to reload its configuration without stopping the service.

### What happens internally

* The master restores environment variables to their original state using `WsgiAppInstance.cfg.env_orig`.
  This removes any variables that were injected during runtime.

* Gunicorn reloads configuration from scratch by calling [do_load_config()](./source_ref/1_startup_&_config_load_code.md#base-class-do_load_config-method) again — essentially repeating the initialization phase that happens at startup.

* The [Arbiter](./source_ref/arbiter.py) instance is updated to reflect the new configuration:

  * The application instance (`app`)
  * The configuration object (`cfg`)
  * Worker class
  * Bind addresses
  * Worker count
  * Timeout values
  * Process name

* Environment variables defined with `--env` are reapplied.

* If `--preload` is enabled, the WSGI callable is imported again in the master process.

* If bind addresses changed, new listener sockets are created.

* The `on_reload` server hook is executed.

* The PID file is updated (or removed if no longer configured).

* If `setproctitle` is available, the process title is updated.

* New workers are spawned using the updated configuration.

Old workers continue serving requests during this transition.
Once the new workers are ready, Gunicorn gracefully scales down the old ones.

This ensures **zero downtime reloads**.

---

## `SIGQUIT` — Immediate Shutdown

[Handler](./source_ref/4_signal_handling_code.md#sigquit-signal-handler)

This signal triggers a controlled but quick shutdown.

### Execution flow

* All listener sockets stored in `Arbiter.LISTENERS` are closed.
* Unix socket files are removed if applicable.
* `SIGQUIT` is sent to all worker processes.
* The master waits up to `--graceful-timeout` seconds.
* If workers are still alive, `SIGKILL` is sent.

The master process then exits by raising `StopIteration`, which safely breaks the supervision loop.

During shutdown:

* A message like `Shutting down: Master` is logged.
* The PID file is removed.
* The `on_exit` hook is executed.

---

## `SIGINT` — Interrupt (Ctrl+C)

[Handler](./source_ref/4_signal_handling_code.md#sigint-signal-handler)

Behavior is identical to `SIGQUIT`.

Workers receive `SIGQUIT`, the master waits for the graceful timeout, and then forces termination if necessary.

---

## `SIGTERM` — Graceful Shutdown

[Handler](./source_ref/4_signal_handling_code.md#sigterm-signal-handler)

Very similar to `SIGQUIT`, but workers receive `SIGTERM` instead.

* Workers attempt a clean shutdown.
* The master waits up to `--graceful-timeout`.
* Remaining workers are forcefully killed.

---

## `SIGTTIN` — Increase Worker Count

[Handler](./source_ref/4_signal_handling_code.md#sigttin-signal-handler)

This signal scales the server up.

* The `num_workers` attribute is incremented.
* The master supervision loop detects the change.
* A new worker process is spawned.

---

## `SIGTTOU` — Decrease Worker Count

[Handler](./source_ref/4_signal_handling_code.md#sigttou-signal-handler)

This signal scales the server down.

* If `num_workers` is greater than one, it is decremented.
* The supervision loop reduces the number of active workers accordingly.

---

## `SIGUSR1` — Reopen Log Files

[Handler](./source_ref/4_signal_handling_code.md#sigusr1-signal-handler)

Used primarily during log rotation.

### What happens

* The master process reopens its log files.
* `SIGUSR1` is sent to all workers so they reopen their logs as well.

This allows safe log rotation without stopping the server.

---

## `SIGUSR2` — Zero-Downtime Binary Upgrade

[Handler](./source_ref/4_signal_handling_code.md#sigusr2-signal-handler)

It allows starting a new Gunicorn master process while keeping the old one alive.

Let’s call the current server **Server A** and the new one **Server B**.

### Execution flow

* Gunicorn checks whether the current master process handling the signal:

    * Has a **child** master process using the `reexec_pid` attribute
    * Or has a **master** master process using the `master_pid` attribute

* If it does, the signal is ignored.

* If no child master exists, Gunicorn forks a new process.

  * The child PID is stored in `reexec_pid`.
  * The parent (Server A) returns to normal operation.
  * The child continues execution.

In the child process:

* The `pre_exec` hook is called.

* The original environment (`env_orig`) is restored.

* Environment variables are updated:

  * `GUNICORN_PID` → stores the old master PID.
  * `LISTEN_PID`, `LISTEN_FDS` → for systemd socket reuse.
  * `GUNICORN_FD` → for non-systemd socket reuse.

* Gunicorn ensures it is in the correct working directory.

* `os.execvpe()` is called.

This effectively replaces the current program with a new Gunicorn process — just as if it were started from the command line — but reusing existing sockets.

Server B boots with its own workers while Server A continues running.
Once Server B is confirmed healthy, Server A can be terminated.

This enables **zero-downtime upgrades**.

---

## `SIGWINCH` — Stop Workers (Daemon Mode Only)

[Handler](./source_ref/4_signal_handling_code.md#sigwinch-signal-handler)

This signal is handled only when Gunicorn runs with `--daemon`.

* If not daemonized, the signal is ignored.
* If daemonized:

  * `num_workers` is set to zero.
  * `SIGTERM` is sent to all workers.

The master process continues running, but no workers remain — meaning no requests can be processed.

---

## `SIGCHLD` — Child Process Exit

[Handler](./source_ref/4_signal_handling_code.md#sigchld-signal-handler)

This signal is sent by the operating system when a child process exits.

Gunicorn uses it to prevent zombie processes.

### Execution flow

* Once the signal is receive, the master repeatedly calls:

  ```
  os.waitpid(-1, os.WNOHANG)
  ```

  This checks for exited child processes without blocking.

* If no child has exited, `(0, 0)` is returned.

* If a child exited, its PID and status code are returned.

* If no children exist, `ChildProcessError` is raised.

For each exited child:

* If the PID matches `reexec_pid`, it means the upgraded master exited.

  * `reexec_pid` is reset to `0`.

* Otherwise, Gunicorn determines why the worker exited:

  * Exit code `0` → Normal shutdown.
  * Exit code `3` → Worker failed to boot (server terminates).
  * Exit code `4` → Application failed to load (server terminates).
  * Other codes → Logged accordingly.
  * If terminated by a signal (e.g., `SIGTERM`), that is logged as well.

Finally:

* The worker is removed from `WORKERS`.
* Its temporary heartbeat file is closed.
* The `child_exit` hook is executed.

This loop continues until no more exited children remain.

---

## Summary

Signal handling is the control plane of Gunicorn’s master process.

Through signals, Gunicorn can:

* Reload configuration
* Scale workers up or down
* Rotate logs
* Perform graceful shutdowns
* Upgrade binaries without downtime
* Monitor and reap child processes

[Next](./5_base_worker.md), we move inside a worker process to see how it initializes and begins handling HTTP requests.
