Deploy Process
==============

When you run a pyinfra deploy via the CLI or API, these are the high level steps taken:

+ Connect to each of the target hosts
+ Generate operations for each host as defined by the user, gathering facts as required
+ The operations are executed on the remote hosts, in a configurable manner


Connecting
----------

To connect to the target hosts, pyinfra uses an inventory. This contains metadata
on all of the target machines, in addition to any user defined data for the deploy. Using
this SSH connections are attempted in parallel until all hosts are either connected or have
failed.


Generating Operations
---------------------

Operations define the desired state of the target hosts. When operations are added to
a deploy, facts/state is read from each of the hosts, for example ``directory:/opt/my_app``.
Based on these facts and the desired state, operations output a list of commands per target
host.

The list of commands contains:

+ simple shell commands
+ local/remote filenames for uploading files
+ Python functions which serve as mid-deploy callbacks


Executing Operations
--------------------

After all the operations & associated commands have been added to the deploy they are
executed in parallel on the remote hosts. By default they are run in order, waiting between
each operation for all hosts to complete or error. This behaviour can be changed to skip
waiting by using ``--no-wait``, or all operations can be run one host after the other,
using ``--serial``. Serial can also be applied on a per-operation level by setting
``serial=True``.
