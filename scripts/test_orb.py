"""
ORB Core Smoke Test — verify the kernel boots and modules run.
Run:  python scripts/test_orb.py
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_manifest():
    """Test manifest parsing + validation."""
    print("─" * 60)
    print("1) Manifest parsing")
    from orb_core.manifest import Manifest, ModuleManifest, Capability, ModuleType

    m = Manifest(
        modules={
            "b": ModuleManifest(
                name="b", version="0.1.0", type=ModuleType.CORE,
                entry_point="orb_core.demo_module:DemoModule",
                capabilities=[Capability.EVENT_BUS_PUB],
                dependencies=["a"],
                priority=20,
            ),
            "a": ModuleManifest(
                name="a", version="0.1.0", type=ModuleType.CORE,
                entry_point="orb_core.demo_module:DemoModule",
                capabilities=[Capability.CONFIG_READ],
                priority=10,
            ),
        }
    )
    order = m.get_load_order()
    assert order == ["a", "b"], f"load order wrong: {order}"
    print(f"  OK — dependency order: {order}")
    print(f"  OK — validation: {m.validate()} (empty = clean)")


def test_kernel_lifecycle():
    """Test kernel start/stop with demo module."""
    print("─" * 60)
    print("2) Kernel lifecycle")
    import tempfile
    from orb_core.kernel import Kernel
    from orb_core.manifest import Manifest, ModuleManifest, ModuleType, Capability

    # Write a temp manifest with just the demo module
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(f"""
orb_version: "1.0"
modules:
  demo:
    name: "demo"
    version: "0.1.0"
    type: core
    entry_point: "orb_core.demo_module:DemoModule"
    capabilities: [events.publish, events.subscribe, config.read]
    priority: 10
""")
        tmp = f.name

    kernel = Kernel(Path(tmp))

    async def run():
        await kernel.start()
        # Verify module loaded + running
        demo = kernel.get_module("demo")
        assert demo is not None, "demo module not loaded"
        assert demo.counter == 0
        print(f"  OK — module state: {kernel.get_status()['modules']['demo']['state']}")

        # Publish an event -> should increment counter
        await kernel.event_bus.publish("demo.command", {"cmd": "bump"})
        await asyncio.sleep(0.1)
        assert demo.counter >= 1, f"event not received: counter={demo.counter}"
        print(f"  OK — event bus delivered, counter={demo.counter}")

        # Capability provider lookup
        provider = kernel.get_capability_provider(Capability.EVENT_BUS_PUB)
        assert provider == "demo", f"capability provider wrong: {provider}"
        print(f"  OK — capability provider: {provider}")

        await kernel.stop()

    asyncio.run(run())
    os.unlink(tmp)
    print("  OK — kernel stopped cleanly")


def test_event_bus():
    """Test request/reply pattern."""
    print("─" * 60)
    print("3) Event bus request/reply")
    from orb_core.kernel import EventBus

    async def run():
        bus = EventBus()

        async def responder(event):
            await asyncio.sleep(0.01)
            bus.reply(event.reply_to, {"echo": event.data})

        bus.subscribe("ping", responder)
        result = await bus.request("ping", "hello")
        assert result == {"echo": "hello"}, f"reply wrong: {result}"
        print(f"  OK — request/reply returned: {result}")

    asyncio.run(run())


def test_protocol():
    """Test IPC message serialization roundtrip."""
    print("─" * 60)
    print("4) IPC protocol serialization")
    from orb_core.ipc import Message, Protocol

    msg = Message.request("deck.play", {"deck": "A", "position": 0.5})
    data = Protocol.encode(msg)
    decoded = Protocol.decode(data)
    assert decoded.method == "deck.play"
    assert decoded.params["deck"] == "A"
    print(f"  OK — roundtrip: {decoded.method} params={decoded.params}")

    # Stream decode with framing
    buffer = bytearray(Protocol.encode(msg) + Protocol.encode(msg))
    msgs = Protocol.decode_stream(buffer)
    assert len(msgs) == 2, f"expected 2 messages, got {len(msgs)}"
    print(f"  OK — stream decode: {len(msgs)} messages")


def test_config_store():
    """Test config store get/set/watch."""
    print("─" * 60)
    print("5) Config store")
    from orb_core.config import ConfigStore
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write('{"audio": {"sample_rate": 44100}}')
        tmp = f.name

    store = ConfigStore(Path(tmp))
    store.load()
    assert store.get("audio.sample_rate") == 44100
    print(f"  OK — dot-notation get: {store.get('audio.sample_rate')}")

    changes = []
    store.watch("theme", lambda k, v: changes.append((k, v)))
    store.set("theme", "neon")
    assert changes == [("theme", "neon")], f"watch not fired: {changes}"
    print(f"  OK — change watch fired: {changes}")

    os.unlink(tmp)


def test_neon_theme():
    """Test neon theme system."""
    print("─" * 60)
    print("6) Neon theme")
    from orb_core.neon import Theme, Glow

    theme = Theme("tron")
    accent = theme.c("accent")
    assert accent == "#00f0ff", f"wrong accent: {accent}"

    # Color math
    rgb = Glow.hex_to_rgb("#00f0ff")
    assert rgb == (0, 240, 255), f"wrong rgb: {rgb}"
    mid = Glow.lerp("#000000", "#ffffff", 0.5)
    assert mid == "#7f7f7f", f"wrong lerp: {mid}"

    print(f"  OK — accent={accent}, lerp mid={mid}")
    print(f"  OK — available themes: {theme.list_themes()}")


def test_platform():
    """Test platform abstraction."""
    print("─" * 60)
    print("7) Platform abstraction")
    from orb_core.platform import current_platform, is_windows, MIDI, FS

    plat = current_platform()
    print(f"  OK — platform detected: {plat.value}")
    print(f"  OK — midi input ports: {MIDI.get_input_names()}")
    print(f"  OK — file URL conversion: {FS.file_url_to_path('file:///C:/music/song.mp3')}")


def test_sandbox():
    """Test sandbox permissions."""
    print("─" * 60)
    print("8) Sandbox permissions")
    from orb_core.sandbox import Permissions, PermissionDenied
    from orb_core.manifest import Capability

    perms = Permissions()
    perms.grant("audio_engine", Capability.AUDIO_PLAYBACK)
    assert perms.check("audio_engine", Capability.AUDIO_PLAYBACK)
    try:
        perms.enforce("audio_engine", Capability.NETWORK_CLIENT)
        print("  FAIL — should have raised")
        return False
    except PermissionDenied as e:
        print(f"  OK — denied as expected: {e}")
    return True


def main():
    print("=" * 60)
    print("  ORB CORE SMOKE TEST")
    print("=" * 60)
    results = []
    tests = [
        test_manifest,
        test_kernel_lifecycle,
        test_event_bus,
        test_protocol,
        test_config_store,
        test_neon_theme,
        test_platform,
        test_sandbox,
    ]
    for t in tests:
        try:
            t()
            results.append((t.__name__, True))
        except Exception as e:
            import traceback
            traceback.print_exc()
            results.append((t.__name__, False))

    print("─" * 60)
    print("  RESULTS")
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    passed = sum(1 for _, ok in results if ok)
    print(f"  {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())