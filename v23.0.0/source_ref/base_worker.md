## Base worker `__init__` method

**Path:** `gunicorn.workers.base.Worker.__init__` [Full file source code](./base_worker.py)

```python
def __init__(self, age, ppid, sockets, app, timeout, cfg, log):
    """\
    This is called pre-fork so it shouldn't do anything to the
    current process. If there's a need to make process wide
    changes you'll want to do that in ``self.init_process()``.
    """
    self.age = age
    self.pid = "[booting]"
    self.ppid = ppid
    self.sockets = sockets
    self.app = app
    self.timeout = timeout
    self.cfg = cfg
    self.booted = False
    self.aborted = False
    self.reloader = None

    self.nr = 0

    if cfg.max_requests > 0:
        jitter = randint(0, cfg.max_requests_jitter)
        self.max_requests = cfg.max_requests + jitter
    else:
        self.max_requests = sys.maxsize

    self.alive = True
    self.log = log
    self.tmp = WorkerTmp(cfg)
```


## Base worker init_process method

**Path:** `gunicorn.workers.base.Worker.init_process` [Full file source code](./base_worker.py)

```python
def init_process(self):
    """\
    If you override this method in a subclass, the last statement
    in the function should be to call this method with
    super().init_process() so that the ``run()`` loop is initiated.
    """
    # set environment' variables
    if self.cfg.env:
        for k, v in self.cfg.env.items():
            os.environ[k] = v

    util.set_owner_process(self.cfg.uid, self.cfg.gid,
                            initgroups=self.cfg.initgroups)

    # Reseed the random number generator
    util.seed()

    # For waking ourselves up
    self.PIPE = os.pipe()
    for p in self.PIPE:
        util.set_non_blocking(p)
        util.close_on_exec(p)

    # Prevent fd inheritance
    for s in self.sockets:
        util.close_on_exec(s)
    util.close_on_exec(self.tmp.fileno())

    self.wait_fds = self.sockets + [self.PIPE[0]]

    self.log.close_on_exec()

    self.init_signals()

    # start the reloader
    if self.cfg.reload:
        def changed(fname):
            self.log.info("Worker reloading: %s modified", fname)
            self.alive = False
            os.write(self.PIPE[1], b"1")
            self.cfg.worker_int(self)
            time.sleep(0.1)
            sys.exit(0)

        reloader_cls = reloader_engines[self.cfg.reload_engine]
        self.reloader = reloader_cls(extra_files=self.cfg.reload_extra_files,
                                        callback=changed)

    self.load_wsgi()
    if self.reloader:
        self.reloader.start()

    self.cfg.post_worker_init(self)

    # Enter main run loop
    self.booted = True
    self.run()
```