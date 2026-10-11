import pytest

from prospectos import config


def test_token_se_lee_de_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("DENUE_TOKEN=abc123\n")
    assert config.get_token() == "abc123"


def test_falta_env_da_mensaje_accionable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match=r"Copia .env.example"):
        config.get_token()


def test_token_sin_valor_da_mensaje_accionable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("DENUE_TOKEN=\n")
    with pytest.raises(SystemExit, match="no tiene valor"):
        config.get_token()
