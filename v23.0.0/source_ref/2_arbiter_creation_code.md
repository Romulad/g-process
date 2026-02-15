## Application class `run` method

**Path:** `gunicorn.app.base.Application.run` [Full source code](./base_classes.py)

```python
def run(self):
    if self.cfg.print_config:
        print(self.cfg)

    if self.cfg.print_config or self.cfg.check_config:
        try:
            self.load()
        except Exception:
            msg = "\nError while loading the application:\n"
            print(msg, file=sys.stderr)
            traceback.print_exc()
            sys.stderr.flush()
            sys.exit(1)
        sys.exit(0)

    if self.cfg.spew:
        debug.spew()

    if self.cfg.daemon:
        if os.environ.get('NOTIFY_SOCKET'):
            msg = "Warning: you shouldn't specify `daemon = True`" \
                    " when launching by systemd with `Type = notify`"
            print(msg, file=sys.stderr, flush=True)

        util.daemonize(self.cfg.enable_stdio_inheritance)

    # set python paths
    if self.cfg.pythonpath:
        paths = self.cfg.pythonpath.split(",")
        for path in paths:
            pythonpath = os.path.abspath(path)
            if pythonpath not in sys.path:
                sys.path.insert(0, pythonpath)

    super().run()
```


## Base class `run` method

**Path:** `gunicorn.app.base.BaseApplication.run` [Full source code](./base_classes.py)

```python
def run(self):
    try:
        Arbiter(self).run()
    except RuntimeError as e:
        print("\nError: %s\n" % e, file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
```


## Arbiter class `__init__` method

**Path:** `gunicorn.arbiter.Arbiter.__init__` [Full source code](./arbiter.py)

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