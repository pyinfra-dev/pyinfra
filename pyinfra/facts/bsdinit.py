from .sysvinit import InitdStatus


class RcdStatus(InitdStatus):
    '''
    Same as ``initd_status`` but for BSD (/etc/rc.d) systems. Unlike Linux/init.d,
    BSD init scripts are well behaved and as such their output can be trusted.
    '''

    command = '''
        for SERVICE in `ls /etc/rc.d/`; do
            _=`cat /etc/rc.d/$SERVICE | grep "daemon="`

            if [ "$?" = "0" ]; then
                STATUS=`/etc/rc.d/$SERVICE check`
                echo "$SERVICE=$?"
            fi
        done
    '''

    default = dict
