# ZEAN - Misinformation and Online Threats Dashboard (Final DataViz)

Dashboard on misinformation and online threats, world and Thailand.

## Data (data/ = cleaned files)
| File | Grain | Rows |
|---|---|---|
| aiid_incidents_clean.csv | 1 row per AI incident (AIID) | 1,775 |
| aiid_snapshot_growth.csv | 1 row per database snapshot | 13 |
| fotn_clean.csv | 1 row per country-year (Freedom on the Net) | 940 |
| euv_articles_clean.csv | 1 row per article (EUvsDisinfo) | 18,249 |
| euv_debunks_clean.csv | 1 row per debunk | 8,522 |
| euv_keywords_long.csv | debunk-keyword pairs | 29,842 |
| afnc_posts_clean.csv | 1 row per post (AFNC, Thailand) | 17,726 |
| afnc_topic_tags_long.csv | post-topic pairs | 51,662 |
| acsc_weekly_clean.csv | 1 row per week (ACSC) | 48 |
| weekly_panel_clean.csv | AFNC + ACSC joined by week_start | 409 |
| cleaning_log.csv | cleaning steps and checks | - |

Cleaning script: `src/clean_data.py`. Raw files are not included in this repo.

## Caveats
- ACSC counts come from news reports, not police data; missing weeks are not zero-filled.
- AIID risk classification is incomplete for 2026.
- EUvsDisinfo ends Aug 2023.

## Run
    pip install -r requirements.txt
    streamlit run app.py
