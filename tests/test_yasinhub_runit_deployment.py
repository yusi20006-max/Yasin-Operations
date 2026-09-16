from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "deploy/termux/runit/yasinhub/run"
INSTALLER = ROOT / "scripts/install-termux-yasinhub-runit.sh"


def test_yasinhub_runit_default_uses_dedicated_runtime_root():
    text = RUN.read_text(encoding="utf-8")
    assert "$HOME/yasineco/YasinHub-runtime" in text
    assert "$HOME/yasineco/YasinHub}" not in text


def test_yasinhub_installer_persists_runtime_root():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "$HOME/yasineco/YasinHub-runtime" in text
    assert 'printf \'%s\\n\' "$HUB_ROOT" >"$TARGET/root"' in text
    assert 'YASINHUB_ROOT="$(cat "$(dirname "$0")/root")"' in text
    assert 'ln -s "$SOURCE" "$TARGET"' not in text


def test_yasinhub_installer_keeps_runit_as_supervisor():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "sv up yasinhub" in text
    assert "python -m yasinhub.startup" in text
