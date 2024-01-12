from pyinfra.operations import files


def call_file_op():
    files.put(
        name="Third main operation",
        src="files/a_file",
        dest="/a_file",
    )
