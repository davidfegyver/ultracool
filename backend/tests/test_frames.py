import numpy as np
import pytest

from app.frames import aperture_flux, deep_stack, group_by_gap, propagate


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


def test_deep_stack_reveals_source_below_single_frame_noise():
    rng = np.random.default_rng(3)
    frames = []
    for i in range(25):
        img = rng.standard_normal((40, 40))
        img[20, 20] += 1.0  # 1 sigma per frame: invisible alone
        img[5, 5] = 50.0 if i == 0 else img[5, 5]  # one cosmic ray
        frames.append(img)
    z = deep_stack(frames)
    assert z[20, 20] > 3.5  # ~sqrt(25) = 5 sigma expected
    assert abs(z[5, 5]) < 3  # clipped


def test_deep_stack_rejects_outlier_among_four_frames():
    rng = np.random.default_rng(4)
    frames = [rng.standard_normal((30, 30)) for _ in range(4)]
    frames[2][10, 10] = 80.0  # hot pixel in one of four visits
    assert abs(deep_stack(frames)[10, 10]) < 3
