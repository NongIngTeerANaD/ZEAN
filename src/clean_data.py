"""Clean the Final DataViz datasets without touching the raw files.

Usage: python clean_data.py <BASE_FOLDER> [OUT_FOLDER]
BASE_FOLDER holds 01_AI_Incident_Database ... 04_Thai_Disinformation_and_Scams.
Outputs are UTF-8 (with BOM) CSV files plus cleaning_log.csv.
"""
import sys
import os
import glob
import numpy as np
import pandas as pd

BASE = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "clean")
os.makedirs(OUT, exist_ok=True)
LOG = []


def log(step, table, before, after, note=""):
    LOG.append(dict(step=step, table=table, rows_before=before, rows_after=after, note=note))


def save(df, name):
    df.to_csv(os.path.join(OUT, name), index=False, encoding="utf-8-sig")
    print(f"saved {name}: {df.shape}")


# ---------------------------------------------------------------- AIID
A = os.path.join(BASE, "01_AI_Incident_Database", "AIID_Excel_Export-20261026.xlsx")
inc = pd.read_excel(A, sheet_name="Incidents", header=2)
n0 = len(inc)
inc = inc.dropna(subset=["Incident ID"]).copy()
inc["Incident ID"] = inc["Incident ID"].astype(int)
assert inc["Incident ID"].is_unique
inc["date"] = pd.to_datetime(inc["date"])
inc["year"] = inc["date"].dt.year
inc["month"] = inc["date"].dt.to_period("M").astype(str)
log("parse dates, drop rows without ID", "aiid_incidents", n0, len(inc), "header row is the 3rd row of the sheet")

ISO2_TO_ISO3 = {
    "AR": "ARG", "AU": "AUS", "CA": "CAN", "CH": "CHE", "CN": "CHN", "DE": "DEU", "FR": "FRA",
    "GB": "GBR", "GR": "GRC", "ID": "IDN", "IE": "IRL", "IL": "ISR", "IN": "IND", "IT": "ITA",
    "JP": "JPN", "KR": "KOR", "LY": "LBY", "NL": "NLD", "NZ": "NZL", "PS": "PSE", "RS": "SRB",
    "RU": "RUS", "SE": "SWE", "US": "USA", "VN": "VNM",
}
cc = inc["Country Code"].astype("string").str.strip().replace({"United States": "US", "": pd.NA})
assert set(cc.dropna()) <= set(ISO2_TO_ISO3), set(cc.dropna()) - set(ISO2_TO_ISO3)
inc["country_iso2"] = cc
inc["country_iso3"] = cc.map(ISO2_TO_ISO3)
log("clean country code", "aiid_incidents", len(inc), len(inc),
    f"{int(cc.notna().sum())} rows with a country; blanks set to missing, 'United States' mapped to US")

for c in ["Risk Domain", "Risk Subdomain", "Intent", "Timing", "Responsible Entity", "Location Region",
          "AI Harm Level", "Autonomy Level"]:
    inc[c] = inc[c].astype("string").str.strip()
inc["is_classified"] = inc["Risk Domain"].notna()
inc["has_csetv1"] = inc["AI Harm Level"].notna()
text = (inc["title"].fillna("") + " " + inc["description"].fillna("")).str.lower()
inc["flag_deepfake_kw"] = text.str.contains(r"deepfake|deep fake|deep-fake|voice clon|cloned voice|face.?swap", regex=True)
inc["flag_deepfake_title"] = inc["title"].fillna("").str.lower().str.contains(r"deepfake|deep fake|deep-fake|voice clon|cloned voice|face.?swap", regex=True)
inc["flag_misinformation_domain"] = inc["Risk Domain"].eq("Misinformation")
keep = ["Incident ID", "date", "year", "month", "title", "description", "deployer", "developer", "harmed",
        "report_count", "Risk Domain", "Risk Subdomain", "Responsible Entity", "Intent", "Timing",
        "is_classified", "has_csetv1", "Location Region", "country_iso2", "country_iso3",
        "AI Harm Level", "Autonomy Level", "flag_deepfake_kw", "flag_deepfake_title", "flag_misinformation_domain", "Date Modified"]
save(inc[keep], "aiid_incidents_clean.csv")

rows, prev = [], None
files = sorted(glob.glob(os.path.join(BASE, "01_AI_Incident_Database", "weekly_versions", "*.xlsx"))) + [A]
for p in files:
    ids = set(pd.read_excel(p, sheet_name="Incidents", header=2, usecols=[0]).iloc[:, 0].dropna().astype(int))
    rows.append(dict(snapshot=pd.to_datetime(os.path.basename(p)[-13:-5]), n_incidents=len(ids),
                     new_incidents=(len(ids - prev) if prev is not None else pd.NA),
                     removed_incidents=(len(prev - ids) if prev is not None else pd.NA)))
    prev = ids
