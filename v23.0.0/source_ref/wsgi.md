## Run function

**Path:** `gunicorn.app.wsgiapp` [Full file source code](./wsgi.py) 

```python
def run(prog=None):
    """\
    The ``gunicorn`` command line runner for launching Gunicorn with
    generic WSGI applications.
    """
    from gunicorn.app.wsgiapp import WSGIApplication
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
```


## WSGIApplication class `load_config` method

**Path:** `gunicorn.app.wsgiapp.WSGIApplication.load_config` [Full file source code](./wsgi.py)

```python
def load_config(self):
    super().load_config()

    if self.app_uri is None:
        if self.cfg.wsgi_app is not None:
            self.app_uri = self.cfg.wsgi_app
        else:
            raise ConfigError("No application module specified.")
```


## WSGIApplication class `init` method

**Path:** `gunicorn.app.wsgiapp.WSGIApplication.init` [Full file source code](./wsgi.py)

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