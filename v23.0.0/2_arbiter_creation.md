
8 - From the previous step, the initialization of our `WsgiAppInstance` is complete and it `run` method
is called, here is where gunicorn handle applying config, launching all process needed and monitor the app.
Let't us see how!

After `WsgiAppInstance` initialization, it `run` method is called. Gunicorn check for config and apply them like:
    - print a string representation of the `WsgiAppInstance.cfg` object when you specify `--print-config`
    - dynamically load the wsgi application callable when you specify `--print-config` or `--check-config`
    to check the config validity and exit
    - setting up tracer to automatically print all code executed by the server if `--spew` is set. All 
    subsequents executed code will be print to the console
    - and so one...

Along with checking and apply configs, it initialize and run the arbiter located at `gunicorn/arbiter.py`.
Arbiter object is the class that setup the environement, start specified worker numbers with `--workers`
(default to 1) cli arg in their own process (child process) and monitor them through system signals handling.

9 - `Arbiter` for initialization take as argument the `WsgiAppInstance`, currently we have :

- `WsgiAppInstance.usage` = `%(prog)s [OPTIONS] [APP_MODULE]`
- `WsgiAppInstance.cfg` = `Config(WsgiAppInstance.usage, WsgiAppInstance.prog)`
- `WsgiAppInstance.cfg.settings` = `dict containing list of gunicorn config`
- `WsgiAppInstance.cfg.usage` = `%(prog)s [OPTIONS] [APP_MODULE]`
- `WsgiAppInstance.cfg.prog` = `program file name`
- `WsgiAppInstance.cfg.env_orig` = `current env variables copy with os.environ.copy()`
- `WsgiAppInstance.callable` = `None`
- `WsgiAppInstance.prog` = `None`
- `WsgiAppInstance.logger` = `None`
- `WsgiAppInstance.app_uri` = `app:app` # set during `load_config` call in `WsgiAppInstance` `init` (not `__init__`) method

During `Arbiter` initialization, gunicorn mainly:
- keep an instance to the `WsgiAppInstance` in an attribute `app` on the `Arbiter` instance
- keep an instance to the `WsgiAppInstance.cfg` in an `cfg` attribute on the `Arbiter` instance
- setup the logger that will be use in the server, set on the `Arbiter` instance `log` attribute. Can be customize with `--logger_class` option
- set the worker classe, the classe object that actually handle loading the wsgi app and incoming client requests. Can be customize with `--worker-class` option
- parse and set the bind address specify with `--bind`
- set worker numbers you specify with `--workers`, it triggers call to `nworkers_changed` callable
- set `--timeout` config, timeout before killing and restarting a worker
- set `--name` config
- set environment variables specify with `--env` option
- if `--preload` is provided, gunicorn load the wsgi callable and set it in `WsgiAppInstance.callable`
