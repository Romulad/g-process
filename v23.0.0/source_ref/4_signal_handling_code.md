## SIGHUP signal Handler

**Path:** `gunicorn.arbiter.handle_hup` [Full source code](./arbiter.py)

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

**Path:** `gunicorn.arbiter.handle_quit` [Full source code](./arbiter.py)

```python
def handle_quit(self):
    "SIGQUIT handling"
    self.stop(False)
    raise StopIteration
```


## SIGINT signal Handler

**Path:** `gunicorn.arbiter.handle_int` [Full source code](./arbiter.py)

```python
def handle_int(self):
    "SIGINT handling"
    self.stop(False)
    raise StopIteration
```


## SIGTERM signal Handler

**Path:** `gunicorn.arbiter.handle_term` [Full source code](./arbiter.py)

```python
def handle_term(self):
    "SIGTERM handling"
    raise StopIteration
```


## SIGTTIN signal Handler

**Path:** `gunicorn.arbiter.handle_ttin` [Full source code](./arbiter.py)

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

**Path:** `gunicorn.arbiter.handle_ttou` [Full source code](./arbiter.py)

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

**Path:** `gunicorn.arbiter.handle_usr1` [Full source code](./arbiter.py)

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

**Path:** `gunicorn.arbiter.handle_usr2` [Full source code](./arbiter.py)

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

**Path:** `gunicorn.arbiter.handle_winch` [Full source code](./arbiter.py)

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

**Path:** `gunicorn.arbiter.handle_chld` [Full source code](./arbiter.py)

```python
def handle_chld(self, sig, frame):
    "SIGCHLD handling"
    self.reap_workers()
    self.wakeup()
```
