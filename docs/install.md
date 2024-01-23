# Installation

## Pipx

It is recommended to install pyinfra using `pip`:

```sh
pip install pyinfra
```

## Windows

Tested on WindowsServer2019 with python 3.7.

+ Download Python https://www.python.org/downloads/windows/
  (ex: python-3.7.6-amd64.exe). Install as Administrator and
  ensure the **Add Python to PATH** option is selected.)

If you need to build any python packages on Windows, perhaps because one of the **pip** packages above fails, you may need a c++ compiler. One possible solution is below.

+ Download Visual Studio Community Edition https://visualstudio.microsoft.com/downloads/ and
  install Visual Studio as Administrator. Select the "Desktop development with C++" option and
  ensure at least these options are selected:

    + "MSVC v142..."
    + "Windows 10 SDK..."
    + "C++ cmake tools for windows"
    + "C++ ATL for latest..."
    + "C++/cli support for v142..."
    + "C++ Modules for v142..."
