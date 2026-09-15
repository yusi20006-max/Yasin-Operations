from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "deploy" / "termux" / "runit" / "yasinhub" / "run"
INSTALLER = ROOT / "scripts" / "install-termux-yasinhub-runit.sh"


def test_yasinhub_runit_service_targets_control_plane():
    text = RUN.read_text()
    assert 'python" -m yasinhub.startup' in text
    assert "yasinhub.cli start yasin-agent" not in text
    assert "YASINHUB_ROOT" in text


def test_yasinhub_runit_service_documents_separate_agent_boundary():
    text = (RUN.parent / "README.md").read_text()
    assert "yasin-agent" in text
    assert "7000" in text
    assert "yasinhub.startup" in text


def test_yasinhub_runit_installer_is_present_and_safe():
    text = INSTALLER.read_text()
    assert 'sv down yasinhub' in text
    assert 'mv "$TARGET" "$backup"' in text
    assert 'ln -s "$SOURCE" "$TARGET"' in text
    assert 'sv up yasinhub' in text
    assert "yasinhub.cli start yasin-agent" not in text
