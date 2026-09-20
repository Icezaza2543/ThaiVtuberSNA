import json
import unittest
from unittest.mock import patch

from scripts.collect.collect_youtube_about import fetch, stop


class PublicYouTubeCrosslinkTests(unittest.TestCase):
    def test_only_matching_owner_sections_supply_tiktok_links(self):
        cid = 'UC' + 'a' * 22
        metadata = {'metadata': {'channelMetadataRenderer': {
            'externalId': cid, 'title': 'Public creator',
            'description': 'Thai VTuber https://www.tiktok.com/@actual_owner'}},
            'contents': {'aboutChannelViewModel': {'channelId': cid,
                'links': [{'url': 'https://www.tiktok.com/@owner_alternate'}]},
                'recommended': {'channelMetadataRenderer': None,
                                'url': 'https://www.tiktok.com/@unrelated_person'}},
            'another': {'aboutChannelViewModel': {'channelId': 'UC' + 'b' * 22,
                'description': 'https://www.tiktok.com/@different_owner'}},
            'viewer': {'cookie': 'do-not-retain'}}
        # Recommendations are outside both the owner metadata and owner About view.
        del metadata['contents']['recommended']['channelMetadataRenderer']
        class Response:
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                return ('<script>var ytInitialData = ' + json.dumps(metadata) + ';</script>').encode()
        stop.clear()
        with patch('scripts.collect.collect_youtube_about.urlopen', return_value=Response()):
            result = fetch({'platform_id': cid, 'url': 'https://www.youtube.com/channel/' + cid,
                            'name': 'Public creator', 'retain_description': True})
        self.assertEqual(result['tiktok_urls'], ['https://www.tiktok.com/@actual_owner',
                                               'https://www.tiktok.com/@owner_alternate'])
        self.assertEqual(result['youtube_channel_id'], cid)
        self.assertNotIn('do-not-retain', json.dumps(result))
        metadata['metadata']['channelMetadataRenderer']['externalId'] = 'UC' + 'b' * 22
        with patch('scripts.collect.collect_youtube_about.urlopen', return_value=Response()):
            mismatch = fetch({'platform_id': cid, 'url': 'https://www.youtube.com/channel/' + cid,
                              'name': 'Public creator'})
        self.assertEqual(mismatch['error'], 'ValueError')
        self.assertNotIn('tiktok_urls', mismatch)
