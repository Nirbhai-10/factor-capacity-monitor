from aegis_mesh.orchestrator.audit import AuditLog


def test_chain_verifies():
    log = AuditLog()
    for i in range(20):
        log.append(float(i), "decision", {"track_id": i})
    assert log.verify()
    assert len(log.records) == 20


def test_tamper_detected():
    log = AuditLog()
    for i in range(10):
        log.append(float(i), "decision", {"track_id": i})
    assert log.verify()
    log._records[4].payload["track_id"] = 999  # retroactive edit
    assert not log.verify()
