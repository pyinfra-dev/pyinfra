from pathlib import Path
from types import SimpleNamespace

import pytest

from pyinfra.connectors.util import CommandOutput, OutputLine
from pyinfra.operations.ansible import AnsibleModuleAdapter, _execute_ansible_module


class FakeHost:
    def __init__(self, status=True, stdout_line="ok", stderr_line=""):
        self.status = status
        self.stdout_line = stdout_line
        self.stderr_line = stderr_line
        self.commands = []

    def run_shell_command(self, command, **_kwargs):
        self.commands.append(command.get_raw_value())
        output = CommandOutput(
            [
                OutputLine("stdout", self.stdout_line),
                OutputLine("stderr", self.stderr_line),
            ],
        )
        return self.status, output


def make_state(cwd: str, diff=False):
    return SimpleNamespace(cwd=cwd, config=SimpleNamespace(DIFF=diff))


def test_ansible_adapter_run_command_list_uses_quoted_bits():
    host = FakeHost()
    adapter = AnsibleModuleAdapter(make_state("/tmp"), host)

    rc, stdout, stderr = adapter.run_command(["echo", "hello world"])

    assert rc == 0
    assert stdout == "ok"
    assert stderr == ""
    assert host.commands == ["echo 'hello world'"]


def test_execute_ansible_adapter_exit_json_is_success(tmp_path: Path):
    module_file = tmp_path / "mod.py"
    module_file.write_text(
        "def adapter_module(m):\n"
        "    rc, out, err = m.run_command(['echo', 'done'])\n"
        "    if rc:\n"
        "        m.fail_json(msg='command failed', stdout=out, stderr=err)\n"
        "    m.exit_json(changed=True, stdout=out)\n",
    )

    host = FakeHost()
    state = make_state(str(tmp_path), diff=True)

    result = _execute_ansible_module(
        state,
        host,
        str(module_file),
        "adapter_module",
        (),
        {},
        False,
    )

    assert result is True
    assert host.commands == ["echo done"]


def test_execute_ansible_adapter_fail_json_raises_runtime_error(tmp_path: Path):
    module_file = tmp_path / "mod.py"
    module_file.write_text(
        "def adapter_module(m):\n"
        "    m.fail_json(msg='broken')\n",
    )

    host = FakeHost()
    state = make_state(str(tmp_path))

    with pytest.raises(RuntimeError, match="broken"):
        _execute_ansible_module(
            state,
            host,
            str(module_file),
            "adapter_module",
            (),
            {},
            False,
        )
