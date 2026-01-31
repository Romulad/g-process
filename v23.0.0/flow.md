# Gunicorn server

## Classes structure

Structure used (from parent to child classes): 
`gunicorn.app.base.BaseApplication` -> `gunicorn.app.base.Application` -> `gunicorn.app.wsgiapp.WSGIApplication`

**Note**: Gunicorn version: 23.0.0

TODO: Clarification: Gunicorn, worker

## Execution flow

1 - From : `gunicorn [OPTIONS] [APP_MODULE]` with `gunicorn.app.wsgiapp.WSGIApplication` as base class
and subclasse of `gunicorn.app.base.Application`

2 - `gunicorn.app.wsgiapp.WSGIApplication` initialization

3 - After `gunicorn.app.base.Application` WSGIApplication initialization we enter in `gunicorn.app.base.BaseApplication` `__init__` method

4 - In `gunicorn.app.base.BaseApplication` `__init__` method, these variables are initialize:
- `usage`:
    - `usage` is the cmd line interface usage message like `gunicorn [OPTIONS] [APP_MODULE]`
- `cfg`:
    - this variable will contain the config object from `gunicorn.config.Config`,
- `callable`:
    - use to store the wsgi application callable, the one that accept `environ` and `start_response` as arg
- `prog`:
    - this store the program name or the file from where the program start like `gunicorn` when
    running the `gunicorn` command directly. Use in `usage` for cmd line interface
- `logger`:
    - the logger that will be use for logging in the application

These variables are initialize on the `WSGIApplication` class instance. `WsgiAppInstance` state become:
- `WsgiAppInstance.usage` = `%(prog)s [OPTIONS] [APP_MODULE]`
- `WsgiAppInstance.cfg` = `None`
- `WsgiAppInstance.callable` = `None`
- `WsgiAppInstance.prog` = `None`
- `WsgiAppInstance.logger` = `None`

After the variables set on `WsgiAppInstance`, the method `do_load_config` is called. It available
on `gunicorn.app.base.BaseApplication` and it is responsible of initialize/loading 
the app configs/settings

5 - From `gunicorn.app.base.BaseApplication` `__init__` calle to `do_load_config` trigger two method
- `load_default_config` from `gunicorn.app.base.BaseApplication`
- `load_config` from `gunicorn.app.base.BaseApplication` but need to be implemented by the child class
which is in our case the `WsgiAppInstance`

6 - `load_default_config` update the instance variable `cfg` on the `WsgiAppInstance` to be an
instance of `gunicorn.config.Config`. The `Config` class load all gunicorn default and accepted 
config. So after call to `load_default_config` method the `WsgiAppInstance` become:
- `WsgiAppInstance.usage` = `%(prog)s [OPTIONS] [APP_MODULE]`
- `WsgiAppInstance.cfg` = `Config(WsgiAppInstance.usage, WsgiAppInstance.prog)`
- `WsgiAppInstance.callable` = `None`
- `WsgiAppInstance.prog` = `prog`
- `WsgiAppInstance.logger` = `None`

The `Config` instance store in the `WsgiAppInstance.cfg` will have as instance attrs:
- `settings`:
    - It is the settings object containing the list of config/setting available in
    gunicorn. It is a dict with key the name of the setting like `bind` and as value a class
    object instance representing the config like an instance of `gunicorn.config.Bind`. Those classes are
    automatically registered using python metaclasse.
- `usage`:
    - `usage` string passed to the `Config` classe
- `prog`: 
    - `prog` passe to th `Config` classe if exists or `os.path.basename(sys.argv[0])` is set
- `env_orig`:
    - contain copy of the current environment variables

So after the `Config` classe initialization our `WsgiAppInstance` state become:
- `WsgiAppInstance.usage` = `%(prog)s [OPTIONS] [APP_MODULE]`
- `WsgiAppInstance.cfg` = `Config(WsgiAppInstance.usage, WsgiAppInstance.prog)`
- `WsgiAppInstance.cfg.settings` = `dict containing list of gunicorn config`
- `WsgiAppInstance.cfg.usage` = `%(prog)s [OPTIONS] [APP_MODULE]`
- `WsgiAppInstance.cfg.prog` = `program file name`
- `WsgiAppInstance.cfg.env_orig` = `current env variables copy with os.environ.copy()`
- `WsgiAppInstance.callable` = `None`
- `WsgiAppInstance.prog` = `prog`
- `WsgiAppInstance.logger` = `None`

7 - Then `load_config` is called in the `do_load_config` method from `gunicorn.app.base.BaseApplication` `__init__`. 
Gunicorn say: 
```text
    This method is used to load the configuration from one or several input(s).
    Custom Command line, configuration file. You have to override this method in your class.
```
This method is used to load/validate and set user provided config. If the child overriding the method doesn't change anything then Gunicorn default config will be used. Our `WsgiAppInstance` classe implement the `load_config` and in it, it calls `super().load_config()` with additional check after super calle. Here
super object is `gunicorn.app.base.Application` which implement the `load_config` method too.

