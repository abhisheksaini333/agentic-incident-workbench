from incident.settings import Settings

def test_configuration_representation_does_not_leak_secrets():
    s=Settings(database_url="postgresql://alice:database-secret@localhost/db", jwt_secret="jwt-secret-"*4, simulator_key="simulator-secret-"*3, simulator_admin_key="admin-secret")
    for secret in [s.database_url,s.jwt_secret,s.simulator_key,s.simulator_admin_key]:
        assert secret not in repr(s)
    assert s.jwt_secret.startswith("jwt-secret")
