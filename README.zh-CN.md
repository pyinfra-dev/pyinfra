[English](https://github.com/pyinfra-dev/pyinfra/blob/3.x/README.md) | [简体中文](https://github.com/pyinfra-dev/pyinfra/blob/3.x/README.zh-CN.md)

> 本文是 [README.md](README.md) 的简体中文翻译。若与英文版存在差异，请以英文版为准。

<p align="center">
    <a href="https://pyinfra.com">
        <img src="https://pyinfra.com/static/logo_readme.png" alt="pyinfra" />
    </a>
</p>

<p>
    pyinfra 把 Python 代码转换成 shell 命令，并在你的服务器上执行。你既可以执行临时命令，也可以编写声明式的操作（operation）。目标可以是 SSH 服务器、本机以及 Docker 容器。它速度很快，可以从一台服务器扩展到数千台。可以把它理解为 <code>ansible</code>，只不过用 Python 而不是 YAML，而且快得多。
</p>

---

<h3>
    <a href="https://docs.pyinfra.com/page/getting-started.html"><strong>入门指南</strong></a> &bull;
    <a href="https://github.com/pyinfra-dev/pyinfra-examples"><strong>示例仓库</strong></a> &bull;
    <a href="https://matrix.to/#/#pyinfra:matrix.org"><strong>在 Matrix 上聊天</strong></a>
</h3>
<p>
    <a href="https://docs.pyinfra.com"><strong>文档</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/support.html"><strong>帮助与支持</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/contributing.html"><strong>参与贡献</strong></a>
</p>

---

为什么选择 pyinfra？它的设计特点包括：

+ 🚀 **极速**：在数千台主机上执行，性能可预期。
+ 🚨 **即时调试**：实时输出 stdin/stdout/stderr（`-vvv`）。
+ 🔄 **幂等的操作**：支持在做出变更前进行差异对比（diff）与试运行（dry run）。
+ 📦 **可扩展**：可直接使用整个 Python 包生态。
+ 💻 **无需 Agent 即可执行**：只要目标有 shell 访问权限即可。
+ 🔌 **连接器集成**：可与 Docker、Terraform、Vagrant 等连接器配合使用。

<img width="100%" src="https://pyinfra.com/static/example_deploy.gif" />

## 快速开始

使用 [`uv`](https://docs.astral.sh/uv/) 安装 pyinfra：

```
uv tool install pyinfra
```

现在你就可以通过 SSH 在主机上执行命令：

```sh
pyinfra my-server.net exec -- echo "hello world"
```

也可以面向 Docker 容器、本机以及其他[连接器](https://docs.pyinfra.com/page/connectors.html)：

```sh
pyinfra @docker/ubuntu exec -- echo "Hello world"
pyinfra @local exec -- echo "Hello world"
```

除了执行命令，你还可以用 [操作](https://docs.pyinfra.com/page/operations.html) 来声明期望状态：

```sh
# Install iftop apt package if not present
pyinfra @docker/ubuntu apt.packages iftop update=true _sudo=true
```

这些内容可以保存为 Python 文件，例如 `deploy.py`：


```py
from pyinfra.operations import apt

apt.packages(
    name="Ensure iftop is installed",
    packages=['iftop'],
    update=True,
    _sudo=True,
)
```

主机也可以写进一个文件，例如 `inventory.py`：

```py
targets = ["@docker/ubuntu", "my-test-server.net"]
```


然后一起执行：

```sh
pyinfra inventory.py deploy.py
```

到这里你已经掌握了 pyinfra 的基本构件！把清单（inventory）、操作和 Python 代码组合起来，你可以部署任何东西。

更详细的说明请参阅[入门指南](https://docs.pyinfra.com/page/getting-started.html)或[使用操作](https://docs.pyinfra.com/page/using-operations.html)指南。你还可以了解如何使用 [inventory 与数据](https://docs.pyinfra.com/page/inventory-data.html)、[全局参数](https://docs.pyinfra.com/page/arguments.html)和 [CLI](https://docs.pyinfra.com/page/cli.html)，或者看看[带说明的示例](https://docs.pyinfra.com/page/examples.html)。

---

<p align="center">
    <a href="https://pypi.python.org/pypi/pyinfra"><img alt="PyPI version" src="https://img.shields.io/pypi/v/pyinfra?color=blue"></a>
    <a href="https://pepy.tech/project/pyinfra"><img alt="PyPi downloads" src="https://pepy.tech/badge/pyinfra"></a>
    <a href="https://docs.pyinfra.com"><img alt="Docs status" src="https://img.shields.io/github/actions/workflow/status/Fizzadar/pyinfra/docs.yml?branch=2.x"></a>
    <a href="https://github.com/Fizzadar/pyinfra/actions?query=workflow%3A%22Execute+tests%22"><img alt="Execute tests status" src="https://img.shields.io/github/actions/workflow/status/Fizzadar/pyinfra/test.yml?branch=2.x"></a>
    <a href="https://codecov.io/github/Fizzadar/pyinfra"><img alt="Codecov Coverage" src="https://img.shields.io/codecov/c/gh/Fizzadar/pyinfra"></a>
    <a href="https://github.com/Fizzadar/pyinfra/blob/2.x/LICENSE.md"><img alt="MIT Licensed" src="https://img.shields.io/pypi/l/pyinfra"></a>
</p>
