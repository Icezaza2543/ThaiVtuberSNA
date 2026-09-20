import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from registry.analytics import growth, timestamp, validate_inputs, csv_write
from registry.analytics_collect import number

class AnalyticsTests(unittest.TestCase):
    def test_growth_keeps_negative_corrections_and_real_interval(self):
        result=growth([{'date':'2026-08-01','subscribers':100},
                       {'date':'2026-09-01','subscribers':90}],30)
        self.assertEqual(result,{'delta':-10,'percent':-10.0,'from':'2026-08-01','to':'2026-09-01','days':31})

    def test_growth_does_not_invent_baseline_or_zero_percent(self):
        self.assertIsNone(growth([{'date':'2026-01-01','subscribers':10},
                                  {'date':'2026-09-01','subscribers':20}],30))
        result=growth([{'date':'2026-08-02','subscribers':0},
                       {'date':'2026-09-01','subscribers':20}],30)
        self.assertIsNone(result['percent'])
        self.assertEqual(result['delta'],20)
        self.assertIsNone(growth([{'date':'2026-08-02','subscribers':None},
                                  {'date':'2026-09-01','subscribers':20}],30))

    def test_missing_metrics_and_unknown_timestamps_are_not_zero(self):
        for value in [None,'123',True,-1]:self.assertIsNone(number(value))
        self.assertEqual(number(0),0)
        self.assertIsNone(timestamp('2026-09-13'))
        self.assertEqual(timestamp('Sun, 13 Sep 2026 09:00:00 GMT'),'2026-09-13T09:00:00+00:00')

    def test_review_detects_tampering_and_cannot_predate_collection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);data={'followers':123}
            row={'source_url':'https://example.com','status':'ok','data':data,
                 'observed_at':'2026-09-13T10:00:00+00:00',
                 'retained_sha256':hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}
            f=p/'source.jsonl';f.write_text(json.dumps(row)+'\n',encoding='utf-8')
            review={'type':'analytics_snapshot_review','reviewer':'test','reviewed_at':'2026-09-13T11:00:00+00:00',
                    'files':[{'name':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}]}
            self.assertEqual(validate_inputs(p,review),{'source.jsonl'})
            review['reviewed_at']='2026-09-13T09:00:00+00:00'
            with self.assertRaisesRegex(ValueError,'predates'):validate_inputs(p,review)
            review['reviewed_at']='2026-09-13T11:00:00+00:00'
            f.write_text('{}\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'changed'):validate_inputs(p,review)

    def test_spreadsheet_export_escapes_formula_text_and_preserves_null(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'test.csv';csv_write(f,[{'name':'=HYPERLINK("bad")','views':None}],['name','views'])
            import csv
            with f.open(encoding='utf-8') as stream:row=next(csv.DictReader(stream))
            self.assertTrue(row['name'].startswith("'="));self.assertEqual(row['views'],'')

if __name__=='__main__':unittest.main()
