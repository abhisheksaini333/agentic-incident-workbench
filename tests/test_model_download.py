import io
import ssl

from scripts import fetch_model


def test_model_download_passes_verified_context_to_every_request(tmp_path, monkeypatch):
    context = fetch_model.trusted_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    calls = []

    def open_url(url, *, timeout, context=None):
        assert context is expected_context
        assert timeout == 60
        calls.append(url)
        return io.BytesIO(b"downloaded model fixture")

    expected_context = context
    monkeypatch.setattr(fetch_model, "trusted_context", lambda: expected_context)
    monkeypatch.setattr(fetch_model.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(fetch_model, "verify_files", lambda directory, items: None)
    monkeypatch.setattr(fetch_model.sys, "argv", ["fetch_model.py", str(tmp_path)])
    fetch_model.main()
    assert len(calls) == 6
    assert len(list(tmp_path.iterdir())) == 6