save(pd.DataFrame(rows), "aiid_snapshot_growth.csv")

# ---------------------------------------------------------------- Freedom on the Net
fo = pd.read_csv(os.path.join(BASE, "02_Freedom_on_the_Net", "freedom_on_the_net_scores.csv"), encoding="utf-8-sig")
n0 = len(fo)
assert not fo.duplicated(["iso3", "data_year"]).any()
assert (fo.total_score == fo.obstacles_to_access + fo.limits_on_content + fo.violations_of_user_rights).all()
fo["country_clean"] = fo["country"].str.replace(r"\s*\(the\)$", "", regex=True).str.strip()
ASEAN = {"THA", "IDN", "MYS", "PHL", "SGP", "VNM", "MMR", "KHM", "LAO", "BRN"}
fo["is_asean"] = fo["iso3"].isin(ASEAN)
fo["is_thailand"] = fo["iso3"].eq("THA")
g = fo.groupby("data_year")
fo["n_countries_year"] = g["iso3"].transform("count")
fo["world_mean_score"] = g["total_score"].transform("mean").round(2)
fo["rank_in_year"] = g["total_score"].rank(ascending=False, method="min").astype(int)
log("tidy names and add comparison columns", "fotn", n0, len(fo), "removed '(the)' from names; added ASEAN flag, yearly mean and rank")
save(fo, "fotn_clean.csv")

# ---------------------------------------------------------------- EUvsDisinfo
eu = pd.read_csv(os.path.join(BASE, "03_EUvsDisinfo", "euvsdisinfo_base.csv"), encoding="utf-8-sig")
n0 = len(eu)
eu["debunk_date"] = pd.to_datetime(eu["debunk_date"], format="%d-%m-%Y")
eu["year"] = eu["debunk_date"].dt.year
eu["month"] = eu["debunk_date"].dt.to_period("M").astype(str)
for c in ["keywords", "article_publisher", "article_domain", "article_language", "class"]:
    eu[c] = eu[c].astype("string").str.strip()
log("parse dates (day-month-year)", "euv_articles", n0, len(eu), "all dates parsed with %d-%m-%Y")
save(eu, "euv_articles_clean.csv")

deb = (eu.groupby("debunk_id")
         .agg(debunk_date=("debunk_date", "first"), year=("year", "first"), month=("month", "first"),
              n_articles=("article_id", "size"),
              n_disinformation=("class", lambda s: int((s == "disinformation").sum())),
              n_trustworthy=("class", lambda s: int((s == "trustworthy").sum())),
              keywords=("keywords", "first"))
         .reset_index())
log("one row per debunk", "euv_debunks", len(eu), len(deb), "counts of articles by class kept per debunk")
save(deb, "euv_debunks_clean.csv")

kw = deb[["debunk_id", "debunk_date", "year", "month", "keywords"]].dropna(subset=["keywords"]).copy()
kw["keyword"] = kw["keywords"].str.split(",")
kw = kw.explode("keyword")
kw["keyword"] = kw["keyword"].str.strip()
kw = kw[kw["keyword"] != ""].drop_duplicates(["debunk_id", "keyword"]).drop(columns="keywords")
log("split keywords to long table", "euv_keywords_long", len(deb), len(kw), "debunk x keyword")
save(kw, "euv_keywords_long.csv")

# ---------------------------------------------------------------- AFNC
P4 = os.path.join(BASE, "04_Thai_Disinformation_and_Scams", "csv")
af = pd.read_csv(os.path.join(P4, "afnc_items.csv"), encoding="utf-8-sig", usecols=lambda c: c != "content")
n0 = len(af)
assert af["post_id"].is_unique
af["date"] = pd.to_datetime(af["date"])
af["week_start"] = pd.to_datetime(af["week_start"])
af["ym"] = af["date"].dt.to_period("M").astype(str)
af["is_verdict"] = af["item_type"].eq("Verdict")
af["is_false"] = af["verdict_en"].isin(["Fake", "Distorted"])
log("parse dates, add verdict flags", "afnc_posts", n0, len(af), "content column left out to keep the file small")
save(af, "afnc_posts_clean.csv")

