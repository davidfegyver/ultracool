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


def test_aperture_errors_match_real_scatter():
    rng = np.random.default_rng(5)
    var = np.full((60, 60), 4.0)
    nets, errs = [], []
    for _ in range(300):
        net, err = aperture_flux(rng.normal(0, 2, (60, 60)), 30, 30, 3, 8, 14, var=var)
        nets.append(net)
        errs.append(err)
    assert np.std(nets) == pytest.approx(np.median(errs), rel=0.15)


def test_masked_pixel_in_aperture_keeps_total():
    yy, xx = np.indices((41, 41))
    img = 1000 * np.exp(-((xx - 20) ** 2 + (yy - 20) ** 2) / (2 * 1.5**2)) / (2 * np.pi * 1.5**2)
    mask = np.zeros(img.shape, bool)
    mask[23, 20] = True  # a flagged pixel in the wing
    net, _ = aperture_flux(img, 20, 20, r_ap=6, mask=mask)
    assert net == pytest.approx(1000, rel=0.05)


def test_crowded_annulus_uses_mode_sky_and_confusion_error():
    """SOURCE flags cover the whole annulus: the fallback sky must not be pulled up by the sources, and the
    error must include the source-to-source scatter (confusion), not just pixel noise."""
    rng = np.random.default_rng(6)
    img = rng.normal(0, 0.01, (61, 61))
    for _ in range(120):  # crowded field of faint point sources
        yy, xx = np.indices(img.shape)
        x0, y0 = rng.uniform(0, 61, 2)
        img += 2.0 * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / 2) / (2 * np.pi)
    var = np.full(img.shape, 1e-4)
    src = np.ones(img.shape, bool)  # SOURCE everywhere
    _, err_plain = aperture_flux(img, 30, 30, 2, 4, 7, var=var)
    net, err = aperture_flux(img, 30, 30, 2, 4, 7, var=var, bkg_mask=src)
    assert err > 2 * err_plain  # confusion dominates the pixel noise
    assert abs(net) < 4 * err
