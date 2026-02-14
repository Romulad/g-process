
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
