# From CLI Invocation to Configuration Loading

## Class hierarchy involved

The execution path for a standard WSGI application follows this inheritance chain - from parent to child:

```
gunicorn.app.base.BaseApplication
        ↓
gunicorn.app.base.Application
        ↓
gunicorn.app.wsgiapp.WSGIApplication
```

When you run:

```bash
gunicorn [APP_MODULE] [OPTIONS]
```

Like: `gunicorn --workers 4 app:app`

Gunicorn internally uses [WSGIApplication](./source_ref/wsgi.py), which is a subclass of [Application](./source_ref/base_classes.py), itself a subclass of [BaseApplication](./source_ref/base_classes.py).

Understanding this hierarchy is important because initialization flows **from the most specific class down to the base class**, while configuration loading is orchestrated by the base class.

[Function runner](./source_ref/1_startup_&_config_load_code.md#run-function)

---

## WSGIApplication Initialization

When `WSGIApplication` is instantiated, its initialization ultimately enters the `__init__` method of `BaseApplication`.

This is where the foundational state of the application instance is created.

Inside [`BaseApplication.__init__`](./source_ref/1_startup_&_config_load_code.md#base-class-init-method), the following instance attributes are initialized:

* **usage**
  The CLI usage string (e.g. `%(prog)s [OPTIONS] [APP_MODULE]`).

* **cfg**
  Initially `None`. This will later hold an instance of [gunicorn.config.Config](./source_ref/config.py).

* **callable**
  Placeholder for the WSGI application callable (the object that receives `environ` and `start_response`).

* **prog**
  The program name (for example `gunicorn` when executed from the CLI).
  This is used in CLI help and usage messages.

* **logger**
  The logger instance used throughout the application lifecycle.

At this stage, the `WSGIApplication` instance state looks like this:

```
usage    = "%(prog)s [OPTIONS] [APP_MODULE]"
cfg      = None
callable = None
prog     = None
logger   = None
```

Once these attributes are initialized, the method [do_load_config()](./source_ref/1_startup_&_config_load_code.md#base-class-do_load_config-method) is called.

This method is defined in `BaseApplication` and is responsible for loading and validating configuration.

---

## Loading the Default Configuration

Inside [do_load_config()](./source_ref/1_startup_&_config_load_code.md#base-class-do_load_config-method), two important methods are triggered:

* [load_default_config()](./source_ref/1_startup_&_config_load_code.md#base-class-load_default_config-method)
* [load_config()](./source_ref/1_startup_&_config_load_code.md#base-class-load_config-method) (meant to be implemented or extended by subclasses)

The first step is [load_default_config()](./source_ref/1_startup_&_config_load_code.md#base-class-load_default_config-method).

This method sets the `cfg` attribute to an instance of `gunicorn.config.Config`.

After this call, the application instance changes state:

```
usage    = "%(prog)s [OPTIONS] [APP_MODULE]"
cfg      = Config(usage, prog)
callable = None
prog     = prog
logger   = None
```

The [Config](./source_ref/config.py) object is central to Gunicorn’s configuration system. It loads all supported settings and their default values.

The `Config` instance stored in `cfg` contains:

* **settings**
  A dictionary of all available Gunicorn settings.
  Each entry maps a setting name (e.g. `bind`) to a configuration class instance (e.g. an instance of `gunicorn.config.Bind`).
  These configuration classes are automatically registered via Python metaclasses.

* **usage**
  The CLI usage string passed during initialization.

* **prog**
  The program name (or `os.path.basename(sys.argv[0])` if not explicitly set).

* **env_orig**
  A copy of the original environment variables.

At this point, the `WSGIApplication` instance now holds a fully initialized configuration object containing **all default settings**.

---

## Loading and Overriding User Configuration

After default configuration is established, [load_config()](./source_ref/1_startup_&_config_load_code.md#base-class-load_config-method) is executed.

The purpose of this method is described in Gunicorn’s own documentation:

> This method is used to load the configuration from one or several input(s): custom command line, configuration file. You have to override this method in your class.

`WSGIApplication` overrides [load_config()](./source_ref/1_startup_&_config_load_code.md#wsgiapplication-class-load_config-method) and calls [super().load_config()](./source_ref/1_startup_&_config_load_code.md#application-class-load_config-method) to reuse the implementation provided by `Application`.

[Remember the class hierarchy?](#class-hierarchy-involved)

So what does [load_config()](./source_ref/1_startup_&_config_load_code.md#wsgiapplication-class-load_config-method) actually do?

First, it constructs the default CLI argument parser using Python’s built-in `argparse`.
This parser is dynamically built to include **all available Gunicorn settings**.

Next, it optionally calls an [init()](./source_ref/1_startup_&_config_load_code.md#base-class-init-method) method.

This allows subclasses to apply custom logic.

In the case of `WSGIApplication`, the [init()](./source_ref/1_startup_&_config_load_code.md#wsgiapplication-class-init-method) method extracts the application path you provide in the CLI (`module:callable`) and stores it in an attribute called `app_uri`.

After that, Gunicorn checks for configuration overrides from multiple sources, applied in increasing order of priority:

* App/Framework-specific settings
* Configuration file
* `GUNICORN_CMD_ARGS` environment variable
* Command-line arguments

If provided, these values override the defaults loaded earlier.

At the end of [load_config()](./source_ref/1_startup_&_config_load_code.md#wsgiapplication-class-load_config-method), the `cfg.settings` dictionary becomes the **source of truth** for the rest of the application lifecycle.

Every subsequent phase — including arbiter creation, worker spawning, and request handling — reads configuration values from this object.

---

## Where This Leads Next

At this stage:

* The application instance is created.
* Default configuration is loaded.
* User-provided configuration is validated.
* The WSGI app path is known.
* The configuration object is fully populated.

The next step in the execution flow is the transition from configuration loading to **arbiter creation inside the master process (current python process)**, which is where the server lifecycle truly begins.