import yaml, pathlib
def test_yaml_loads():
    for p in ["configs/weights.yaml","configs/normalization.yaml"]:
        assert pathlib.Path(p).exists()
        with open(p, "r", encoding="utf-8") as f:
            assert isinstance(yaml.safe_load(f), dict)
