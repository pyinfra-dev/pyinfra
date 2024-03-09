from pyinfra import host
from pyinfra.facts.files import File, Sha256File
from pyinfra.operations import files, python, server

TEST_FILENAME = "/opt/testfile"
TEST_LINE = "test line"


# Facts
# Facts are gathered during the operation run which happens after the deploy
# code is completely executed, so facts altered by operations will have the
# state prior to any operations.

files.line(
    path=TEST_FILENAME,
    line=TEST_LINE,
)

# Instead of:
if host.get_fact(File, path=TEST_FILENAME):
    # This will only be executed if the file existed on the remote machine before
    # the deploy started.
    server.shell(commands=["echo if sees file"])

# Use the host.when context to add operations that will run if a condition,
# evaluated at runtime, is met.
with host.when(lambda: bool(host.get_fact(File, path=TEST_FILENAME))):
    # This will be executed if the file exists on the remote machine at this point
    # in the deploy.
    server.shell(commands=["echo when sees file"])


# This fact will be None because the file doesn't exist on the remote machine
# before the deploy starts.

# Instead of:
sha256 = host.get_fact(Sha256File, path=TEST_FILENAME)
print("Wrong sha256:", sha256)


# Use a callback function to get the updated fact data
def check_host_roles():
    # This will have the correct SHA of the file as callback functions are
    # evaluated during the deploy.
    sha256 = host.get_fact(Sha256File, path=TEST_FILENAME)
    print("Correct sha256:", sha256)

    # Call nested operations here using sha256..


python.call(function=check_host_roles)


# Operation changes
# Operations are run after deploy code are completely executed, so operations
# that overlap making changes to the remote system will both report they will
# make changes.

# For demonstration we just duplicate the first line op so it's always no change
second_line_op = files.line(
    path=TEST_FILENAME,
    line=TEST_LINE,
)

# Instead of:
if second_line_op.changed:
    # This will be executed if the line/file didn't exist on the remote machine
    # before the deploy started.
    server.shell(commands=["echo if sees second op"])

# Use the op.did_change context
with second_line_op.did_change:
    # This will be executed if the second line operation made any changes, in
    # this deploy that's never. This will appear as a conditional op in the CLI.
    server.shell(commands=["echo with sees second op"])


# Nested

with host.when(lambda: False):
    with host.when(lambda: True):
        # This should never be executed
        server.shell(commands=["echo this message should not be printed"])
    server.shell(commands=["echo this message should not be printed"])

with host.when(lambda: True):
    with host.when(lambda: False):
        # This should never be executed
        server.shell(commands=["echo this message should not be printed"])
    server.shell(commands=["echo this message should be printed"])
