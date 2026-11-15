"""Self-check: is the type driven by the photometry choice? Re-type every measured object from the cached dev-API manifest
with (1) plain aperture photometry (spectral.classify on the manifest frames) and (2) the neighbour-subtracted PSF fit
(analysis.neighbour_frames), whichever the pipeline did not use. Read-only import of the current backend code; the
dev cache is only read (psfphot cache files already exist from /summary).
Writes out/<tag>/photometry_check.json. Run: CACHE_DIR=/data/devcache/discovery2 python scripts/aperture_check.py <tag> ..."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("../../backend").resolve()))
from app import analysis, spectral  # noqa: E402
from app.sequences import load_manifest  # noqa: E402


def short(sp):
    return {"verdict": sp["verdict"], "best": (sp.get("best") or {}).get("label"), "chi2_red": (sp.get("best") or {}).get("chi2_red"),
            "type_range": sp.get("type_range"), "detection_snr": sp.get("detection_snr"), "doubt": sp.get("doubt"),
            "top5": [(r["label"], round(r["chi2_red"], 2)) for r in sp.get("ranking") or []]}


for tag in sys.argv[1:]:
    met = json.loads((Path("out") / tag / "metrics.json").read_text())
    m = load_manifest(met["seq_id"])
    ap = spectral.classify(m["frames"])
    psf_frames, nb, blends = analysis.neighbour_frames(m)
    ps = spectral.classify(psf_frames) if psf_frames else None
    out = {"tag": tag, "seq_id": met["seq_id"], "pipeline_used": met["spectrum"]["photometry"], "aperture": short(ap),
           "psf": short(ps) if ps else None, "neighbour_frac": nb, "blends_arcsec": blends}
    (Path("out") / tag / "photometry_check.json").write_text(json.dumps(out, indent=1, default=float))
    print(tag, "used:", out["pipeline_used"], "| aperture:", out["aperture"]["best"], out["aperture"]["type_range"], out["aperture"]["top5"][:3],
          "| psf:", out["psf"] and (out["psf"]["best"], out["psf"]["type_range"], out["psf"]["top5"][:3]))
