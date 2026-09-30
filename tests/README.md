# Engine tests

This directory owns the tests for the engine code in `src/`:

- `kernel/`: kernel lifecycle and system management.
- `systems/<module>/`: tests owned by one engine system, mirroring `src/systems/<module>/`.
- `integration/`: collaboration, UI/display lifecycle, and embedded Vision workflows spanning systems.

Keep a test's private helper headers beside that test. Introduce `support/` when
multiple test suites need the same helper; do not move production headers into it.
Editor, Vision, and `modules/corona_resource` keep their own test directories.

Each test directory defines its targets in a local `CMakeLists.txt`. The root
build adds `tests/` after the production modules when `BUILD_CORONA_TESTING` or
`BUILD_TESTING` is enabled. Vision-dependent engine tests also require
`CORONA_BUILD_VISION`.

Configure and build with the existing `tests-<configuration>` or
`vision-tests-<configuration>` presets, then run CTest directly. CMake adds the
Slang, TBB, Python, CEF, and renderer runtime directories to each test's `PATH`
on Windows. CLion's **All CTest** uses the same settings; no manual Conan runtime
activation is needed. Reload CMake after changing this configuration.

```powershell
ctest --test-dir build/conan/tests/relwithdebinfo -C RelWithDebInfo --output-on-failure
ctest --test-dir build/conan/vision-tests/relwithdebinfo -C RelWithDebInfo --output-on-failure
```

Set `CORONA_RUN_GPU_SMOKE=1` to opt into the UI GPU smoke test on a machine with a
usable GPU and desktop session.

The shader source checks remain Python tests and can be run in an environment
with pytest installed:

```powershell
python -m pytest tests/systems/optics -q
```

Tests that need private engine headers add the owning production directory as a
`PRIVATE` include directory. Resource-dependent tests specify their working
directory explicitly; preserve those settings when moving a test.
