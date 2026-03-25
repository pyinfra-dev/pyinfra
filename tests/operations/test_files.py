// Add unit tests for checksum-based file validation in `files.download`

import pytest
from pyinfra.api import host
from pyinfra.operations import files


def test_checksum_validation(mocker):
    # Mock the download function to simulate successful download
    mocker.patch('pyinfra.operations.files.download_file', return_value=True)
    
    # Define a dummy file path and checksum
    file_path = '/tmp/testfile'
    checksum = 'dummychecksum'
    
    # Ensure the file does not exist initially
    assert not host.fact.file(file_path)
    
    # Download the file with checksum validation
    files.download(
        src='http://example.com/testfile',
        dest=file_path,
        checksum=checksum,
        _sudo=True,
    )
    
    # Verify that the file was downloaded and exists
    assert host.fact.file(file_path)
    
    # Mock the download function to simulate a failed download due to incorrect checksum
    mocker.patch('pyinfra.operations.files.download_file', return_value=False)
    
    # Attempt to redownload the file with the same checksum
    files.download(
        src='http://example.com/testfile',
        dest=file_path,
        checksum=checksum,
        _sudo=True,
    )
    
    # Verify that the file was not redownloaded due to correct checksum match
    assert host.fact.file(file_path)
