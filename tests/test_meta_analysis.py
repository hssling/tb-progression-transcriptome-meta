import numpy as np

from tbmeta.analysis.meta import random_effects_meta


def test_random_effects_meta_reasonable_output():
    effects = np.array([0.4, 0.5, 0.6])
    variances = np.array([0.05, 0.04, 0.05])
    mu, se, i2 = random_effects_meta(effects, variances)
    assert 0.3 < mu < 0.7
    assert se > 0
    assert 0 <= i2 <= 100
