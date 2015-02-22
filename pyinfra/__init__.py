# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

import logging


# Global logger
logger = logging.getLogger('pyinfra')

# Internal connections
_connections = {}

# Current server host
_current_server = None

# Central operation data
_op_order = [] # list of operation hashes
_op_meta = {} # maps operation hash -> names/etc
# Per-host operation data
_ops = {} # maps operation hash -> operation

# Per-host meta
_facts = {}
_meta = {}
_results = {}
