## Run function

**Path:** `gunicorn.app.wsgiapp` [Full source code](./wsgi.py) 

```python
def run(prog=None):
    """\
    The ``gunicorn`` command line runner for launching Gunicorn with
    generic WSGI applications.
    """
    from gunicorn.app.wsgiapp import WSGIApplication
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
```

## Base class `__init__` method

**Path:** `gunicorn.app.base.BaseApplication.__init__` [Full source code](./base_classes.py) 

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

**Path:** `gunicorn.app.base.BaseApplication.do_load_config` [Full source code](./base_classes.py) 

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

**Path:** `gunicorn.app.base.BaseApplication.load_default_config` [Full source code](./base_classes.py) 

```python
def load_default_config(self):
    # init configuration
    self.cfg = Config(self.usage, prog=self.prog)
```


## Base class `load_config` method

**Path:** `gunicorn.app.base.BaseApplication.load_config` [Full source code](./base_classes.py) 

```python
def load_config(self):
    """
    This method is used to load the configuration from one or several input(s).
    Custom Command line, configuration file.
    You have to override this method in your class.
    """
    raise NotImplementedError
```


## WSGIApplication class `load_config` method

**Path:** `gunicorn.app.wsgiapp.WSGIApplication.load_config` [Full source code](./wsgi.py)

```python
def load_config(self):
    super().load_config()

    if self.app_uri is None:
        if self.cfg.wsgi_app is not None:
            self.app_uri = self.cfg.wsgi_app
        else:
            raise ConfigError("No application module specified.")
```


## Application class `load_config` method

**Path:** `gunicorn.app.base.Application.load_config` [Full source code](./base_classes.py) 

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

**Path:** `gunicorn.app.base.BaseApplication.init` [Full source code](./base_classes.py) 

```python
def init(self, parser, opts, args):
    raise NotImplementedError
```


## WSGIApplication class `init` method

**Path:** `gunicorn.app.wsgiapp.WSGIApplication.init` [Full source code](./wsgi.py)

```python
def init(self, parser, opts, args):
    self.app_uri = None

    if opts.paste:
        from .pasterapp import has_logging_config

        config_uri = os.path.abspath(opts.paste)
        config_file = config_uri.split('#')[0]

        if not os.path.exists(config_file):
            raise ConfigError("%r not found" % config_file)

        self.cfg.set("default_proc_name", config_file)
        self.app_uri = config_uri

        if has_logging_config(config_file):
            self.cfg.set("logconfig", config_file)

        return

    if len(args) > 0:
        self.cfg.set("default_proc_name", args[0])
        self.app_uri = args[0]
```