---
# Ignore warning about this page not being included in any toctree
orphan: true
---

# Installation

## Prerequisites

### Python Version Requirements

- Python 3.9 or later is required
- pyinfra 3.2+ supports Python 3.9, 3.10, 3.11, and 3.12
- You can check your Python version with:

  ```sh
  python --version
  ```

### System Requirements

- A Unix-like operating system (Linux, macOS) or Windows
- Shell access to target systems
- For Windows users: Administrator privileges for installation
- For development: A C++ compiler may be required for some Python packages

## Installation Method

### Using uv (Recommended)

First install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already.

Now you can install pyinfra as a tool, or add it to your project's dependencies.

#### Installing pyinfra as a tool

   ```sh
   # install pyinfra
   uv tool install pyinfra
   
   # verify installation
   pyinfra --version
   ```

#### Adding pyinfra to your project dependencies

   ```sh
   # add pyinfra to your project dependencies
   uv add pyinfra
   
   # verify installation
   uv run pyinfra --version
   ```

### Using pipx

First install [pipx](https://pipx.pypa.io/stable/installation/) if you haven't already.

#### Install pyinfra

   ```sh
   pipx install pyinfra
   ```

#### Verify Installation

   ```sh
   pyinfra --version
   ```

### Using pip

#### Create a Virtual Environment (Best Practice)

   ```sh
   # Create a virtual environment
   python -m venv env

   # Activate the virtual environment
   # On macOS/Linux
   source env/bin/activate
   # On Windows
   env\Scripts\activate
   ```

#### Install pyinfra

   ```sh
   pip install pyinfra
   ```

#### Verify Installation

   ```sh
   pyinfra --version
   ```

## Platform-Specific Instructions

### Windows Installation

#### Install Python

- Download from [Python's official website](https://www.python.org/downloads/windows/)
- Run installer as Administrator
- Check "Add Python to PATH" during installation

#### Optional: Install C++ Compiler

- Download [Visual Studio Community Edition](https://visualstudio.microsoft.com/downloads/)
- Select "Desktop development with C++" workload
- Required components:
  - MSVC v142...
  - Windows 10 SDK...
  - C++ CMake tools for Windows
  - C++ ATL for latest...
  - C++/CLI support for v142...
  - C++ Modules for v142...

#### Install pyinfra

   ```sh
   python -m venv env
   env\Scripts\activate
   pip install pyinfra
   ```

## Best Practices

### Do's

- ✅ Use virtual environments for isolation
- ✅ Keep pyinfra and dependencies up-to-date
- ✅ Use the latest Python version supported
- ✅ Install as a regular user (not root/sudo)

### Don'ts

- ❌ Avoid system-wide installation
- ❌ Don't mix pyinfra with other projects in the same virtual environment
- ❌ Don't use unsupported package managers (poetry, pip-tools)

## Troubleshooting

### Common Issues

#### Permission Errors

- Ensure you're not using sudo for installation
- Check virtual environment permissions
- Verify Python installation directory permissions

#### Python Version Issues

- Verify Python version meets requirements
- Consider using pyenv or similar version manager

#### Virtual Environment Issues

- Ensure virtual environment is properly activated
- Check PATH environment variable
- Verify Python interpreter location

## Updating pyinfra

To update to the latest version:

```sh
pip install --upgrade pyinfra
```
