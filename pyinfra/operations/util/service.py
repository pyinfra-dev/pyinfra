def handle_service_control(
    host,
    name, statuses, formatter, running, restarted, reloaded, command,
    status_argument='status',
):
    status = statuses.get(name, None)

    # If we don't know the status, we need to check if it's up before starting
    # and/or restarting/reloading
    if status is None:
        yield '''
            # If the service is running
            if {status_command}; then
                {stop_command}
                {restart_command}
                {reload_command}

            # If the service is not running, we just start it (no re[start|load])
            else
                {start_command}
            fi
        '''.format(
            status_command=formatter.format(name, status_argument),
            start_command=(
                formatter.format(name, 'start')
                if running is True else 'true'
            ),
            stop_command=(
                formatter.format(name, 'stop')
                if running is False else 'true'
            ),
            restart_command=(
                formatter.format(name, 'restart')
                if restarted else 'true'
            ),
            reload_command=(
                formatter.format(name, 'reload')
                if reloaded else 'true'
            ),
        )
        statuses[name] = running

    else:
        # Need down but running
        if running is False:
            if status:
                yield formatter.format(name, 'stop')
                statuses[name] = False
            else:
                host.noop('service {0} is stopped'.format(name))

        # Need running but down
        if running is True:
            if not status:
                yield formatter.format(name, 'start')
                statuses[name] = True
            else:
                host.noop('service {0} is running'.format(name))

        # Only restart if the service is already running
        if restarted and status:
            yield formatter.format(name, 'restart')

        # Only reload if the service is already reloaded
        if reloaded and status:
            yield formatter.format(name, 'reload')

    # Always execute arbitrary commands as these may or may not rely on the service
    # being up or down
    if command:
        yield formatter.format(name, command)
