import numpy as np

from aegis_mesh.fusion.classifier import MODEL, featurize


def test_quad_vs_bird_vs_aircraft_separation():
    quad = MODEL.proba(featurize(24, 120, 0.02, 0.85, True, 1.0))
    bird = MODEL.proba(featurize(13, 90, 0.01, 0.05, False, 1.5))
    acft = MODEL.proba(featurize(110, 600, 5.0, 0.1, False, 3.0))
    assert max(quad, key=quad.get) == "uas"
    assert max(bird, key=bird.get) == "bird"
    assert max(acft, key=acft.get) == "aircraft"


def test_held_out_accuracy_above_threshold():
    from aegis_mesh.fusion.classifier import _sample
    X, y = _sample(np.random.default_rng(99), 2000)
    pred = []
    cls = ["uas", "bird", "aircraft", "clutter"]
    for f in X:
        p = MODEL.proba(f)
        pred.append(cls.index(max(p, key=p.get)))
    acc = (np.array(pred) == y).mean()
    assert acc > 0.80, acc
