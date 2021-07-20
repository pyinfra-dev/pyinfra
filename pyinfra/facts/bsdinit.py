from .sysvinit import InitdStatus


class RcdStatus(InitdStatus):
    '''
    Same as ``initd_status`` but for BSD (/etc/rc.d) systems. Unlike Linux/init.d,
    BSD init scripts are well behaved and as such their output can be trusted.
    '''

    command = '''
        for SERVICE in `find /etc/rc.d /usr/local/etc/rc.d -type f`; do
            STATUS=`$SERVICE status 2> /dev/null || $SERVICE check`
            echo "`basename $SERVICE`=$?"
        done
    '''

    default = dict
