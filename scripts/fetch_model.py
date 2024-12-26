"""Download only immutable original model files, with hash verification."""
import argparse
import json
from pathlib import Path
import sys
import ssl
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model.server import verify_files


def trusted_context():
    context = ssl.create_default_context()
    # Python.org macOS installations may lack their optional certificate setup.
    # Add the operating system's public CA bundle without weakening verification.
    system_bundle = Path("/etc/ssl/cert.pem")
    if sys.platform == "darwin" and system_bundle.is_file():
        context.load_verify_locations(cafile=str(system_bundle))
    return context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="models/flan-t5-small")
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "models/manifest.json").read_text()
    )
    context = trusted_context()
    for item in manifest:
        target = directory / item["file"]
        if target.exists():
            verify_files(directory, [item])
            continue
        temporary = target.with_suffix(target.suffix + ".partial")
        with urllib.request.urlopen(
            item["url"], timeout=60, context=context
        ) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        temporary.rename(target)
        verify_files(directory, [item])
    print("Verified immutable original model files")


if __name__ == "__main__":
    main()
