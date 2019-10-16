Files
-----


The files module handles filesystem state, file uploads and template generation.

:code:`files.directory`
~~~~~~~~~~~~~~~~~~~~~~~

Add/remove/update directories.

.. code:: python

    files.directory(
        name, present=True, assume_present=False, user=None, group=None, mode=None,
        recursive=False
    )

+ **name**: name/patr of the remote folder
+ **present**: whether the folder should exist
+ **assume_present**: whether to assume the directory exists
+ **user**: user to own the folder
+ **group**: group to own the folder
+ **mode**: permissions of the folder
+ **recursive**: recursively apply user/group/mode


:code:`files.download`
~~~~~~~~~~~~~~~~~~~~~~

Download files from remote locations.

.. code:: python

    files.download(source_url, destination, user=None, group=None, mode=None, cache_time=None, force=False)

+ **source_url**: source URl of the file
+ **destination**: where to save the file
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files
+ **cache_time**: if the file exists already, re-download after this time (in s)
+ **force**: always download the file, even if it already exists


:code:`files.file`
~~~~~~~~~~~~~~~~~~

Add/remove/update files.

.. code:: python

    files.file(
        name, present=True, assume_present=False, user=None, group=None, mode=None, touch=False,
        create_remote_dir=False
    )

+ **name**: name/path of the remote file
+ **present**: whether the file should exist
+ **assume_present**: whether to assume the file exists
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files as an integer, eg: 755
+ **touch**: whether to touch the file
+ **create_remote_dir**: create the remote directory if it doesn't exist

``create_remote_dir``:
    If the remote directory does not exist it will be created using the same
    user & group as passed to ``files.put``. The mode will *not* be copied over,
    if this is required call ``files.directory`` separately.


:code:`files.line`
~~~~~~~~~~~~~~~~~~

Ensure lines in files using grep to locate and sed to replace.

.. code:: python

    files.line(name, line, present=True, replace=None, flags=None)

+ **name**: target remote file to edit
+ **line**: string or regex matching the target line
+ **present**: whether the line should be in the file
+ **replace**: text to replace entire matching lines when ``present=True``
+ **flags**: list of flags to pass to sed when replacing/deleting

Regex line matching:
    Unless line matches a line (starts with ^, ends $), pyinfra will wrap it such that
    it does, like: ``^.*LINE.*$``. This means we don't swap parts of lines out. To
    change bits of lines, see ``files.replace``.

Regex line escaping:
    If matching special characters (eg a crontab line containing *), remember to escape
    it first using Python's ``re.escape``.


:code:`files.link`
~~~~~~~~~~~~~~~~~~

Add/remove/update links.

.. code:: python

    files.link(
        name, target=None, present=True, assume_present=False, user=None, group=None,
        symbolic=True, create_remote_dir=False
    )

+ **name**: the name of the link
+ **target**: the file/directory the link points to
+ **present**: whether the link should exist
+ **assume_present**: whether to assume the link exists
+ **user**: user to own the link
+ **group**: group to own the link
+ **symbolic**: whether to make a symbolic link (vs hard link)
+ **create_remote_dir**: create the remote directory if it doesn't exist

``create_remote_dir``:
    If the remote directory does not exist it will be created using the same
    user & group as passed to ``files.put``. The mode will *not* be copied over,
    if this is required call ``files.directory`` separately.

Source changes:
    If the link exists and points to a different target, pyinfra will remove it and
    recreate a new one pointing to then new target.


:code:`files.put`
~~~~~~~~~~~~~~~~~

Copy a local file to the remote system.

.. code:: python

    files.put(
        local_filename, remote_filename, user=None, group=None, mode=None, add_deploy_dir=True,
        create_remote_dir=False
    )

+ **local_filename**: local filename
+ **remote_filename**: remote filename
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files
+ **add_deploy_dir**: local_filename is relative to the deploy directory
+ **create_remote_dir**: create the remote directory if it doesn't exist

``create_remote_dir``:
    If the remote directory does not exist it will be created using the same
    user & group as passed to ``files.put``. The mode will *not* be copied over,
    if this is required call ``files.directory`` separately.


:code:`files.replace`
~~~~~~~~~~~~~~~~~~~~~

A simple shortcut for replacing text in files with sed.

.. code:: python

    files.replace(name, match, replace, flags=None)

+ **name**: target remote file to edit
+ **match**: text/regex to match for
+ **replace**: text to replace with
+ **flags**: list of flaggs to pass to sed


:code:`files.sync`
~~~~~~~~~~~~~~~~~~

Syncs a local directory with a remote one, with delete support. Note that delete will
remove extra files on the remote side, but not extra directories.

.. code:: python

    files.sync(
        source, destination, user=None, group=None, mode=None, delete=False, exclude=None,
        exclude_dir=None, add_deploy_dir=True
    )

+ **source**: local directory to sync
+ **destination**: remote directory to sync to
+ **user**: user to own the files and directories
+ **group**: group to own the files and directories
+ **mode**: permissions of the files
+ **delete**: delete remote files not present locally
+ **exclude**: string or list/tuple of strings to match & exclude files (eg *.pyc)
+ **exclude_dir**: string or list/tuple of strings to match & exclude directories (eg node_modules)


:code:`files.template`
~~~~~~~~~~~~~~~~~~~~~~

Generate a template and write it to the remote system.

.. code:: python

    files.template(
        template_filename, remote_filename, user=None, group=None, mode=None,
        create_remote_dir=False
    )

+ **template_filename**: local template filename
+ **remote_filename**: remote filename
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files
+ **create_remote_dir**: create the remote directory if it doesn't exist

``create_remote_dir``:
    If the remote directory does not exist it will be created using the same
    user & group as passed to ``files.put``. The mode will *not* be copied over,
    if this is required call ``files.directory`` separately.

