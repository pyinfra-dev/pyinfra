# pyinfra
# File: pyinfra/facts/hardware.py
# Desc: hardware facts (memory, CPUs, etc)

from __future__ import division

from pyinfra.api import FactBase


class Cpus(FactBase):
    '''
    Returns the number of CPUs on this server.
    '''

    command = 'getconf NPROCESSORS_ONLN || getconf _NPROCESSORS_ONLN'

    @staticmethod
    def process(output):
        try:
            return int(output[0])
        except ValueError:
            pass


class Memory(FactBase):
    '''
    Returns the memory installed in this server, in MB.
    '''

    command = 'vmstat -s'

    @staticmethod
    def process(output):
        data = {}

        for line in output:
            value, key = line.split(' ', 1)

            try:
                value = int(value)
            except ValueError:
                continue

            data[key.strip()] = value

        # Easy - Linux just gives us the number
        total_memory = data.get('K total memory', data.get('total memory'))

        # BSD - calculate the total from the # pages and the page size
        if not total_memory:
            bytes_per_page = data.get('bytes per page')
            pages_managed = data.get('pages managed')

            if bytes_per_page and pages_managed:
                total_memory = (pages_managed * bytes_per_page) / 1024

        if total_memory:
            return int(round(total_memory / 1024))
