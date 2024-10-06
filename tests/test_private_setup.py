import os
import pytest
from scripts.init_demo import initialize


def test_setup_never_overwrites_existing_secrets_and_disables_experiments(tmp_path):
    path = tmp_path / ".env"
    initialize(path)
    original = path.read_bytes()
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert b"ENABLE_MODEL_MODES=0" in original
    with pytest.raises(FileExistsError):
        initialize(path)
    assert path.read_bytes() == original
