import urllib.request
import re

handles = ['noeluc_', 'ChizizFa', 'SukaiVtuber', 'kuroyoruyami', 'crazyghsot', 'KitadesuS_MDZ', 'ElseniaVolentia']
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

for h in handles:
    url = f'https://www.youtube.com/@{h}'
    req = urllib.request.Request(url, headers=headers)
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    m = re.findall(r'"([0-9,]+)\s+videos?"', html, re.IGNORECASE)
    print(f"@{h}: vids = {m}")
