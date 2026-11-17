"""Exclude desktop fixtures only; retain every selected module's core tests."""
def pytest_collection_modifyitems(config, items):
    core, desktop = [], []
    for item in items:
        (desktop if 'app' in item.fixturenames else core).append(item)
    items[:] = core
    if desktop:
        config.hook.pytest_deselected(items=desktop)
