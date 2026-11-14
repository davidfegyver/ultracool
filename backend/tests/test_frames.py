import numpy as np
import pytest

from app.frames import aperture_flux, group_by_gap, propagate


def test_aperture_recovers_gaussian_total():
    yy, xx = np.indices((41, 41))
    s = 1.5
    img = 1000 * np.exp(-((xx - 20) ** 2 + (yy - 20) ** 2) / (2 * s * s)) / (2 * np.pi * s * s)
    net, _ = aperture_flux(img, 20, 20, r_ap=6)
    assert net == pytest.approx(1000, rel=0.02)


def test_group_by_gap_splits_visits():
    assert group_by_gap([0, 1, 2, 200, 201], 10) == [0, 0, 0, 1, 1]


def test_propagate_pmra():
    ra, dec = propagate(10.0, 0.0, 1000, 0, 2000.0, 2003.6)
    assert ra - 10.0 == pytest.approx(0.001)
    assert dec == 0.0
