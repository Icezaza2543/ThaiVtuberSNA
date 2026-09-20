"""Read public TikTok creator embeds into dated observations, without login.

This module does not modify the registry or certify persona ownership. The web
user ID namespace is intentionally separate from app-scoped open_id/union_id.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

NAMESPACE = 'web_user_id'
MAX_BYTES = 2_000_000

class EmbedState(HTMLParser):
    def __init__(self):
        super().__init__()
        self.collect = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.collect = dict(attrs).get('id') == '__FRONTITY_CONNECT_STATE__'

    def handle_data(self, data):
        if self.collect:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.collect = False

def profile_handle(url):
    parsed = urlparse(url)
    match = re.fullmatch(r'/@([A-Za-z0-9_.]+)/?', parsed.path)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.hostname not in {'tiktok.com', 'www.tiktok.com'} or not match:
        raise ValueError('Expected an HTTPS TikTok creator profile URL')
    return match[1]

def public_text(value, limit):
    # Creator contact details are unnecessary for persona research.
    text = str(value or '')
    if re.search(r'top\s*donat|รายชื่อผู้(?:โดเนท|บริจาค)', text, re.I):
        return '[donor acknowledgements omitted]'
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[contact omitted]', text)
    return text[:limit]

def parse_embed(body, expected_handle):
    parser = EmbedState()
    parser.feed(body)
    if not parser.parts:
        raise ValueError('Public profile data absent; challenge/error page is not evidence')
    state = json.loads(''.join(parser.parts))
    pages = state.get('source', {}).get('data', {})
    matching = []
    for page in pages.values():
        if not isinstance(page, dict) or not isinstance(page.get('userInfo'), dict):
            continue
        user = page['userInfo']
        if str(user.get('uniqueId', '')).casefold() != expected_handle.casefold():
            continue
        if page.get('isError') or user.get('privateAccount') is not False or user.get('code') != 200:
            raise ValueError('Profile is unavailable or not publicly embeddable')
        identifier = str(user.get('id', ''))
        if not re.fullmatch(r'\d{5,30}', identifier):
            raise ValueError('Missing numeric TikTok web user ID')
        result = {'platform_id': identifier, 'id_namespace': NAMESPACE,
                  'handle': user['uniqueId'], 'name': public_text(user.get('nickname'), 150),
                  'bio': public_text(user.get('signature'), 500), 'public_profile': True,
                  'videos': []}
        for video in page.get('videoList', []):
            if len(result['videos']) >= 3:
                break
            if video.get('privateItem') or str(video.get('authorUniqueId', '')).casefold() != expected_handle.casefold():
                continue
            vid = str(video.get('id', ''))
            if vid.isdigit():
                result['videos'].append({'id': vid,
                    'url': f'https://www.tiktok.com/@{user["uniqueId"]}/video/{vid}',
                    'description': public_text(video.get('desc'), 200)})
        matching.append(result)
    if len(matching) != 1:
        raise ValueError('Expected exactly one matching public profile')
    return matching[0]

def fetch_profile(item):
    handle = profile_handle(item['url'])
    source = f'https://www.tiktok.com/embed/@{handle}?lang=en&embedFrom=webapp_preview'
    result = {'url': item['url'], 'source_url': source, 'sources': item.get('sources', []),
              'observed_at': datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(source, headers={'User-Agent': 'Mozilla/5.0'}), timeout=25) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Response exceeds public profile size limit')
        profile = parse_embed(body.decode('utf-8'), handle)
        result.update(status='resolved', **profile)
        # Hash only the retained public creator fields, not request/session data.
        result['public_profile_sha256'] = hashlib.sha256(json.dumps(profile, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    except HTTPError as error:
        result.update(status='unresolved', reason='http_' + str(error.code))
    except (OSError, ValueError, KeyError, TypeError) as error:
        result.update(status='unresolved', reason=type(error).__name__)
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 9))
    args = parser.parse_args(argv)
    items = json.loads(args.input.read_text(encoding='utf-8-sig'))
    unique = {}
    for item in items:
        key = profile_handle(item['url']).casefold()
        if key in unique:
            raise ValueError('Input contains duplicate TikTok profile handles')
        unique[key] = item
    if args.output.exists():
        raise ValueError('Output already exists; choose a new observation batch')
    counts = {'requested': len(items), 'resolved': 0, 'unresolved': 0}
    with args.output.open('x', encoding='utf-8') as stream, ThreadPoolExecutor(max_workers=args.workers) as pool:
        for index, result in enumerate(pool.map(fetch_profile, items), 1):
            stream.write(json.dumps(result, ensure_ascii=False) + '\n')
            stream.flush()
            counts[result['status']] += 1
            if index % 50 == 0:
                print(json.dumps({'processed': index, **counts}), flush=True)
    print(json.dumps(counts), flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
