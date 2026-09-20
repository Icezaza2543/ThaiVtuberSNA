import json
import unittest

from registry.tiktok import parse_embed, profile_handle, public_text

def document(user=None, videos=None, error=False):
    user = user or {'id': '1234567890123456789', 'uniqueId': 'test_creator', 'nickname': 'Test',
                    'signature': 'VTuber contact@example.org', 'privateAccount': False, 'code': 200}
    state = {'user': {'id': '999999999999', 'ttwid': 'must-not-export'},
             'source': {'data': {'/embed/@test_creator': {'userInfo': user, 'videoList': videos or [], 'isError': error}}}}
    return '<script id="__FRONTITY_CONNECT_STATE__" type="application/json">' + json.dumps(state) + '</script>'

class TikTokProfileTests(unittest.TestCase):
    def test_donor_acknowledgements_are_not_retained_as_creator_evidence(self):
        self.assertEqual(public_text('Thanks! Top Donate viewer one, viewer two', 200),
                         '[donor acknowledgements omitted]')

    def test_only_matching_public_profile_and_owned_public_videos_are_retained(self):
        video = {'id': '12345', 'authorUniqueId': 'test_creator', 'privateItem': False,
                 'desc': 'Thai VTuber', 'playAddr': 'signed-media-secret', 'playCount': 23}
        other = dict(video, id='54321', authorUniqueId='someone_else')
        private = dict(video, id='98765', privateItem=True)
        result = parse_embed(document(videos=[other, private, video]), 'TEST_CREATOR')
        self.assertEqual(result['platform_id'], '1234567890123456789')
        self.assertEqual([v['id'] for v in result['videos']], ['12345'])
        serialized = json.dumps(result)
        for excluded in ('ttwid', '999999999999', 'playAddr', 'playCount', 'signed-media-secret', 'contact@example.org'):
            self.assertNotIn(excluded, serialized)

    def test_challenge_mismatch_private_and_error_pages_cannot_resolve(self):
        for body, handle in [('<html>Please wait</html>', 'test_creator'),
                             (document(), 'another_creator'), (document(error=True), 'test_creator')]:
            with self.subTest(handle=handle, body=body), self.assertRaises(ValueError):
                parse_embed(body, handle)
        user = {'id':'12345678','uniqueId':'test_creator','privateAccount':True,'code':200}
        with self.assertRaises(ValueError): parse_embed(document(user=user), 'test_creator')

    def test_handle_cannot_substitute_for_numeric_account_id(self):
        user = {'id':'@test_creator','uniqueId':'test_creator','privateAccount':False,'code':200}
        with self.assertRaises(ValueError): parse_embed(document(user=user), 'test_creator')

    def test_profile_url_rejects_other_hosts_credentials_and_video_paths(self):
        self.assertEqual(profile_handle('https://www.tiktok.com/@test_creator?lang=en'), 'test_creator')
        for url in ('https://example.com/@test_creator','http://www.tiktok.com/@test_creator',
                    'https://www.tiktok.com/@test_creator/video/123','https://www.tiktok.com.evil/@test_creator',
                    'https://name:password@www.tiktok.com/@test_creator'):
            with self.subTest(url=url), self.assertRaises(ValueError): profile_handle(url)

if __name__ == '__main__': unittest.main()