[Remember our tree](#classes-structure)

So what does `load_config` do?

- Get the default cli arg parser which is dynamically construct to include all available and supported 
gunicorn settings/cli-options. Gunicorn use python bulltin `argparse`.
- call a optional `init` method of the child classe to let it apply custom logique, based on the `parser` 
and `argument` and optionally return a dict object (can be none)  containing config that should be override or set. e.g. Our `WsgiAppInstance` `init` method set the wsgi app callable path, the one you set with
`module:callable` in the cli; the path is set in an attribute called `app_uri`.
- gunicorn then check for config from diffrent possible user provided source 
(lower-priority to higher-priority):
    - Environment Variables
    - Framework Settings
    - Configuration File
    - GUNICORN_CMD_ARGS environment variable named
    - Command Line
Those configs, if provided override the default gunicorn config/settings. 

After the `load_config` call, `WsgiAppInstance.cfg.settings` will be use as the source of truth to read config from for the rest of the application that will be trigger by the `run` method on our `WsgiAppInstance`.

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

10 - After `Arbiter` initialization, it `run` method is called and you get the message 
`Starting gunicorn <guniron_version>`. 

The `run` method on the `Arbiter` instance is the one that:

- create PID file that contain gunicorn master process PID when you use the option `--pid`, the object
managing the PID file is set on an instance attribute called `pidfile`
- call the server hook `on_starting`(callable) specified in your config with an instance of the `Arbiter` object, so the _server_
- setup handlers to listen to signal events:
    - `SIGHUP`: 
        Reload the configuration, start the new worker processes with a new configuration and      gracefully shutdown older workers. If the application is not preloaded (using the preload_app option), Gunicorn will also load the new version of it.
    - `SIGQUIT`, `SIGINT`: 
        Quick shutdown
    - `SIGTERM`: 
        Graceful shutdown. Waits for workers to finish their current requests up to 
        the graceful_timeout --graceful-timeout.
    - `SIGTTIN`: 
        Increment the number of worker processes by one
    - `SIGTTOU`: 
        Decrement the number of worker processes by one
    - `SIGUSR1`: 
        Reopen the log files
    - `SIGUSR2`: 
        Upgrade Gunicorn on the fly. A separate TERM signal should be used to kill the old master process. This signal can also be used to use the new versions of pre-loaded applications. See Upgrading to a new binary on the fly for more information.
    - `SIGWINCH`: 
        Gracefully shutdown the worker processes when Gunicorn is daemonized.
    - `SIGCHLD`: 
        Sent to the master process when a worker process terminates or stops. Gunicorn uses this signal to monitor and manage worker processes.
- create socket objects for the configured addresses or file descriptors; gunicorn read file descriptors from your option `--bind fd://<FD>`, `systemd` and `GUNICORN_FD` env variable. Gunicorn dynamically determine the socket type to use based on addresses or file descriptors, TCP socket or unix socket. The interfaces that wrap a type of socket object and used throughout the app is located at `gunicorn.sock`:
    - `gunicorn.sock.TCPSocket`
    - `gunicorn.sock.TCP6Socket`
    - `gunicorn.sock.UnixSocket`
- gunicorn validate provided info about ssl certification, mainly check if value specify with `--keyfile`, 
`--certfile` are validate; if the files exist
- gunicorn optionally send notification to systemd if running as service to notify it's booted.

Gunicorn is booted at this stage meanning the socket object(s) are bound to the address(es) and 
are listening but not accepting requests yet. This last step, _accepting requests_, is handle in the worker processe(s) that we shall see.

The bound sockets are store in an attribute called `LISTENERS` as an array on the `Arbiter` object instance.

It is from there you have the message `Listening at <address:port> <gunicorn_pid>` .etc. Gunicorn also check
if the worker class has a `check_config` method and then call it with the server config and logger object; it at this stage before spawning workers, gunicorn call the server hook `when_ready` with the `Arbiter` instance object, so the _server_.

11 - We'are still in the `Arbiter` instance `run` method and after the previous step, gunicorn tries 
to set the process title if you have `setproctitle` installed.

Then gunicorn start the number of workers specified with `--workers` option.

If `--workers 4`, 4 workers will be start in different child processes, each of them follow this process:
    - after `__init__` call of the worker class through class initiliazation, gunicorn call the `pre_fork` server hook callable with an instance of the server (`Arbiter`) instance and the current initialized worker. A new child process is created by gunicorn with `os.fork` call:
        - In the current process _aka the master process_ gunicorn store in an instance attribute called `WORKERS` as dict the new worker initialized; the key is the worker process PID and as value the worker intance
        - in the worker process _aka the child process_ gunicorn: 
            - first close all other workers (if any) temp file in the current new worker process as a new process inherit the execution environement of it parent process. The temp file as we will see is used between a gunicorn worker and the gunicorn master process to check if the worker in the child process is still running.
            - set the the worker process title if you have `setproctitle` installed
            - log the message `Booting worker with pid: <worker PID>`
            - call the `post_fork` server hook callable with an instance of the server (`Arbiter`) instance and the current
            initialized worker. This call is happening in the worker process, so the child process of gunicorn master process
            - the worker class `init_process` method is called, it setup the worker and _run_ it
            - from there the worker instance _initialized_, _setup_ and _runing_ in the child process can start accepting requests.

After starting the needed workers in different processes, gunicorn enter in an infinite while loop, where it constantly:
    - check if the current process, acting as master process to the worker processes, is not an orphan process, if its then gunicorn update _metadata_ to make it as new master process.
    As it sound an Orphan process is a process whose it parent process is not running anymore, 
    exited or kill in some way but the a process it forked still alive, so an orphan process. This can
    happen when gunicorn receive a `SIGUSR2`, asking him to `Upgrading to a new binary on the fly` without any service downtime.
    **Note**: A process can be a master process to worker processes and also a child process for another gunicorn master process.
    - check the an instance variable `SIG_QUEUE`, which keep a list of maximum 5 signals sent by the os. 
    Gunicorn check if a signal exists in the list and take the first if so, following FIFO principle.
    A signal exists? Then gunicorn call the appropriate handler to handle it and then _wake up_ the master
    process by writting to a pipe. Writting to the pipe write end help processing the next signal if exists in the `SIG_QUEUE` immediatly as gunicorn sleep for 1 second with `select` on the pipe read end when no signal exists.
    - from the last step if no signal exists, then gunicorn, sleep for 1 second using `select` with 1 second
    timeout, murder and manage workers meaning:
        - check if amongst forked workers if any of them died or is not responding anymore, if so terminate the worker process. Gunicorn check an attribute called `aborted` on the worker class instance to see if it `True` meaning the worker is somehow aware that it died otherwise it means something unexpected
        happened.
        **Info**: To check if a worker is died or no responding, gunicorn use an artificial write to file
        mechanisme. The worker process manually update _last modified_ and _last accessed_ time of a tempory file after a certain amount of time. Then the master process running the `Arbiter` (gunicorn server)
        check the last modified of the temp file if it within a time interval limit otherwise terminate the worker process so the worker.
        - during managing workers, gunicorn create or kill workers based on the `--workers` config provided
    - then it restart this same process again.... until you exit

12 - Now let'us look at what each signal handler does

- `SIGHUP`: 
    Reload the configuration, start the new worker processes with a new configuration and gracefully shutdown older workers.

    Handler execution flow:
        - Gunicorn reset environment variable to it original form before it execution. 
        Recall this `WsgiAppInstance.cfg.env_orig` ? It is that reference that is used to restore the
        env variables and remove other variables set by gunicorn during execution
        - Then gunicorn reload the configuration from scratch, with a call to `do_load_config` saw earlier.
        It like when gunicorn first initialize, those are steps from 1 to 7 in this article, just before 
        calling the  `WsgiAppInstance` `run` method. 
        - The next step executed by gunicorn is to update the `Arbiter` instance with the new config loaded.
        The `Arbiter`, the server, is update to reflect the new config loaded: 
            - the app obj instance `app`
            - the config (`gunicorn.config.Config`) object instance `cfg`
            - worker class `worker_class`
            - address `address`
            - worker count `num_workers`
            - timeout setting for gracefull shutdown `timeout`
            - the process name `proc_name`
        are updated on the server instance. Additionally gunicorn update the environment variables
        with  `--env` you provided and load (import) the wsgi callable if `--preload` option.
        - Gunicorn then check if the address has changed, if so it create new listeners (sockets)
        - call the server hook `on_reload`
        - update PID file if specify in you new config otherwise delete it if exists
        - update the process name if `setproctitle` is installed
        - spawn new workers based on `--workers` config available in you new loaded config
        - So far old workers still accepting request so you app is still running, the last step in the 
        process is to regulate workers count to reflect you new config

    And that's for `SIGHUP`.

- `SIGQUIT`:
    Sending this signal, stop worker processes by sending them a `SIGQUIT` signal, wait for gracefull timeout set with `--graceful-timeout`, then force worker to exit if still alive.

    Handler execution flow:
        - Gunicorn start by closing all sockets obj available in the list instance variable called 
        `LISTENERS` on the `Arbiter` in the master process, also it delete all unix socket endpoint if available.
        - Send `SIGQUIT` to the worker processes and wait for `--graceful-timeout` for the worker to exit.
        Then send a `SIGKILL` to force exit if still running
        - But there is one thing still running, right? Gunicorn master process, the `Arbiter` (server) instance. To exit gunicorn raise `StopIteration` to quit the main loop describe earlier, which is safely caught and Gunicorn stoped. During that phase:
            - you get a message like `Shutting down: Master`
            - gunicorn remove PID file if available
            - call the server hook `on_exit`

- `SIGINT`:
    Stop worker processes by sending them a `SIGQUIT` signal, wait for gracefull timeout set with
    `--graceful-timeout`, then force worker to exit if still alive.

    Handler execution flow: Exact same process as `SIGQUIT`.

- `SIGTERM`:
    Stop worker processes by sending them a `SIGTERM` signal, wait for gracefull timeout set with
    `--graceful-timeout`, then force worker to exit if still alive.

    Handler execution flow: Exact same process as `SIGQUIT` but only with `SIGTERM` send to workers.

- `SIGTTIN`:
    Increases the number of workers by one.

    Handler execution flow: 
        - Increment the instance variable `num_workers` by one
        - then manage workers as describe earlier

- `SIGTTOU`:
    Decreases the number of workers by one.

    Handler execution flow:
        - check if `num_workers` is at least greater than one and decrement the variable by one
        - then manage workers as describe earlier

- `SIGUSR1`:
    When receive this signal, Gunicorn reopen log files and instruct child worker processes 
    to do the same.

    Handler execution flow:
        - Gunicorn reopen the master process log files
        - send `SIGUSR1` to worker processes to do the same.
        **PS**: The effective use of this by Gunicorn is when you start a new gunicorn binary or reloading
        configuration. Probably it a way gunicorn allow user to reopen log files if needed.

- `SIGUSR2`:
    With this signal, Gunicorn keep the current running server with it worker processes, let call it `server_a`, and create a new one lets call it `server_b` same as `server_a` in a new child process. It like starting a new server with it own worker processes and keep the old server active and running.

    Handler execution flow:
        - Gunicorn start by checking if in `server_a`, we've created a `server_b`(child master process) already and ignore the signal. Likewise if `server_b` already exists and the signal is sent to it, it checks if `server_a`(master process, old server) exists and ignore the signal as well.
        - If the `server_a`doesn't have a child master process or the `server_b` exists but without a 
        master process then the execution flow continue
        - gunicorn create a new process with `os.fork()` and set the forked process PID in an instance variable called `reexec_pid` (default value is 0) which is use in the previous step to allow `server_a` to check if a child master process `server_b` already exist. From there `server_a` return
        from the function and the new child created `server_b` continue it execution.
        - In the child process gunicorn start by calling the server hook `pre_exec` with the server instance
        `Arbiter`
        - Copy the default, no modified env variables from the config object available in the instance variable `env_orig`
        - Then update the origin env variables to include:
            - a env variable named `GUNICORN_PID`, the `server_a` PID, so master process ID. The env variable `GUNICORN_PID` will be used during the setup of the new `server_b` to reopen log file since it indicate that we are in a new process and have a new program. It will also be use during starting `server_b` to set a variable named `master_pid` on the new instance, as you can guess it is that instance variable that is use to check if we have a parent as master process in the check decribe at the start of the execution
            - `LISTEN_PID`, `LISTEN_FDS` if gunicorn is executed as service with `systemd` to allow the `server_b` to use the same underline fds when starting
            - `GUNICORN_FD` is set if gunicorn is not running as `systemd` service for the same purpose, allow the new server `server_b` to use the same fds. Recall when creating socket, where gunicorn
            read fds from?
            - lastly gunicorn ensure we are in the correct workig dir, then call `os.execvpe` like this
            `os.execvpe(<executable>, <args>, <new_environ>)`. The call to `os.execvpe` is like we calling gunicorn from the command line directly, so it create a new programm in the current process giving birth to `server_b`.

- `SIGWINCH`:
    Gunicorn react to this signal when runing as daemon with the option `--daemon`. `SIGTERM` is sent to worker processes to ask them to terminate and the gunicorn master process keep running

    Handler execution flow:
        - Gunicorn check if its running as daemon, otherwise ignore the signal
        - if running as daemon, it reset the worker count to 0 on the server instance by change the instance variable `num_workers` to zero
        - then send `SIGTERM` to worker processes
        - Gunicorn is still running as daemon but can't accept a request anymore

- `SIGCHLD`:
    Sent by the undeline system (os), when a child exit. Gunicorn listen to this signal to avoid zombie
    child process; process who already exits but still available in the process table.

    Handler execution flow:
        - Gunicorn enter in an infinite loop and call `os.waitpid` like this `os.waitpid(-1, os.WNOHANG)`.
        With that, it check if any child process already finished(exit), if so the chil PID and status is returned. If no child process can not be wait, `os.waitpid` raise `ChildProcessError` error otherwise - child process exist but has no finished yet - (0, 0) is returned.
        **Note**: `os.waitpid(-1, os.WNOHANG)` does not wait for a child to finish and return immediatly whether or not a child already exit. `os.waitpid(-1, os.WNOHANG)` return two value, the first is the zombie process ID and second is the exit code.
        - Then it check if the return value is not (0, 0), if it is, the infinte loop is stoped and we are done here
        - At this stage a zombie child process exist, so gunicorn:
            - first check if the child PID is the same as the instance variable `reexec_pid` which is update during `SIGUSR2` signal handling. if `reexec_pid` and the child PID are equal it means the new server created during `SIGUSR2` handling exit, so we don't have a child master process anymore. What happened? Gunicorn update `reexec_pid` to 0 (it initial value) so it can respond to 
            `SIGUSR2` signal to create a new child master process next time.
            - if the previouse check fail (`reexec_pid` != `zombie_pid`), gunicorn check whether the process
            exit normally or in response to a signal, this check is done based on the return status code by `os.waitpid`. 
                - if it is a normal exit and the status code is 0 then gunicorn log a message to tell you that a given worker has exited, otherwise gunicorn check if the exit code is:
                    - `3` meaning the worker failed to boot, an appropriate message is log and the server 
                    terminate
                    - `4` meaning application failed to be loaded the same process happened as for exit code `3`
                    - otherwise gunicorn just let you know about the worker exited and the exit code
                - if it an exit from a signal like `SIGTERM` and so one, the appropriate message is log to let you know about it as well
            Lastly gunoicorn remove the worker from it state, concretly from the instance variable `WORKERS`, then close it tempory file and call the server hook `child_exit`.
            The infinite continue untill `os.waitpid` return (0, 0) which means no child has exited or raise an error.

We just cover signals handling in gunicorn master process. Now lets look at how a worker process is initialize and start accepting request.

13 - To spawn a new worker Gunicorn:
    - Initialize the worker class 
    - Call the initalize worker class setup method called `init_process`
    - `init_process` after runing it logic call `run` method on the worker instance
    - worker enter in the main loop and start accepting requests

14 - We will look at the behavior of the base worker class located at `gunicorn.workers.base.Worker` then specific worker: `sync` `gunicorn.workers.sync.SyncWorker`.

15 - Base worker initialization `gunicorn.workers.base.Worker`

During worker class initialization in the master process these instance variable are set:

- `age`: representing the `age` of the worker. Concretly if we have 3 workers to spawn, the first spawn worker will have an `age` of `1` and second spawn will have an `age` of 2 and so one. The worker age is tracked by the master process and the current age is increment by one then pass to the worker class as param when spawning new worker
- `pid`: representing the PID of the worker process. It default value is `[booting]` and will be update after fork.
- `ppid`: the master process PID, where the server instance is running. Pass to the worker class as param.
- `sockets`: List of listeners to use to accept incoming request. It value is the list of listeners setup by the master process in it intance variable `LISTENERS`.
- `app`: `WsgiAppInstance`, passed by the master process as param
- `timeout`: timeout to wait before the master process murders the worker process. The worker process use `timeout` to periodically notify the master process that it is alive.
- `cfg`: the config object instance,  passed by the master process as param
- `booted`: indicating if the worker process is already booted, meaning it has done the necessary setup and ready to accept request. Default to `False`
- `aborted`: indicating if the worker has aborted, default to `False`
- `reloader`: will store the reloader engine instance to use when specify the `--reload` option
- `nr`: keep track of the number of request handle by the worker so far, default to 0
- `max_requests`: The maximum number of requests the worker will process before restarting, you specify this with `--max-requests`. Default to `sys.maxsize`
- `alive`: indicate whether the worker can process requests. Default to `True`
- `log`: the logger to use, passed by the master process as param
- `tmp`: intance of `gunicorn.workers.workertmp.WorkerTmp`, representing the tempory file setup and frequently update (worker update the _access time_ and _modified time_ of the temp file) by the worker process and use by the master process to check worker `health` (by checking if the temp _modified time_ that should be update by the worker process is within `timeout`) before murdering the worker process.

16 - What does base worker `gunicorn.workers.base.Worker` `init_process` method do ?
The  `init_process` method is where Gunicorn setup the worker and run it main loop. As their recommend 
if a subclass overrides this method, the last statement should be to call the base worker `init_process` method with `super().init_process()` so that the `run()` loop is initiated. 

In `gunicorn.workers.base.Worker` `init_process` method works as follow:
- it starts by updating the new worker process environment variables with variables provided with `--env` options
- change the process owner, the user and group as which the process should run. Can be controlled by `--user` and `--group` options
- create a `pipe` to _wake up_ the worker process when new signal is available to avoid delay; the fds are set no blocking and setup to close on an exec
- prevent fd inheritance by appling close on exec flag on the sockets passed by the parent process, the tempory file create at initialization step and on log file(s)
- cleanup and setup new signal events for the worker process
- if `--reload` option gunicorn setup realoader mechanisme to use when file changes. If you have 
[Inotify](https://pypi.org/project/inotify/) installed it will be used otherwhise file system polling mechanisme will be used. With file polling, gunicorn, will check the modified time over all tracking files
and run the reload logic if needed. 
During reload, gunicorn change the instance variable `alive` to `False` and call the server hook `worker_int`. 
Reload here mean: stop the current worker process and start another one, who should pick the necessary change made to the wsgi application.
**Note**: if `--reload` option is specified only the reloader class initialization is run in the worker process main thread, the whole reloading check/process run in different thread than the main thread.
- Then:
    - the wsgi application is loaded if not already
    - the server hook `post_worker_init` is called
    - the instance variable `booted` is set to `True` and the `run` method of the worker class is called where we start processing request.

17 - A closer look at `gunicorn.workers.sync.SyncWorker`

`gunicorn.workers.sync.SyncWorker` is the default worker used by gunicorn when no worker is specified.
It subclasses the base worker `gunicorn.workers.base.Worker` we just saw in the previous step and implement the `run` method, the one needed to accept and handle incomming request.

The `run` method of `gunicorn.workers.sync.SyncWorker` starts by making all our listeners (server sockets) no blocking meaning when we will call `accept` method on a listener(socket), it won't block waiting for a request to be available, instead it will return immediatly by either throwing an error or with a client request data (client socket and address). 

We then enter in the main loop, where gunicorn continously accept and process requests.

The main loop is design for two cases:
    - when we only have one listener:
        - In this case the worker starts processing request if available and after a request/response lifecycle, it updates its tempory file to tell the master process it still alive, then without waiting (meaning no call to `select.select`), the worker continously processes more requests if available until no request is waiting for processing. The worker then wait for `timeout --timeout` using `select.select` to free up the CPU before the next iteration and continue with the next iteration if `timeout` complete or new request arrives. 
    - when we have more than one listener:
        - The worker starts by checking listeners (server sockets) readability using `select.select` with `timeout`, if one or more listener (server socket) are readable, the worker then processes one request over each readable listeners then continues with the next iteration in the main loop using the same process again.

In other words, for each iteration in the main loop:
    - the worker notify the master process it's alive, 
    - check if there is request to process and processes it 
    - wait for `timeout` or new request
    - and restart the same process in the next iteration

**Note**: The worker notify the master process before starting to wait for `timeout` or new request.

Also during each iteration in the main loop, the worker check if its parent has changed, if so, meaning it's an orphan process, the worker breaks from the main loop and exits the process.

During the main loop execution, the worker instance method `accept` is called with a listener (server socket) on which socket `accept` method is called.

When a request is available the call to `accept` on the listener(server socket) return a new socket to interact with the client and the client address info (address, port).

The client socket is set to blocking (e.g read operation will wait untill data is available) and close on exec flag is apply to it, then the worker instance method `handle` is called with:
    - the server socket, the listener
    - the socket to use to interact with the client
    - and the client address, a tuple in form (address, port).

The `handle` method starts by checking whether the communication with the client should be done over ssl based on `--keyfile` and `--certfile` options. If `--keyfile` or `--certfile` is specified, a new secure socket is created from the client socket and will be used to handle the communication over SSL/TLS.

The worker handles the client Http request in two phases:
    - Parsing the client request
    - Process the request after parsing by calling the wsgi application and send its response to the client

### Parsing the client request
As I am writting this, Gunicorn uses Http/1 and parses the http message according to that specification.
In the `handle` method, after deciding wether or not to use ssl/tls, the worker creates a parser object that takes as arguments the client socket, address and the server configuration. 

The parser object is an intance of `gunicorn.http.parser.RequestParser`. Let's call the instance created `parser`.

During the parser initialization:
    - the config object is set on the parser instance as an attribute named `cfg`
    - based on the client info, an attribute `unreader` is set on the parser instance `parser` and contains an object that wrap the client socket or data source in order to provide a convinent way to read the data.
    The unreader can be of two types `gunicorn.http.unreader.SocketUnreader` or `gunicorn.http.unreader.IterUnreader`, both sharing a common parent class `gunicorn.http.unreader.Unreader`. 
    Instance of `gunicorn.http.unreader.SocketUnreader` is created when the client socket or data source has the `recv` method otherwhise `gunicorn.http.unreader.IterUnreader` is created.
    So far, from my understanding, the unreader object wrap the client socket, then is used to read from it an amount `Q` of data and if we get more than `Q`, the remaining data is kept in memory for reference later to potentially avoid data lost.
    In fact during unreader initialization, it creates an in memory byte buffer using python `io` 
    module
    - then an attribute named `mesg` is set on `parser`, which represent a request object `gunicorn.http.message.Request` and will contain the parsed data from the Http message
    - `source_addr`, an instance attribute is set containing the client address on `parser`
    -  and at the end `req_count` attribute is set on `parser`, gunicorn says it used when we have the `Connection` header with `keep-alive` value

`gunicorn.http.parser.RequestParser` provides a python iterator interface, so after `parser` is created, python bultin `next` function is executed on it leading to the execution of the `__next__` method. 

The execution flow of `__next__` method from `parser` create a request object `R`(just a name, nothing more) which is an instance of `gunicorn.http.message.Request`. The request object `R` created is set in `mesg` attribute on `parser` and that attribute is then returned from the `__next__` method. 

So, the `mesg` attribute on `parser` will contain an instance of `gunicorn.http.message.Request`. 

`R` represents the object containing the parsed http message for a request.

**Parsed http message?**

Yes! And the parsing is done during the intialization of `gunicorn.http.message.Request` resulted to `R`

During the intialization of `gunicorn.http.message.Request` the Http message request line, headers are parsed and the body object or mechanism that will be use to read payload sent by the client is determined.

Before we look at the parsing process, here is an example of a Http GET message:
```bash
GET / HTTP/1.1\r\n
Host: localhost:8000\r\n
User-Agent: user-agent-value\r\n
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n
Accept-Language: fr-FR,fr;q=0.5\r\n
Accept-Encoding: gzip, deflate, br, zstd\r\n
DNT: 1\r\n
Sec-GPC: 1\r\n
Connection: keep-alive\r\n
Cookie: csrftoken=csrtoken-value\r\n
Upgrade-Insecure-Requests: 1\r\n
Sec-Fetch-Dest: document\r\n
Sec-Fetch-Mode: navigate\r\n
Sec-Fetch-Site: none\r\n
Sec-Fetch-User: ?1\r\n
Priority: u=0, i\r\n\r\n
[body]
```
`gunicorn.http.message.Request` for initialization takes as args the server config object, the unreader created earlier, the client address and the request count (usefull with `keep-alive` connection) then:
    - Setup the class state with a set of instance variables like `method` `uri` `path` `query`, `limit_request_line`, `limit_request_fields`, `limit_request_field_size` among others
    - Executes the `parse` method:
        - The request line is read from the http message, that's up to the first occurence of `\r\n`.
        In the example provided, it's this: `GET / HTTP/1.1`. If gunicorn is running behind a server proxy that support protocol proxy and you enable it with the config option `--proxy-protocol`, then it checks if the first line read is the protocol proxy line. If so, which can looks like this `PROXY TCP4 203.0.113.10 203.0.113.20 56324 80`, it parses it, validate it, extracts the necessary informations like the client IP and Port from it and then read again up to the next occurence of `\r\n` to now get the request line. Gunicorn while reading the request line ensure it size is not larger than the config option `--limit-request-line`
        - After the request line is read, for example `GET / HTTP/1.1`, it's parsed, validate and the request **method**, **path**, **query**, **fragment** and Http **version** are extract from it. If any error occures during parsing like:
            - the request method contains not allowed characteres like lower case letters, # etc...
            - the request method length is too large or less, must be between 3 or 20, no more, no less
            - the request uri is empty or is invalid
            - the http version specified in the message is invalid or not the version 1
        then the request processing stops and the client get an error message. 
        - Now come the request headers parsing part, from the remaining data after reading the request line, the worker reads from the socket/data source untill it find the fisrt occurence of `\r\n\r\n` indicating the end of the request headers. The headers data size should be within a limit which is calculate using `--limit-request-fields` and `--limit-request-field_size` config options. In case of no request headers available, we immediatly return from the `parse` method. This can happen with a message like this : 
        ```bash
        GET / HTTP/1.1\r\n
        \r\n
        [body]
        ```
        - if headers exist then the worker parses them to get a list of tuple (name, value) pair. While parsing each header line, the worker ensure that the headers count does not exceed `--limit-request-fields` option value or an error occures. It also makes sure that each header line size is within `--limit-request-field_size` option value or an error occures. Other validations happen as well like :
            - validating that the header has this format `name:value` like `Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`
            - ensuring that the header `name` does not contain not allowed characteres
            - making sure that the header value does not contain invalid and dangerous characteres `\0\r\n`
            - validating whether to allow `_` or not in header name based on `--header-map` option.
        - The headers are successfully parsed, we return from the `parse` method with the remain/unused data as value. That value is keep in the `unreader` object buffer.
    - From here We've successfully parse the http message request line and headers, and the read but not used data is keep in the `unreader` object buffer. The next step is to determine how we will read the http message request body
    - The body reading mechanism is influenced by two headers : `CONTENT-LENGTH` and `TRANSFER-ENCODING`. The goal is to determine if the request body should be read in chunk with `TRANSFER-ENCODING` header containing `chunked` as value in the right order or directly using the `CONTENT-LENGTH` header. Only one should be specified at a time but if both exist in the request header which is uncommon, an error occures to avoid smuggling attack. The base object use to read the request payload is `gunicorn.http.body.Body` and it takes a reader object during initialization which can be `ChunkedReader`, `LengthReader` or `EOFReader`. The reader is a class that takes the `unreader` object intance and provide a `.read` method.

The initialization of `gunicorn.http.message.Request` is completed and we get an object (which we called `R`) that contains the http request message parsed.

### Request handling
This is where the client request is processed and a response is returned to the client. Mainly the [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary for the request is created then the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) is called and the data returned by the wsgi app is sent to the client.

#### Environ dictionary and response object
This step start with call to the server hook `pre_request`, then the [environ](https://peps.python.org/pep-3333/#environ-variables) and a response object(`gunicorn.http.wsgi.Response`) are created using the client socket and address, the request object created in the last step, the server config and the server address.

The response object `gunicorn.http.wsgi.Response` is intialized using the request object, the client socket and the server configuration, then the worker starts building the [environ variables](https://peps.python.org/pep-3333/#environ-variables) along with headers parsed in the request object. 

The worker also responds to the [Expect header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Expect#large_message_body) and normalize headers by replacing `-` by `_` for consistency. Request headers are also prefixed with  `HTTP_` before being set in the [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary except `CONTENT_TYPE` and `CONTENT_LENGTH`.

The client and server addresses and ports are set in the [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary using `REMOTE_ADDR`, `REMOTE_PORT`, `SERVER_NAME`, `SERVER_PORT` along with the `url_scheme` `http` or `https` determined during request parsing.

If `SCRIPT_NAME` is available, the url part containing it, is cut from the parsed path in the request object. The remaining part is set in the [environ](https://peps.python.org/pep-3333/#environ-variables) as `PATH_INFO` along with script name itself `SCRIPT_NAME`.

If gunicorn is running behind a proxy that support protocol proxy and you enable protocol proxy through `--protocol-poxy` then the client info `REMOTE_ADDR`, `REMOTE_PORT` are updated in the [environ](https://peps.python.org/pep-3333/#environ-variables).

At the end an [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary can looks like this:
```python
{
    "wsgi.errors": <gunicorn.http.wsgi.WSGIErrorsWrapper object at address>, 
    "wsgi.version": (1, 0), 
    "wsgi.multithread": False, 
    "wsgi.multiprocess": False, 
    "wsgi.run_once": False, 
    "wsgi.file_wrapper": <class "gunicorn.http.wsgi.FileWrapper">, 
    "wsgi.input_terminated": True, 
    "SERVER_SOFTWARE": "gunicorn/23.0.0", 
    "wsgi.input": <gunicorn.http.body.Body object at address>, 
    "gunicorn.socket": <socket.socket fd=9, family=2, type=1, proto=0, laddr=("127.0.0.1", 8000), raddr=("127.0.0.1", 54810)>, 
    "REQUEST_METHOD": "GET", 
    "QUERY_STRING": "", 
    "RAW_URI": "/", 
    "SERVER_PROTOCOL": "HTTP/1.1", 
    "HTTP_HOST": "localhost:8000", 
    "HTTP_USER_AGENT": "user-agent", 
    "HTTP_ACCEPT": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "HTTP_ACCEPT_LANGUAGE": "fr-FR,fr;q=0.5", 
    "HTTP_ACCEPT_ENCODING": "gzip, deflate, br, zstd", 
    "HTTP_DNT": "1", 
    "HTTP_SEC_GPC": "1", 
    "HTTP_CONNECTION": "keep-alive", 
    "HTTP_COOKIE": "csrftoken=csrf-value", 
    "HTTP_UPGRADE_INSECURE_REQUESTS": "1", 
    "HTTP_SEC_FETCH_DEST": "document", 
    "HTTP_SEC_FETCH_MODE": "navigate", 
    "HTTP_SEC_FETCH_SITE": "none", 
    "HTTP_SEC_FETCH_USER": "?1", 
    "HTTP_PRIORITY": "u=0, i", 
    "wsgi.url_scheme": "http", 
    "REMOTE_ADDR": "127.0.0.1", 
    "REMOTE_PORT": "54810", 
    "SERVER_NAME": "127.0.0.1", 
    "SERVER_PORT": "8000", 
    "PATH_INFO": "/", 
    "SCRIPT_NAME": ""
}
```

#### WSGI app call
Before calling the wsgi application callable the worker increment it instance attribute `nr` that keep track on the number of request handle so far. If after incrementation, `nr` value is greater that `--max-requests` option then the worker will restart(exit and a new one will be created) after handling the current request.

Then the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) is called with [environ](https://peps.python.org/pep-3333/#environ-variables) dictionnary created and the response object instance (`gunicorn.http.wsgi.Response`) [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method. 

The [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) do it magic and return the data that should be sent to client as an iterable of bytes. But before returning the data it must call the response object [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method with the response status like `201 Created` and the response headers as collection of tuple `(header_name, header_value)` along with an optional arg `exc_info`. See [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) for more info.

Mainly, the response object [start_response](https://peps.python.org/pep-3333/#the-start-response-callable) method mark the start of the http response, it:
    - parsed the status code provide by the wsgi application
    - processes the headers provided by the wsgi application, validate each of them and ignore [hop-by-hop headers](https://datatracker.ietf.org/doc/html/rfc2616.html#section-13.5.1) 
    - determine how data should be sent to client:
        - in chuck, when content length is not provided, http version support chunked body and the response status code/request method support sending a body in the response data
        - directly up to content length when `CONTENT-LENGTH` is not `None`

The data returned by the [wsgi app callable](https://peps.python.org/pep-3333/#the-application-framework-side) are sent to client up to `CONTENT-LENGTH` or if not `CONTENT-LENGTH` in chucked if client support it.

If the returned object is an intance of `gunicorn.http.wsgi.FileWrapper` then based on `--no-sendfile` and ssl not being enabled, gunicorn use `socket.socket.sendfile` for data transmission to client otherwhise fallback to the default sending mechanisme (iterate and send returned data to client).

Once data are sent to client, `post_request` server hook is called and no matter `--keep-alive`, the connection is closed with the client since we are use using `gunicorn.workers.sync.SyncWorker` worker.

We are just done handling a request with `gunicorn.workers.sync.SyncWorker`.