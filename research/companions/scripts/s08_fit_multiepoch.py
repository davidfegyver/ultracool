"""Step 8: independent multi-epoch PMs for the two open candidates whose UCD has no Gaia 5-parameter solution, from
catalogue positions saved in raw/astrom/*.tsv (CfA VizieR) plus the CatWISE2020 2015.4 position as copied into
UltracoolSheet (ra/dec_epoch_WISE, ref Maro21). Weighted linear fit per axis, sigma = 0.10" per epoch (assumed;
Gaia 2-parameter position: its quoted error), errors scaled by sqrt(chi2_red) if > 1.
Run: ../../.venv/bin/python scripts/s08_fit_j1119.py"""
import numpy as np

SETS = {
    "ULAS J111929.43+002133.1": dict(
        host=("Gaia DR3 3798153658479923968", 18.330, -59.414),
        ep=[("SDSS DR16 (V/154, MJD 51257.27)", 1999.2140, 169.872615, 0.359313, 0.10),
            ("UKIDSS LAS DR9 (II/319)", 2008.3419, 169.872697, 0.359208, 0.10),
            ("PS1 DR2 mean (II/349, MJD 56050.16)", 2012.3708, 169.872662020, 0.3591177, 0.10),
            ("CatWISE2020 ep. 2015.4 (UCS)", 2015.4, 169.8726255, 0.3591766, 0.10)]),
    "SDSS J134338.74-022044.6": dict(
        host=("Gaia DR3 3658413770767688192", -140.719, 122.140),
        ep=[("SDSS DR16 (MJD 51586.50)", 2000.1150, 205.911443, -2.345795, 0.10),
            ("2MASS (JD 2451943.82)", 2001.0928, 205.911342, -2.345733, 0.10),
            ("SDSS DR16 (MJD 52053.25)", 2001.3929, 205.911407, -2.345710, 0.10),
            ("SDSS DR16 (MJD 53881.20)", 2006.3976, 205.911161, -2.345559, 0.10),
            ("UKIDSS LAS DR9 (II/319)", 2010.5702, 205.911007, -2.345379, 0.10),
            ("CatWISE2020 ep. 2015.4 (UCS)", 2015.4, 205.9108334, -2.3452299, 0.10),
            ("Gaia DR3 2-param 3658413667689105920", 2016.0, 205.91080412552, -2.34523459749, 0.0027)]),
}
for name, s in SETS.items():
    t = np.array([e[1] for e in s["ep"]]); ra = np.array([e[2] for e in s["ep"]]); de = np.array([e[3] for e in s["ep"]])
    w = 1 / (np.array([e[4] for e in s["ep"]]) * 1000) ** 2
    x = (ra - ra.mean()) * np.cos(np.radians(de.mean())) * 3.6e6
    y = (de - de.mean()) * 3.6e6
    A = np.vstack([np.ones_like(t), t - t.mean()]).T
    out = []
    for lab, v in (("pmRA*", x), ("pmDE", y)):
        cov = np.linalg.inv(A.T @ (A * w[:, None]))
        coef = cov @ A.T @ (w * v)
        chi2r = float(np.sum(w * (v - A @ coef) ** 2) / (len(t) - 2))
        err = float(np.sqrt(cov[1, 1]) * max(1, np.sqrt(chi2r)))
        out.append((coef[1], err))
        print(f"{name} {lab} = {coef[1]:.1f} +- {err:.1f} mas/yr (chi2_red {chi2r:.2f}); residuals mas:", np.round(v - A @ coef).tolist())
    h = s["host"]
    d = np.array([out[0][0] - h[1], out[1][0] - h[2]]); e = np.array([out[0][1], out[1][1]])
    print(f"  host {h[0]} ({h[1]}, {h[2]}): delta = ({d[0]:.1f}, {d[1]:.1f}) mas/yr = ({d[0]/e[0]:.1f}, {d[1]/e[1]:.1f}) sigma")
