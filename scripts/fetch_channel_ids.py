import urllib.request
import re
import json

cids = [
  ("Noeluc", "@noeluc_", "UCkvce0jZJYBWJLTuKoLIvLA", "Independent"),
  ("Chiziz R Fa", "@ChizizFa", "UCtJXU7YRwS-Cc8pu8U8bicg", "Independent"),
  ("Aozora Sukai Ch.", "@SukaiVtuber", "UCP8tsYT8efX32P4WUlNrFOA", "Independent"),
  ("Kuroyoru Yami", "@kuroyoruyami", "UC2q-fPPrsyKOjRpmm--vzPQ", "Independent"),
  ("crazyghsot", "@crazyghsot", "UCfIXIjmCUKMBdmB2EspTygw", "Independent"),
  ("KitadesuS", "@KitadesuS_MDZ", "UCOv6QnpFZfsVsOfh581sFrA", "Independent"),
  ("Elsenia Volentia", "@ElseniaVolentia", "UCobiRetMOLHDrdLfLQzGiAw", "Independent")
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

def parse_count(text):
    if not text:
        return 0
    text = text.replace(',', '').strip()
    m = re.search(r'([0-9\.]+)\s*([KMBkmb]?)\s*(?:subscribers?|videos?|views?)?', text)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2).upper()
    if unit == 'K':
        return int(val * 1000)
    elif unit == 'M':
        return int(val * 1000000)
    elif unit == 'B':
        return int(val * 1000000000)
    return int(val)

results = []
for name, handle, cid, agency in cids:
    url = f"https://www.youtube.com/channel/{cid}"
    html = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=12).read().decode('utf-8')

    # Subscribers
    m_sub = re.search(r'subscriberCountText.*?simpleText":"([^"]+)"', html)
    if not m_sub:
        m_sub = re.search(r'label":"([0-9\.,KMBkmb]+\s+subscribers?)"', html)
    sub_str = m_sub.group(1) if m_sub else ""
    subs = parse_count(sub_str)

    # Videos
    m_vid = re.search(r'videoCountText.*?simpleText":"([^"]+)"', html)
    vid_str = m_vid.group(1) if m_vid else ""
    vids = parse_count(vid_str)

    # View count from about or metadata if present
    m_view = re.search(r'viewCountText.*?simpleText":"([^"]+)"', html)
    view_str = m_view.group(1) if m_view else ""
    views = parse_count(view_str)

    results.append({
        "name": name,
        "handle": handle,
        "channel_id": cid,
        "agency": agency,
        "subscribers": subs,
        "videos": vids,
        "views": views,
        "sub_str": sub_str,
        "vid_str": vid_str
    })
    print(f"{name} ({handle}): {subs} subs ({sub_str}), {vids} videos ({vid_str}), {views} views")

with open("scripts/new_7_vtubers.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
