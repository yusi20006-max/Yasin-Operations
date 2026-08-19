from scripts.production_acceptance import (
    FakeProbe,
    _runit_state,
    check_ecosystem_adapters,
    check_hermes,
)


def test_runit_state_normalization_is_authoritative():
    assert _runit_state("run: service: (pid 123) 10s") == "running"
    assert _runit_state("down: service: 10s, normally up") == "stopped"
    assert _runit_state("fail: service: 10s") == "failed"
    assert _runit_state("timeout: service: 10s") == "failed"
    assert _runit_state("unexpected output") == "unknown"


def test_fake_probe_matches_requested_service():
    snapshot = FakeProbe().inspect("Yasin-AI")
    assert snapshot.service == "Yasin-AI"
    assert snapshot.available is True
    assert snapshot.state == "running"


def test_hermes_acceptance_checks_use_current_typed_contract():
    results = check_hermes()
    assert results
    assert all(result.status == "PASS" for result in results)


def test_ecosystem_acceptance_checks_inject_probes():
    results = check_ecosystem_adapters()
    assert len(results) == 3
    assert all(result.status == "PASS" for result in results)
