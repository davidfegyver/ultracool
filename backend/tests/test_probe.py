import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import analysis, sequences
from app.frames import grid_wcs_json, make_grid
from app.probe import flag_outliers, snap

SID = "00000000000000bb"


def _star(shape, x, y, flux, sigma=1.0):
    yy, xx = np.indices(shape)
    return flux / (2 * np.pi * sigma**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))


def test_snap_to_synthetic_peak():
    rng = np.random.default_rng(3)
    z = rng.standard_normal((41, 41)) + _star((41, 41), 20.7, 15.3, 35.0)  # matched-filter S/N ~10
    x, y, snr = snap(z, 21.5, 15.8, 6.4 / 2.75)  # click 2.6" off
    assert abs(x - 20.7) < 0.3 and abs(y - 15.3) < 0.3 and snr > 5
    assert snap(z, 23.7, 15.3, 6.4 / 2.75) is None  # 8" away: outside the 4" snap radius
    assert snap(rng.standard_normal((41, 41)), 20, 20, 6.4 / 2.75) is None  # nothing there


def test_preview_flags_cosmic_ray_frames():
    sx = [{"wavelength_um": 4.0 + 0.01 * i, "flux_ujy": 100.0 + i, "flux_err_ujy": 10.0, "flagged": False} for i in range(8)]
    sx[3]["flux_ujy"] = 5000.0
    flag_outliers(sx)
    assert [f["flagged"] for f in sx] == [i == 3 for i in range(8)]


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A synthetic finished sequence: a star at the grid centre in 6 W1 + 6 W2 visits and 24 SPHEREx frames,
    one SPHEREx frame entirely off the detector (NaN)."""
    monkeypatch.setattr(sequences, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(analysis, "_catalogs", lambda m: {"catwise": [], "simbad": []})  # no network in tests
    rng = np.random.default_rng(5)
    wcs, shape = make_grid(150.0, 0.0, 40 * 2.75 / 3600)
    cx, cy = wcs.wcs.crpix[0] - 1, wcs.wcs.crpix[1] - 1
    d = tmp_path / "seq" / SID / "npy"
    d.mkdir(parents=True)
    frames = []
    for i in range(36):
        survey = "wise" if i < 12 else "spherex"
        band = ("W1", "W2")[i % 2] if survey == "wise" else f"D{1 + i % 6}"
        img = rng.standard_normal(shape) + _star(shape, cx, cy, 200.0)
        if i == 35:
            img[:] = np.nan
        fid = f"wise-{band}-v{i:02d}" if survey == "wise" else f"sx-{i:02d}"
        np.save(d / f"{fid}.npy", img.astype(np.float32))
        frames.append({"id": fid, "survey": survey, "band": band, "kind": "visit" if survey == "wise" else "single",
                       "mjd": 55200.0 + 180 * i, "wavelength_um": 3.4 if band == "W1" else 4.6 if band == "W2" else 0.8 + 0.18 * (i - 12),
                       "flux_ujy": None, "flux_err_ujy": None, "flagged": False, "flag_names": [],
                       "magzp": 20.0 if survey == "wise" else None, "target_px": [cx, shape[0] - 1 - cy]})
    m = {"id": SID, "status": "done", "total": 36, "done": 36, "error": None, "wise_done": True,
         "grid": {"wcs": grid_wcs_json(wcs, shape), "width": shape[1], "height": shape[0]},
         "target": {"ra": 150.0, "dec": 0.0, "pmra_masyr": 0.0, "pmdec_masyr": 0.0, "epoch_yr": 2000.0},
         "frames": frames}
    (tmp_path / "seq" / SID / "manifest.json").write_text(json.dumps(m))
    from app.main import app
    return TestClient(app)


def test_probe_outside_grid_is_400(client):
    assert client.get(f"/api/sequences/{SID}/probe", params={"ra": 150.0, "dec": 0.02}).status_code == 400
    assert client.get(f"/api/sequences/{SID}/probe", params={"ra": 150.0, "dec": 0.0}).status_code == 200
    assert client.get("/api/sequences/00000000000000cc/probe", params={"ra": 150.0, "dec": 0.0}).status_code == 404


def test_preview_shape_without_nan(client):
    r = client.get(f"/api/sequences/{SID}/probe", params={"ra": 150.0 + 1.5 / 3600, "dec": 0.0})
    assert r.status_code == 200  # Starlette refuses NaN in JSON, so 200 means none
    p = r.json()
    assert {"status", "mode", "requested", "position", "pm", "frames", "color", "variability", "spectrum", "plain",
            "progress", "error"} <= p.keys()
    assert p["status"] == "ok" and p["mode"] == "preview" and p["plain"][0].startswith("Quick preview")
    assert p["position"]["snapped"] and p["position"]["snap_offset_arcsec"] == pytest.approx(1.5, abs=0.5)
    assert p["pm"]["source"] == "none"
    assert len(p["frames"]) == 36 and p["frames"][-1]["flux_ujy"] is None
    assert {"verdict", "w1_w2"} <= p["color"].keys() and "verdict" in p["variability"] and "verdict" in p["spectrum"]
    json.dumps(p, allow_nan=False)


def test_probe_on_empty_sky_is_not_sure(client):
    """No clear source at the point: no colour class, no variability verdict, no period."""
    p = client.get(f"/api/sequences/{SID}/probe", params={"ra": 150.0 + 20 / 3600, "dec": 0.0}).json()
    assert not p["position"]["snapped"] and p["pm"]["source"] == "none"
    assert p["color"]["verdict"] == "insufficient data" and p["color"]["w1_w2"] is None
    assert p["variability"]["verdict"] == "insufficient data" and p["variability"]["period_days"] is None
    assert any("no clear source" in s for s in p["plain"][2:])
