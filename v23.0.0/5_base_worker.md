
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
