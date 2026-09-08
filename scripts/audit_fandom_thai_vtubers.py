import urllib.request
import urllib.parse
import json
import re
from pathlib import Path
import pandas as pd

def run():
    manifest = pd.read_csv("data/temporal/catalog/target_manifest.csv")
    manifest_cids = set(manifest["channel_id"])
    print(f"Target manifest channels: {len(manifest_cids)}")

    # Fetch all pages in Category:Thai
    all_thai = []
    cmcontinue = ""
    while True:
        url = "https://virtualyoutuber.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category:Thai&cmlimit=100&format=json"
        if cmcontinue:
            url += f"&cmcontinue={cmcontinue}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            all_thai.extend([m["title"] for m in data.get("query", {}).get("categorymembers", [])])
            if "continue" in data and "cmcontinue" in data["continue"]:
                cmcontinue = data["continue"]["cmcontinue"]
            else:
                break

    creator_pages = [p for p in all_thai if not any(k in p.lower() for k in ["project", "stage", "easter:", "user:", "draft:", "category:"])]
    print(f"Total candidate creator wiki pages: {len(creator_pages)}")

    records = []
    print(f"Beginning crawl of {len(creator_pages)} pages...", flush=True)
    for idx, title in enumerate(creator_pages, 1):
        if idx % 10 == 0 or idx == 1:
            print(f"Scraping [{idx}/{len(creator_pages)}]: {title}", flush=True)
        try:
            t_enc = urllib.parse.quote(title)
            url = f"https://virtualyoutuber.fandom.com/api.php?action=parse&page={t_enc}&prop=wikitext&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req) as resp:
                pdata = json.loads(resp.read().decode())
                wtext = pdata.get("parse", {}).get("wikitext", {}).get("*", "")
                
                # Extract YouTube Channel ID if present
                ch_matches = re.findall(r"UC[a-zA-Z0-9_-]{22}", wtext)
                cid = ch_matches[0] if ch_matches else None
                
                # Extract debut date
                debut_match = re.search(r"\|\s*debut_date\s*=\s*([^\n<]+)", wtext)
                debut = debut_match.group(1).strip() if debut_match else None
                
                # Extract retirement / graduation date
                retire_match = re.search(r"\|\s*retirement_date\s*=\s*([^\n<]+)", wtext)
                retire = retire_match.group(1).strip() if retire_match else None
                
                # Check status
                status_match = re.search(r"\|\s*status\s*=\s*([^\n<]+)", wtext)
                status = status_match.group(1).strip() if status_match else None
                
                # Check agency / affiliation
                agency_match = re.search(r"\|\s*affiliation\s*=\s*([^\n<]+)", wtext)
                agency = agency_match.group(1).strip() if agency_match else None

                page_url = f"https://virtualyoutuber.fandom.com/wiki/{urllib.parse.quote(title)}"
                records.append({
                    "wiki_title": title,
                    "page_url": page_url,
                    "channel_id": cid,
                    "in_target_cohort": cid in manifest_cids if cid else False,
                    "debut_date_raw": debut,
                    "retirement_date_raw": retire,
                    "status_raw": status,
                    "agency_raw": agency,
                    "has_dates": bool(debut or retire)
                })
        except Exception as e:
            print(f"Error parsing {title}: {e}")

    df = pd.DataFrame(records)
    print("\nSummary of Scraped Wiki Pages:")
    print(f"Total pages scraped: {len(df)}")
    print(f"Pages with detected channel_id: {df['channel_id'].notna().sum()}")
    print(f"Pages in target cohort: {df['in_target_cohort'].sum()}")
    print(f"Pages with explicit debut/retire dates: {df['has_dates'].sum()}")
    
    # Show matched target cohort creators
    cohort_matches = df[df["in_target_cohort"] == True]
    print("\nTarget Cohort Matches from Wiki:")
    for _, r in cohort_matches.iterrows():
        print(f"  {r['wiki_title']} ({r['channel_id']}) -> Debut: {r['debut_date_raw']} | Retire: {r['retirement_date_raw']} | Status: {r['status_raw']}")

    out_csv = Path("data/industry/fandom_thai_vtubers_audit.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved full audit to {out_csv}")

if __name__ == "__main__":
    run()
