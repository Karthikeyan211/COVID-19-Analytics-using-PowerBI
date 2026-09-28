"""COVID-19 ETL: builds synthetic epidemiology data -> star-schema CSVs + dashboard JSON.
Run:  pip install pandas numpy  &&  python python_etl/etl_pipeline.py
"""
import json, shutil, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, WEB = ROOT / "data/processed", ROOT / "web_dashboard/data"
log = []
def say(m): log.append(f"{dt.datetime.now():%H:%M:%S}  {m}"); print(m)
for p in (PROC, WEB / "csv"): p.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)
sig = lambda x: 1 / (1 + np.exp(-x))

# code, name, continent, population, iso3, lat, lng, severity, vaccine plateau, wave shift (days)
C = [("US","United States","North America",331e6,"USA",39.8,-98.6,1.0,.78,0),
     ("IN","India","Asia",1.38e9,"IND",22.0,79.0,.45,.72,50),
     ("BR","Brazil","South America",212e6,"BRA",-10.0,-52.0,.9,.80,20),
     ("GB","United Kingdom","Europe",67e6,"GBR",54.0,-2.5,1.1,.82,-10),
     ("DE","Germany","Europe",83e6,"DEU",51.0,10.4,.8,.80,0),
     ("FR","France","Europe",67e6,"FRA",46.6,2.4,1.0,.80,-5),
     ("JP","Japan","Asia",125e6,"JPN",36.2,138.3,.5,.83,70),
     ("ZA","South Africa","Africa",59e6,"ZAF",-29.0,24.0,.6,.42,15),
     ("AU","Australia","Oceania",25.7e6,"AUS",-25.0,134.0,.5,.86,90)]
V = ["Wildtype", "Alpha", "Delta", "Omicron"]
say("Generating daily epidemiology data (Wildtype, Alpha, Delta, Omicron waves)")

dates = pd.date_range("2020-03-01", "2022-12-31"); n = len(dates)
t = np.arange(n); dow = dates.dayofweek.values; key = dates.strftime("%Y%m%d").astype(int)
ma = lambda x: pd.Series(x).rolling(7, min_periods=1).mean().values
fd, fv_, series, vc = [], [], {}, np.zeros((n, 4))

for code, name, cont, pop, iso, lat, lng, sev, plat, s in C:
    b = lambda c, w, a: a * np.exp(-((t - c - s) / w) ** 2)
    per = b(260, 40, 15) + b(320, 35, 25) + b(532, 40, 30) + b(690, 22, 120) + 1.5
    cases = np.round(per * pop / 1e5 * sev * rng.lognormal(0, .12, n) * np.where(dow >= 5, .75, 1)).astype(int)
    a, d, o = sig((t - s - 290) / 15), sig((t - s - 505) / 12), sig((t - s - 670) / 6)
    sh = np.column_stack([1 - a, a - d, d - o, o])
    cfr = (0.02 * np.exp(-t / 400) + 0.002) * (1 - .6 * o)
    deaths = np.round(np.concatenate([np.zeros(14), cases[:-14]]) * cfr * rng.lognormal(0, .15, n)).astype(int)
    pos = np.clip((.02 + .28 * (1 - np.exp(-per * sev / 50))) * rng.lognormal(0, .05, n), 0, 1)
    ma7, md7 = ma(cases), ma(deaths)
    cfrp = np.cumsum(deaths) / np.maximum(np.cumsum(cases), 1) * 100
    pv = plat * sig((t - s - 420) / 60) * np.clip((t - 270) / 30, 0, 1) * 100
    fv = plat * .93 * sig((t - s - 460) / 60) * np.clip((t - 285) / 30, 0, 1) * 100
    bo = plat * .6 * sig((t - s - 660) / 50) * np.clip((t - 560) / 30, 0, 1) * 100
    tot = pop * (pv + fv + bo) / 100
    vc += sh * cases[:, None]
    fd.append(pd.DataFrame({"CountryCode": code, "DateKey": key, "NewCases": cases, "NewDeaths": deaths,
        "MovingAvg7DayCases": ma7.round(1), "MovingAvg7DayDeaths": md7.round(1), "CFR_Pct": cfrp.round(3),
        "PositivityRate": pos.round(4), "VariantID": sh.argmax(1) + 1}))
    fv_.append(pd.DataFrame({"CountryCode": code, "DateKey": key, "TotalVaccinations": tot.astype("int64"),
        "PeopleVaccinated": (pop * pv / 100).astype("int64"), "PeopleFullyVaccinated": (pop * fv / 100).astype("int64"),
        "BoosterDoses": (pop * bo / 100).astype("int64"), "VaccinationsPer100": (tot / pop * 100).round(2)}))
    series[code] = {"cases": cases.tolist(), "ma7": ma7.round(1).tolist(), "deaths": deaths.tolist(),
        "pv": pv.round(2).tolist(), "full": fv.round(2).tolist(), "boost": bo.round(2).tolist(), "pos": pos.round(4).tolist()}

say("Building star schema tables")
tables = {
 "dim_country": pd.DataFrame([(c[0], c[1], c[2], int(c[3]), c[4], c[5], c[6]) for c in C],
     columns=["CountryCode","Country","Continent","Population","Iso3","Latitude","Longitude"]),
 "dim_date": pd.DataFrame({"DateKey": key, "Date": dates.strftime("%Y-%m-%d"), "Year": dates.year,
     "Quarter": dates.quarter, "Month": dates.month, "MonthName": dates.strftime("%b"),
     "WeekNumber": dates.isocalendar().week.values}),
 "dim_variant": pd.DataFrame({"VariantID": [1,2,3,4], "VariantName": V,
     "WHO_Label": ["Original strain","Alpha (B.1.1.7)","Delta (B.1.617.2)","Omicron (B.1.1.529)"]}),
 "fact_covid_daily": pd.concat(fd), "fact_vaccinations": pd.concat(fv_)}
for name, df in tables.items():
    df.to_csv(PROC / f"{name}.csv", index=False); shutil.copy(PROC / f"{name}.csv", WEB / "csv" / f"{name}.csv")
    say(f"Wrote {name}.csv ({len(df):,} rows)")

dax = ROOT / "powerbi/dax_measures.dax"
if dax.exists(): shutil.copy(dax, WEB / "dax_measures.dax"); say("Copied dax_measures.dax for the DAX Studio tab")

vm = pd.DataFrame(vc, index=dates, columns=V).resample("MS").sum()
vm = vm.div(vm.sum(1), axis=0) * 100
variants = {"months": [d.strftime("%b %Y") for d in vm.index], **{c: vm[c].round(1).tolist() for c in V}}
say("Computed monthly variant shares")
out = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "dates": dates.strftime("%Y-%m-%d").tolist(),
       "countries": [{"code": c[0], "name": c[1], "continent": c[2], "pop": int(c[3]), "iso3": c[4], "lat": c[5], "lng": c[6]} for c in C],
       "series": series, "variants": variants, "files": [f"{k}.csv" for k in tables]}
say("Wrote covid_dashboard_data.json - pipeline complete")
out["log"] = log
(WEB / "covid_dashboard_data.json").write_text(json.dumps(out, separators=(",", ":")))
