## Base class `__init__` method

**Path:** `gunicorn.app.base.BaseApplication.__init__` [Full file source code](./base_classes.py) 

```python
def __init__(self, usage=None, prog=None):
    self.usage = usage
    self.cfg = None
    self.callable = None
    self.prog = prog
    self.logger = None
    self.do_load_config()
```

## Base class `do_load_config` method

**Path:** `gunicorn.app.base.BaseApplication.do_load_config` [Full file source code](./base_classes.py) 

```python
def do_load_config(self):
    """
    Loads the configuration
    """
    try:
        self.load_default_config()
        self.load_config()
    except Exception as e:
        print("\nError: %s" % str(e), file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
```

## Base class `load_default_config` method

**Path:** `gunicorn.app.base.BaseApplication.load_default_config` [Full file source code](./base_classes.py) 

```python
def load_default_config(self):
    # init configuration
    self.cfg = Config(self.usage, prog=self.prog)
```


## Base class `load_config` method

**Path:** `gunicorn.app.base.BaseApplication.load_config` [Full file source code](./base_classes.py) 

```python
def load_config(self):
    """
    This method is used to load the configuration from one or several input(s).
    Custom Command line, configuration file.
    You have to override this method in your class.
    """
    raise NotImplementedError
```

## Application class `load_config` method

**Path:** `gunicorn.app.base.Application.load_config` [Full file source code](./base_classes.py) 

```python
def load_config(self):
    # parse console args
    parser = self.cfg.parser()
    args = parser.parse_args()

    # optional settings from apps
    cfg = self.init(parser, args, args.args)

    # set up import paths and follow symlinks
    self.chdir()

    # Load up the any app specific configuration
    if cfg:
        for k, v in cfg.items():
            self.cfg.set(k.lower(), v)

    env_args = parser.parse_args(self.cfg.get_cmd_args_from_env())

    if args.config:
        self.load_config_from_file(args.config)
    elif env_args.config:
        self.load_config_from_file(env_args.config)
    else:
        default_config = get_default_config_file()
        if default_config is not None:
            self.load_config_from_file(default_config)

    # Load up environment configuration
    for k, v in vars(env_args).items():
        if v is None:
            continue
        if k == "args":
            continue
        self.cfg.set(k.lower(), v)

    # Lastly, update the configuration with any command line settings.
    for k, v in vars(args).items():
        if v is None:
            continue
        if k == "args":
            continue
        self.cfg.set(k.lower(), v)

    # current directory might be changed by the config now
    # set up import paths and follow symlinks
    self.chdir()
```


## Base class `init` method

**Path:** `gunicorn.app.base.BaseApplication.init` [Full file source code](./base_classes.py) 

```python
def init(self, parser, opts, args):
    raise NotImplementedError
```


## Application class `run` method

**Path:** `gunicorn.app.base.Application.run` [Full file source code](./base_classes.py)

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

**Path:** `gunicorn.app.base.BaseApplication.run` [Full file source code](./base_classes.py)

```python
def run(self):
    try:
        Arbiter(self).run()
    except RuntimeError as e:
        print("\nError: %s\n" % e, file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
```