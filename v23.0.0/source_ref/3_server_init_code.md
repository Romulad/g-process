## Arbiter class `run` method

**Path:** `gunicorn.arbiter.Arbiter.run` [Full source code](./arbiter.py)


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


## TCPSocket class

**Path:** `gunicorn.sock.TCPSocket` [Full source code](./sock.py)

```python
class TCPSocket(BaseSocket):

    FAMILY = socket.AF_INET

    def __str__(self):
        if self.conf.is_ssl:
            scheme = "https"
        else:
            scheme = "http"

        addr = self.sock.getsockname()
        return "%s://%s:%d" % (scheme, addr[0], addr[1])

    def set_options(self, sock, bound=False):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return super().set_options(sock, bound=bound)
```


## TCP6Socket class

**Path:** `gunicorn.sock.TCP6Socket` [Full source code](./sock.py)

```python
class TCP6Socket(TCPSocket):

    FAMILY = socket.AF_INET6

    def __str__(self):
        (host, port, _, _) = self.sock.getsockname()
        return "http://[%s]:%d" % (host, port)
```


## UnixSocket class

**Path:** `gunicorn.sock.UnixSocket` [Full source code](./sock.py)

```python
class UnixSocket(BaseSocket):

    FAMILY = socket.AF_UNIX

    def __init__(self, addr, conf, log, fd=None):
        if fd is None:
            try:
                st = os.stat(addr)
            except OSError as e:
                if e.args[0] != errno.ENOENT:
                    raise
            else:
                if stat.S_ISSOCK(st.st_mode):
                    os.remove(addr)
                else:
                    raise ValueError("%r is not a socket" % addr)
        super().__init__(addr, conf, log, fd=fd)

    def __str__(self):
        return "unix:%s" % self.cfg_addr

    def bind(self, sock):
        old_umask = os.umask(self.conf.umask)
        sock.bind(self.cfg_addr)
        util.chown(self.cfg_addr, self.conf.uid, self.conf.gid)
        os.umask(old_umask)
```


## Base worker init_process method

**Path:** `gunicorn.workers.base.Worker.init_process` [Full source code](./worker.py)

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