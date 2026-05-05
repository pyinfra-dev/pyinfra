from typing import cast
from unittest import TestCase

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.host import Host
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.state import StateStage, StateTimings
from pyinfra.operations import server

from ..paramiko_util import PatchSSHTestCase
from ..util import make_inventory


class TestStateTimings(TestCase):
    def test_record_op_prepare_and_execute(self):
        timings = StateTimings()
        host = cast(Host, object())  # opaque key
        timings.record_op_prepare("op1", host, 0.5)
        timings.record_op_execute("op1", host, 1.25)
        assert timings.op_prepare["op1"][host] == 0.5
        assert timings.op_execute["op1"][host] == 1.25

    def test_record_fact_appends(self):
        timings = StateTimings()
        host = cast(Host, object())
        timings.record_fact(host, "server.LinuxName", 0.1)
        timings.record_fact(host, "server.LinuxName", 0.2)
        timings.record_fact(host, "server.Date", 0.3)
        assert timings.facts[host]["server.LinuxName"] == [0.1, 0.2]
        assert timings.facts[host]["server.Date"] == [0.3]

    def test_elapsed_none_until_both_set(self):
        timings = StateTimings()
        assert timings.elapsed is None
        timings.run_start = 10.0
        assert timings.elapsed is None
        timings.run_end = 12.5
        assert timings.elapsed == 2.5


class TestRunPopulatesTimings(PatchSSHTestCase):
    def test_run_records_op_timings(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        state.current_stage = StateStage.Prepare
        connect_all(state)

        add_op(state, server.shell, name="echo", commands=["echo hi"])

        op_order = state.get_op_order()
        op_hash = op_order[0]

        # Prepare timings get recorded during add_op
        prepare_times = state.timings.op_prepare[op_hash]
        assert len(prepare_times) == len(list(state.inventory.iter_activated_hosts()))
        for host in state.inventory.iter_activated_hosts():
            assert host in prepare_times
            assert prepare_times[host] >= 0.0

        run_ops(state)

        execute_times = state.timings.op_execute[op_hash]
        assert len(execute_times) == len(list(state.inventory.iter_activated_hosts()))
        for host in state.inventory.iter_activated_hosts():
            assert host in execute_times
            assert execute_times[host] >= 0.0

        disconnect_all(state)


class TestPrintTimingsJson(PatchSSHTestCase):
    def test_json_payload_shape(self):
        from pyinfra_cli.prints import print_timings_json

        inventory = make_inventory()
        state = State(inventory, Config())
        state.current_stage = StateStage.Prepare
        connect_all(state)

        add_op(state, server.shell, name="echo", commands=["echo hi"])
        run_ops(state)

        state.timings.run_start = 0.0
        state.timings.run_end = 1.0
        state.timings.wall_start = 100.0
        state.timings.wall_end = 101.0

        captured: list[str] = []
        original_echo = None

        try:
            import click

            original_echo = click.echo

            def capture(msg=None, *args, **kwargs):
                if msg is not None and not kwargs.get("err"):
                    captured.append(msg)

            click.echo = capture  # type: ignore[assignment]
            print_timings_json(state)
        finally:
            if original_echo is not None:
                click.echo = original_echo  # type: ignore[assignment]

        assert captured, "expected JSON output on stdout"
        import json

        payload = json.loads(captured[-1])
        assert payload["elapsed_seconds"] == 1.0
        assert isinstance(payload["operations"], list)
        assert payload["operations"]
        assert "facts" in payload

        disconnect_all(state)
