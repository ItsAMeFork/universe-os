"""Track newly registered launchers per user; no change to system app defaults."""
def reconcile(apps, previous):
    ids = [app['id'] for app in apps]
    if not isinstance(previous, dict) or not isinstance(previous.get('seen'), list):
        return {'seen': ids, 'planets': []}
    seen = {value for value in previous['seen'] if isinstance(value, str)}
    stored = previous.get('planets', [])
    planets = [value for value in stored if isinstance(value, str) and value in ids] if isinstance(stored, list) else []
    for value in ids:
        if value not in seen and value not in planets:
            planets.append(value)
    return {'seen': ids, 'planets': planets}
