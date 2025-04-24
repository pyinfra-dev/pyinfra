---
# Ignore warning about this page not being included in any toctree
orphan: true
---

# Installation

## Prerequisites

Successful installation requires a Python 3 environment. Starting with pyinfra 3.2, pyinfra supports Python 3.9, 3.10, 3.11, and 3.12.

Officially supported installation methods include pip and uv. Both tools provide a streamlined workflow for installing pyinfra and managing dependencies.

While there have been successes with using other tools like poetry or pip-tools, they do not share the same workflow as pip or uv - especially when it comes to constraint vs. requirements management. Installing via Poetry or pip-tools is not currently supported.

This guide will help you quickly set up pyinfra using pip or uv, a fast and modern tool for managing Python environments and dependencies. uv makes the installation process easy and provides a smooth setup experience.

Before installing pyinfra, ensure you have **Python** installed: pyinfra requires Python 3.9 or later. You can download Python from the [official website](https://www.python.org/downloads/).

## Bad Practices

- **Avoid System-Wide Installation**: Installing pyinfra system-wide (using `sudo pip install pyinfra`) can lead to conflicts with other Python packages and system tools.
- **Do Not Mix Projects**: Avoid installing pyinfra in a virtual environment that is shared with other projects to prevent dependency conflicts.


## Installation Methods

### Using Pip

It is recommended to install pyinfra using `pip`. To avoid potential conflicts with system packages, it is best practice to install pyinfra in a virtual environment.

1. Ensure `pip` is installed and up-to-date. You can upgrade `pip` using the following command:

  ```sh
  python -m pip install --upgrade pip
  ```

2. **Create a Virtual Environment**: Creating a virtual environment ensures that pyinfra and its dependencies are isolated from other projects and system packages.

   ```sh
   # Create a virtual environment
   python -m venv env

   # Activate the virtual environment
   # On macOS/Linux
   source env/bin/activate
   ```

3. **Install pyinfra**: Once the virtual environment is activated, install pyinfra using `pip`.

   ```sh
   pip install pyinfra
   ```

4. **Verify Installation**: Check the installed version of pyinfra to ensure it was installed correctly.

   ```sh
   pyinfra --version
   ```

5. **Keep Dependencies Up-to-Date**: Regularly update pyinfra and its dependencies to benefit from the latest features and security patches.

   ```sh
   pip install --upgrade pyinfra
   ```

### Using uv

It is recommended to install pyinfra using `uv`. To avoid potential conflicts with system packages, it is best practice to install pyinfra in a virtual environment.

1. **Install pyinfra**: Once the virtual environment is activated, install pyinfra using `pip`.

   ```sh
   uv pip install pyinfra
   ```

2. **Verify Installation**: Check the installed version of pyinfra to ensure it was installed correctly.

   ```sh
   pyinfra --version
   ```

3. **Keep Dependencies Up-to-Date**: Regularly update pyinfra and its dependencies to benefit from the latest features and security patches.

   ```sh
   uv pip install --upgrade pyinfra
   ```

### Windows-Specific Instructions

Tested on Windows Server 2019 with Python 3.9.

#### Prerequisites

1. **Download and Install Python**:
   - Download Python from the [official website](https://www.python.org/downloads/windows/).
   - Install Python as Administrator and ensure the **Add Python to PATH** option is selected.

2. **C++ Compiler (Optional)**: If you need to build any Python packages on Windows, you may need a C++ compiler. One possible solution is to install Visual Studio Community Edition.

   - Download [Visual Studio Community Edition](https://visualstudio.microsoft.com/downloads/).
   - Install Visual Studio as Administrator and select the "Desktop development with C++" option. Ensure at least the following options are selected:
     - "MSVC v142..."
     - "Windows 10 SDK..."
     - "C++ CMake tools for Windows"
     - "C++ ATL for latest..."
     - "C++/CLI support for v142..."
     - "C++ Modules for v142..."

#### Installation Steps

1. **Create a Virtual Environment**:

   ```sh
   python -m venv env
   ```

2. **Activate the Virtual Environment**:

   ```sh
   env\Scripts\activate
   ```

3. **Install pyinfra**:

   ```sh
   pip install pyinfra
   ```

4. **Verify Installation**:

   ```sh
   pyinfra --version
   ```

By following these best practices and instructions, you can ensure a smooth and conflict-free installation of pyinfra.