import asyncio
from unittest import IsolatedAsyncioTestCase, TestCase

from pyinfra import host, inventory
from pyinfra.api import Host, Inventory
from pyinfra.context import ContextManager, LocalContextObject, ctx_host, ctx_inventory


def _create_host(name: str = "host"):
    return Host(name, Inventory(([name], {})), None, None)


class TestHostContextObject(TestCase):
    def test_context_host_dir_matches_class(self):
        assert dir(Host) == dir(host)

    def test_context_host_eq(self):
        host_obj = _create_host()
        with ctx_host.use(host_obj):
            assert host == host_obj

    def test_context_host_repr(self):
        host_obj = _create_host("somehost")
        with ctx_host.use(host_obj):
            assert repr(host) == "ContextObject(Host):Host(somehost)"

    def test_context_host_str(self):
        host_obj = _create_host()
        with ctx_host.use(host_obj):
            assert str(host_obj) == "host"

    def test_context_host_attr(self):
        host_obj = _create_host()

        with self.assertRaises(AttributeError):
            host_obj.hello

        with ctx_host.use(host_obj):
            setattr(host, "hello", "world")
            assert host_obj.hello == host.hello

    def test_context_host_class_attr(self):
        host_obj = _create_host()

        with ctx_host.use(host_obj):
            assert ctx_host.isset() is True

            with self.assertRaises(AttributeError):
                host_obj.hello

            setattr(Host, "hello", "class_world")
            setattr(host_obj, "hello", "instance_world")

            assert host.hello == host.hello

        # Reset and check fallback to class variable
        assert ctx_host.isset() is False
        assert host.hello == "class_world"


class TestInventoryContextObject(TestCase):
    def test_context_inventory_len(self):
        inventory_obj = Inventory(("host", "anotherhost"))

        with ctx_inventory.use(inventory_obj):
            assert ctx_inventory.isset() is True
            assert len(inventory) == len(inventory_obj)

    def test_context_inventory_iter(self):
        inventory_obj = Inventory(("host", "anotherhost"))

        with ctx_inventory.use(inventory_obj):
            assert ctx_inventory.isset() is True
            assert list(iter(inventory)) == list(iter(inventory_obj))


class TestContextManager(IsolatedAsyncioTestCase):
    def test_use_restores_context_after_exception(self):
        manager = ContextManager("test", LocalContextObject)
        original = object()

        for replacement in (original, object()):
            with self.subTest(same_value=replacement is original):
                with manager.use(original):
                    with self.assertRaisesRegex(RuntimeError, "boom"):
                        with manager.use(replacement):
                            manager.set(object())
                            raise RuntimeError("boom")
                    assert manager.get() is original
                assert manager.get() is None

    async def test_use_restores_context_after_cancellation(self):
        manager = ContextManager("test", LocalContextObject)
        original = object()
        entered = asyncio.Event()
        restored = []

        async def worker():
            try:
                with manager.use(object()):
                    entered.set()
                    await asyncio.Future()
            except asyncio.CancelledError:
                restored.append(manager.get())
                raise

        with manager.use(original):
            task = asyncio.create_task(worker())
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            assert restored == [original]
            assert manager.get() is original
        assert manager.get() is None
