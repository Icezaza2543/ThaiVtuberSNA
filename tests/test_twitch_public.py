import unittest
from registry.twitch_public import parse_user


class TwitchPublicTests(unittest.TestCase):
    def user(self):
        return {'id':'9007199254740993','login':'current_name','displayName':'Synthetic test fixture',
                'description':'Thai VTuber','broadcastSettings':{'language':'TH','title':'Test'},
                'channel':{'socialMedias':[]},'panels':[]}

    def test_stable_id_resolves_rename_but_never_accepts_different_id(self):
        user=self.user()
        with self.assertRaisesRegex(ValueError,'Login mismatch'):
            parse_user(user,'old_name')
        parsed=parse_user(user,'old_name','9007199254740993')
        self.assertEqual(parsed['handle'],'current_name')
        self.assertEqual(parsed['platform_id'],'9007199254740993')
        with self.assertRaisesRegex(ValueError,'User ID mismatch'):
            parse_user(user,'old_name','123')

    def test_missing_public_profile_is_not_an_account(self):
        for value in [None,{},dict(self.user(),id='')]:
            with self.assertRaises(ValueError):parse_user(value,'current_name')

    def test_retains_introduction_but_excludes_acknowledgements(self):
        user=self.user()
        user['panels']=[{'title':'About me','description':'I am a Thai VTuber'},
                        {'title':'Special thanks','description':'Viewer one and Viewer two'},
                        {'title':'Top donors','description':'Viewer three'},
                        {'title':'PC specs','description':'A computer'}]
        parsed=parse_user(user,'current_name')
        self.assertEqual(parsed['panels'],[{'title':'About me','description':'I am a Thai VTuber'}])

if __name__=='__main__':unittest.main()
