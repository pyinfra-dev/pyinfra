# pyinfra
# File: pyinfra/facts/init.py
# Desc: init system facts

import re

from pyinfra.api import FactBase


class UpstartStatus(FactBase):
    '''
    Returns a dict of name -> status for upstart managed services.
    '''

    command = 'initctl list'
    _regex = r'^([a-z\-]+) [a-z]+\/([a-z]+)'

    def process(self, output):
        services = {}

        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                services[matches.group(1)] = matches.group(2) == 'running'

        return services


class SystemdStatus(FactBase):
    '''
    Returns a dict of name -> status for systemd managed services.
    '''

    command = 'systemctl -alt service list-units'
    _regex = r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'

    def process(self, output):
        services = {}

        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                services[matches.group(1)] = matches.group(2) == 'running'

        return services


class SystemdEnabled(FactBase):
    '''
    Returns a dict of name -> whether enabled for systemd managed services.
    '''

    command = '''
        systemctl --no-legend -alt service list-unit-files | while read -r SERVICE STATUS; do
            if [ "$STATUS" = generated ] &&
                systemctl is-enabled $SERVICE.service >/dev/null 2>&1; then
                STATUS=enabled
            fi
            echo $SERVICE $STATUS
        done
    '''
    _regex = r'^([a-z\-]+)\.service\s+([a-z]+)'

    def process(self, output):
        services = {}

        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                services[matches.group(1)] = (
                    matches.group(2) in ('enabled', 'static')
                )

        return services


class InitdStatus(FactBase):
    '''
    Low level check for every /etc/init.d/* script. Unfortunately many of these
    mishehave and return exit status 0 while also displaying the help info/not
    offering status support.

    Returns a dict of name -> status.

    Expected codes found at:
        http://refspecs.linuxbase.org/LSB_3.1.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html
    '''

    command = '''
        for SERVICE in `ls /etc/init.d/`; do
            _=`cat /etc/init.d/$SERVICE | grep status`

            if [ "$?" = "0" ]; then
                STATUS=`/etc/init.d/$SERVICE status`
                echo "$SERVICE=$?"
            fi
        done
    '''
    _regex = r'([a-zA-Z0-9\-]+)=([0-9]+)'

    def process(self, output):
        services = {}

        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                status = int(matches.group(2))

                # Exit code 0 = OK/running
                if status == 0:
                    status = True

                # Exit codes 1-3 = DOWN/not running
                elif status < 4:
                    status = False

                # Exit codes 4+ = unknown
                else:
                    status = None

                services[matches.group(1)] = status

        return services


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


class RcdEnabled(FactBase):
    '''
    Returns a dict of service name -> whether enabled (on boot) status. Different
    to Linux variants because BSD has no/one runlevel.
    '''
