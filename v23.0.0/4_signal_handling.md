
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
