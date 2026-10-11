from __future__ import annotations

from dsserver.config import Config, load_config


def test_port_for_selects_prod_and_test():
    config = Config(port=8787, test_port=8788)
    assert config.port_for("prod") == 8787
    assert config.port_for("test") == 8788


def test_load_config_reads_test_port_and_smart_zone(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'port = 9000\ntest_port = 9001\nsmart_zone_tokens = 120000\n', encoding="utf-8"
    )
    config = load_config(path)
    assert config.port == 9000
    assert config.test_port == 9001
    assert config.smart_zone_tokens == 120000


def test_load_config_defaults_test_port_and_smart_zone(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("port = 8787\n", encoding="utf-8")
    config = load_config(path)
    assert config.test_port == 8788
    assert config.smart_zone_tokens == 150000