tg = af[["post_id", "date", "year", "ym", "category_en", "verdict_en", "topic_tags"]].dropna(subset=["topic_tags"]).copy()
tg["topic_tag"] = tg["topic_tags"].astype(str).str.split(";")
tg = tg.explode("topic_tag")
tg["topic_tag"] = tg["topic_tag"].str.strip()
tg = tg[tg["topic_tag"] != ""].drop_duplicates(["post_id", "topic_tag"]).drop(columns="topic_tags")
log("split topic tags to long table", "afnc_topic_tags_long", len(af), len(tg), "post x tag")
save(tg, "afnc_topic_tags_long.csv")

# ---------------------------------------------------------------- ACSC and weekly panel
def type_group(s):
    if pd.isna(s):
        return pd.NA
    if "ลงทุน" in s or "การเงิน" in s:
        return "Investment / finance"
    if "แอบอ้าง" in s:
        return "Impersonation"
    if "ข่มขู่" in s:
        return "Phone threats"
    if "รางวัล" in s or "รายได้พิเศษ" in s:
        return "Prize / easy-income transfer"
    if "ทำงาน" in s:
        return "Online job"
    if "สินค้า" in s or "ซื้อ" in s:
        return "Goods / services purchase"
    return "Other"


ac = pd.read_csv(os.path.join(P4, "acsc_weekly.csv"), encoding="utf-8-sig", parse_dates=["week_start", "week_end"])
ac["is_suspect"] = ac["flag"].fillna("").str.contains("Suspect")
ac["top_type_group"] = ac["top_type_th"].map(type_group)
ac["highest_loss_type_group"] = ac["highest_loss_type_th"].map(type_group)
ac["is_tied_label"] = ac["top_type_th"].fillna("").str.contains("tied") | ac["highest_loss_type_th"].fillna("").str.contains("tied")
ac["publisher_clean"] = (ac["publisher"].astype("string").str.lower().str.replace(r"[^a-z0-9ก-๙]", "", regex=True))
log("group crime type labels", "acsc_weekly", len(ac), len(ac), "22 raw labels mapped to 6 groups; raw labels kept; suspect week flagged, values unchanged")
save(ac, "acsc_weekly_clean.csv")

wk = pd.read_csv(os.path.join(P4, "weekly_panel.csv"), encoding="utf-8-sig", parse_dates=["week_start", "week_end"])
wk["ym"] = wk["week_start"].dt.to_period("M").astype(str)
wk["acsc_reported"] = wk["acsc_reported"].astype(bool)
wk["has_afnc"] = wk["afnc_verdicts"] > 0
wk["acsc_is_suspect"] = wk["acsc_flag"].fillna("").str.contains("Suspect")
wk["acsc_top_type_group"] = wk["acsc_top_type_th"].map(type_group)
wk["acsc_highest_loss_type_group"] = wk["acsc_highest_loss_type_th"].map(type_group)
wk["data_status"] = np.select(
    [wk["acsc_reported"] & wk["acsc_is_suspect"], wk["acsc_reported"] & wk["has_afnc"],
     wk["acsc_reported"], wk["has_afnc"]],
    ["acsc_suspect", "complete", "acsc_only", "afnc_only"], default="no_data")
log("add quality columns", "weekly_panel", len(wk), len(wk), "no zero filling; missing ACSC weeks stay missing")
save(wk, "weekly_panel_clean.csv")

# ---------------------------------------------------------------- cross checks
assert af["is_verdict"].sum() == wk["afnc_verdicts"].sum(), (af["is_verdict"].sum(), wk["afnc_verdicts"].sum())
per_week = af[af["is_verdict"]].groupby("week_start").size()
cmp_ = wk.set_index("week_start")["afnc_verdicts"].sub(per_week, fill_value=0).abs()
print("weeks where weekly_panel verdicts differ from afnc posts:", int((cmp_ > 0).sum()))
log("cross check", "afnc_posts vs weekly_panel", int(af["is_verdict"].sum()), int(wk["afnc_verdicts"].sum()),
    f"weeks that differ: {int((cmp_ > 0).sum())}")
pd.DataFrame(LOG).to_csv(os.path.join(OUT, "cleaning_log.csv"), index=False, encoding="utf-8-sig")
print("deepfake keyword incidents (title+description):", int(inc["flag_deepfake_kw"].sum()), "| title only:", int(inc["flag_deepfake_title"].sum()),
      "| classified:", int(inc["is_classified"].sum()), "| with iso3:", int(inc["country_iso3"].notna().sum()))
print(wk["data_status"].value_counts().to_dict())
print(ac["top_type_group"].value_counts().to_dict())
