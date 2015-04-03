# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

import logging


# Global logger
logger = logging.getLogger('pyinfra')

# Internal connections
_connections = {}
_sftp_connections = {}

# Current server host
_current_server = None

# Central operation data
_op_order = [] # list of operation hashes
_op_meta = {} # maps operation hash -> names/etc
_ops_run = [] # list of ops which have been started/run
# Per-host operation data
_ops = {} # maps hostnames ->  operation hashes -> operation

# Per-host meta
_facts = {}
_meta = {}
_results = {}
