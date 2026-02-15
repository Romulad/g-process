# From Configuration to Arbiter Instantiation

**Important:** **WsgiAppInstance** is the instance from [WSGIApplication](./source_ref/wsgi.py) initialization from [previous step](./1_startup_&_config_load.md)

At this stage, the `WsgiAppInstance` has already been created and its [run()](./source_ref/2_arbiter_creation_code.md#application-class-run-method) method is invoked.

The responsibility now shifts from *parsing and validating options* to *bootstrapping the server runtime*.

Let’s walk through what happens.

---

## Applying Configuration and Preparing the Runtime

When [WsgiAppInstance.run()](./source_ref/2_arbiter_creation_code.md#application-class-run-method) executes, Gunicorn performs several important actions before any worker process is spawned.

[See also base application run method](./source_ref/2_arbiter_creation_code.md#base-class-run-method)


### 🔎 Configuration-related behaviors

Depending on the CLI flags provided, Gunicorn may:

* Print a string representation of the config `cfg` when `--print-config` is specified.
* Dynamically load the WSGI application callable when `--check-config` or `--print-config` is used, in order to validate configuration and exit early.
* Enable execution tracing when `--spew` is set. This activates a Python tracer that prints every executed line of code to the console.
* Gunicorn runs in the background when you use `--daemon`
* If you specify `--pythonpath`, gunicorn add them to `sys.path`

Once configuration validation and optional debug behaviors are handled, Gunicorn proceeds to initialize the central controller of the server:

> The [Arbiter](./source_ref/arbiter.py)

The Arbiter is implemented in `gunicorn.arbiter` and represents the **master process controller**.

It is responsible for:

* Preparing the runtime environment
* Spawning worker processes (default: 1, configurable via `--workers`)
* Monitoring workers
* Handling system signals (reload, shutdown, scaling, etc.)

At this point, control moves from the application layer into the process management layer.

---

## Arbiter Initialization

The [Arbiter](./source_ref/arbiter.py) constructor receives the `WsgiAppInstance` as its main argument.

At this moment, the `WsgiAppInstance` contains:

* `usage` → `%(prog)s [OPTIONS] [APP_MODULE]`
* `cfg` → `Config(WsgiAppInstance.usage, WsgiAppInstance.prog)`
* `cfg.settings` → dictionary containing all Gunicorn configuration definitions
* `cfg.usage` → `%(prog)s [OPTIONS] [APP_MODULE]`
* `cfg.prog` → program filename
* `cfg.env_orig` → copy of the original environment (`os.environ.copy()`)
* `callable` → `None`
* `prog` → `None`
* `logger` → `None`
* `app_uri` → `app:app` (set during [load_config()](./source_ref/1_startup_&_config_load_code.md#wsgiapplication-class-load_config-method) inside [init()](./source_ref/1_startup_&_config_load_code.md#wsgiapplication-class-init-method) if using `gunicorn app:app`)


### What Happens Inside [Arbiter.__init__](./source_ref/2_arbiter_creation_code.md#arbiter-class-__init__-method)

During initialization, Gunicorn prepares the master process state.

The Arbiter:

#### 1️⃣ Stores Core References

* Stores the `WsgiAppInstance` in `self.app`
* Stores `WsgiAppInstance.cfg` in `self.cfg`

This gives the Arbiter full access to configuration and application metadata.


#### 2️⃣ Sets Up Logging

* Instantiates the configured logger
* Stores it in `self.log`
* The logger class can be customized using `--logger-class`


#### 3️⃣ Determines the Worker Class

* Resolves the worker implementation specified via `--worker-class`
* Stores the class object
* This class is responsible for:

  * Loading the WSGI app
  * Accepting client connections
  * Parsing HTTP requests
  * Calling the WSGI callable


#### 4️⃣ Parses Bind Addresses

* Reads the `--bind` configuration
* Parses host/port or Unix socket definitions
* Prepares sockets for later server startup


#### 5️⃣ Configures Worker Count

* Reads `--workers`
* Sets the number of worker processes to spawn
* Triggers `nworkers_changed` hook if defined


#### 6️⃣ Applies Runtime Settings

The Arbiter also configures:

* `--timeout` → Maximum time before a worker is killed and restarted
* `--name` → Process naming
* if you specify `--env`, they are set in the execution environment


#### 7️⃣ Optional Preloading (`--preload`)

If `--preload` is enabled:

* The WSGI callable is loaded **in the master process**
* The callable is stored in `WsgiAppInstance.callable`

Without `--preload`, each worker loads the application independently after forking.

---

## Summary of This Phase

At the end of this section:

* Configuration has been validated and applied.
* The Arbiter (master process controller) is instantiated.
* Logging, worker class, bind addresses, and runtime parameters are prepared.
* The system is now ready to transition into [server initialization and worker spawning](./3_server_initialization.md).
