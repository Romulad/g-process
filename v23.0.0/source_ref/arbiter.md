## Arbiter class `__init__` method

**Path:** `gunicorn.arbiter.Arbiter.__init__` [Full file source code](./arbiter.py)

```python
def __init__(self, app):
    os.environ["SERVER_SOFTWARE"] = SERVER_SOFTWARE

    self._num_workers = None
    self._last_logged_active_worker_count = None
    self.log = None

    self.setup(app)

    self.pidfile = None
    self.systemd = False
    self.worker_age = 0
    self.reexec_pid = 0
    self.master_pid = 0
    self.master_name = "Master"

    cwd = util.getcwd()

    args = sys.argv[:]
    args.insert(0, sys.executable)

    # init start context
    self.START_CTX = {
        "args": args,
        "cwd": cwd,
        0: sys.executable
    }
```


## Arbiter class `run` method

**Path:** `gunicorn.arbiter.Arbiter.run` [Full file source code](./arbiter.py)


```python
def run(self):
    "Main master loop."
    self.start()
    util._setproctitle("master [%s]" % self.proc_name)

    try:
        self.manage_workers()

        while True:
            self.maybe_promote_master()

            sig = self.SIG_QUEUE.pop(0) if self.SIG_QUEUE else None
            if sig is None:
                self.sleep()
                self.murder_workers()
                self.manage_workers()
                continue

            if sig not in self.SIG_NAMES:
                self.log.info("Ignoring unknown signal: %s", sig)
                continue

            signame = self.SIG_NAMES.get(sig)
            handler = getattr(self, "handle_%s" % signame, None)
            if not handler:
                self.log.error("Unhandled signal: %s", signame)
                continue
            self.log.info("Handling signal: %s", signame)
            handler()
            self.wakeup()
    except (StopIteration, KeyboardInterrupt):
        self.halt()
    except HaltServer as inst:
        self.halt(reason=inst.reason, exit_status=inst.exit_status)
    except SystemExit:
        raise
    except Exception:
        self.log.error("Unhandled exception in main loop",
                        exc_info=True)
        self.stop(False)
        if self.pidfile is not None:
            self.pidfile.unlink()
        sys.exit(-1)
```


## Arbiter class `spawn_worker` method

**Path:** `gunicorn.arbiter.Arbiter.spawn_worker` [Full file source code](./arbiter.py)


```python
def spawn_worker(self):
    self.worker_age += 1
    worker = self.worker_class(self.worker_age, self.pid, self.LISTENERS,
                                self.app, self.timeout / 2.0,
                                self.cfg, self.log)
    self.cfg.pre_fork(self, worker)
    pid = os.fork()
    if pid != 0:
        worker.pid = pid
        self.WORKERS[pid] = worker
        return pid

    # Do not inherit the temporary files of other workers
    for sibling in self.WORKERS.values():
        sibling.tmp.close()

    # Process Child
    worker.pid = os.getpid()
    try:
        util._setproctitle("worker [%s]" % self.proc_name)
        self.log.info("Booting worker with pid: %s", worker.pid)
        self.cfg.post_fork(self, worker)
        worker.init_process()
        sys.exit(0)
    except SystemExit:
        raise
    except AppImportError as e:
        self.log.debug("Exception while loading the application",
                        exc_info=True)
        print("%s" % e, file=sys.stderr)
        sys.stderr.flush()
        sys.exit(self.APP_LOAD_ERROR)
    except Exception:
        self.log.exception("Exception in worker process")
        if not worker.booted:
            sys.exit(self.WORKER_BOOT_ERROR)
        sys.exit(-1)
    finally:
        self.log.info("Worker exiting (pid: %s)", worker.pid)
        try:
            worker.tmp.close()
            self.cfg.worker_exit(self, worker)
        except Exception:
            self.log.warning("Exception during worker exit:\n%s",
                                traceback.format_exc())
```


## SIGHUP signal Handler

**Path:** `gunicorn.arbiter.handle_hup` [Full file source code](./arbiter.py)

```python
def handle_hup(self):
    """\
    HUP handling.
    - Reload configuration
    - Start the new worker processes with a new configuration
    - Gracefully shutdown the old worker processes
    """
    self.log.info("Hang up: %s", self.master_name)
    self.reload()
```


## SIGQUIT signal Handler

**Path:** `gunicorn.arbiter.handle_quit` [Full file source code](./arbiter.py)

```python
def handle_quit(self):
    "SIGQUIT handling"
    self.stop(False)
    raise StopIteration
```


## SIGINT signal Handler

**Path:** `gunicorn.arbiter.handle_int` [Full file source code](./arbiter.py)

```python
def handle_int(self):
    "SIGINT handling"
    self.stop(False)
    raise StopIteration
```


## SIGTERM signal Handler

**Path:** `gunicorn.arbiter.handle_term` [Full file source code](./arbiter.py)

```python
def handle_term(self):
    "SIGTERM handling"
    raise StopIteration
```


## SIGTTIN signal Handler

**Path:** `gunicorn.arbiter.handle_ttin` [Full file source code](./arbiter.py)

```python
def handle_ttin(self):
    """\
    SIGTTIN handling.
    Increases the number of workers by one.
    """
    self.num_workers += 1
    self.manage_workers()
```


## SIGTTOU signal Handler

**Path:** `gunicorn.arbiter.handle_ttou` [Full file source code](./arbiter.py)

```python
def handle_ttou(self):
    """\
    SIGTTOU handling.
    Decreases the number of workers by one.
    """
    if self.num_workers <= 1:
        return
    self.num_workers -= 1
    self.manage_workers()
```


## SIGUSR1 signal Handler

**Path:** `gunicorn.arbiter.handle_usr1` [Full file source code](./arbiter.py)

```python
def handle_usr1(self):
    """\
    SIGUSR1 handling.
    Kill all workers by sending them a SIGUSR1
    """
    self.log.reopen_files()
    self.kill_workers(signal.SIGUSR1)
```


## SIGUSR2 signal Handler

**Path:** `gunicorn.arbiter.handle_usr2` [Full file source code](./arbiter.py)

```python
def handle_usr2(self):
    """\
    SIGUSR2 handling.
    Creates a new arbiter/worker set as a fork of the current
    arbiter without affecting old workers. Use this to do live
    deployment with the ability to backout a change.
    """
    self.reexec()
```


## SIGWINCH signal Handler

**Path:** `gunicorn.arbiter.handle_winch` [Full file source code](./arbiter.py)

```python
def handle_winch(self):
    """SIGWINCH handling"""
    if self.cfg.daemon:
        self.log.info("graceful stop of workers")
        self.num_workers = 0
        self.kill_workers(signal.SIGTERM)
    else:
        self.log.debug("SIGWINCH ignored. Not daemonized")
```


## SIGCHLD signal Handler

**Path:** `gunicorn.arbiter.handle_chld` [Full file source code](./arbiter.py)

```python
def handle_chld(self, sig, frame):
    "SIGCHLD handling"
    self.reap_workers()
    self.wakeup()
```
