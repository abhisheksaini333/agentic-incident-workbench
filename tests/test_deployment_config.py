from pathlib import Path
import yaml


def test_compose_parses_and_keeps_model_inference_opt_in():
    config = yaml.safe_load(Path("compose.yaml").read_text())
    assert config["services"]["model"]["profiles"] == ["models"]
    assert config["services"]["api"]["read_only"]
    assert config["services"]["worker"]["cap_drop"] == ["ALL"]
    assert config["services"]["api"]["ports"] == ["127.0.0.1:8085:8085"]
