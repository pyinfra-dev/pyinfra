Files
-----


The files module handles filesystem state, file uploads and template generation.

:code:`files.directory`
~~~~~~~~~~~~~~~~~~~~~~~

Manage the state of directories.

.. code:: python

    files.directory(name, present=True, user=None, group=None, mode=None, recursive=False)

+ **name**: name/patr of the remote file
+ **present**: whether the file should exist
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files
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

Manage the state of files.

.. code:: python

    files.file(name, present=True, user=None, group=None, mode=None, touch=False)

+ **name**: name/path of the remote file
+ **present**: whether the file should exist
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files
+ **touch**: touch the file


:code:`files.line`
~~~~~~~~~~~~~~~~~~

Ensure lines in files using grep to locate and sed to replace.

.. code:: python

    files.line(name, line, present=True, replace=None, flags=None)

+ **name**: target remote file to edit
+ **line**: string or regex matching the *entire* target line
+ **present**: whether the line should be in the file
+ **replace**: text to replace entire matching lines when ``present=True``
+ **flags**: list of flags to pass to sed when replacing/deleting

Note:
    if not present, line will have ``^`` & ``$`` wrapped around so when using regex
    the entire line must match (eg ``SELINUX=.*``)


:code:`files.put`
~~~~~~~~~~~~~~~~~

Copy a local file to the remote system.

.. code:: python

    files.put(local_filename, remote_filename, user=None, group=None, mode=None, add_deploy_dir=True)

+ **local_filename**: local filename (or file-like object)
+ **remote_filename**: remote filename
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files


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

.. code:: python

    files.sync(source, destination, user=None, group=None, mode=None, delete=False)

remove extra files on the remote side, but not extra directories.

+ **source**: local directory to sync
+ **destination**: remote directory to sync to
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files
+ **delete**: delete remote files not present locally


:code:`files.template`
~~~~~~~~~~~~~~~~~~~~~~

Generate a template and write it to the remote system.

.. code:: python

    files.template(template_filename, remote_filename, user=None, group=None, mode=None)

+ **template_filename**: local template filename (or file-like object)
+ **remote_filename**: remote filename
+ **user**: user to own the files
+ **group**: group to own the files
+ **mode**: permissions of the files

