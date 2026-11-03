"""Contract tests for semantic grouping and LLM element identity/math protection."""
import json,tempfile,unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'mupdf'))
from pipeline import repair_overlapping_prose
from llm_adapter import translate

class TranslationContracts(unittest.TestCase):
    def test_overlap_merges_prose_but_never_math(self):
        a={'id':'p1.a','page':1,'type':'text','bbox':[10,10,100,30],'source':'a','translation':'甲'}
        b={**a,'id':'p1.b','bbox':[60,20,100,35],'source':'b','translation':'乙'}
        formula={**a,'id':'p1.eq','type':'formula','bbox':[10,15,100,40]}
        result=repair_overlapping_prose([a,b,formula]);self.assertEqual(len(result),2)
        self.assertEqual(result[0]['children'],['p1.a','p1.b']);self.assertEqual(result[1]['type'],'formula')

    def fixture(self):
        return {'pages':[{'number':1,'blocks':[{'id':'p1.b0','text':'scale σ','type':'text','lines':[{'spans':[{'text':'scale ','font':'Times'},{'text':'σ','font':'CMMI10'}]}]}]}]}

    def run_adapter(self,entries):
        body=json.dumps({'choices':[{'message':{'content':json.dumps({'translations':entries})}}]}).encode()
        with tempfile.TemporaryDirectory() as td,patch('urllib.request.urlopen',return_value=BytesIO(body)):
            return translate(self.fixture(),{},'https://example.invalid/no-network','test',Path(td)/'cache.json')

    def test_math_placeholder_round_trip(self):
        result=self.run_adapter([{'id':'p1.b0','translation':'尺度 __MATH_0__'}]);self.assertEqual(result[0]['translation'],'尺度 σ')

    def test_unknown_id_rejected(self):
        with self.assertRaises(ValueError):self.run_adapter([{'id':'p2.fake','translation':'文字'}])

    def test_lost_math_rejected(self):
        with self.assertRaises(ValueError):self.run_adapter([{'id':'p1.b0','translation':'尺度'}])

    def test_duplicate_math_rejected(self):
        with self.assertRaises(ValueError):self.run_adapter([{'id':'p1.b0','translation':'__MATH_0__ __MATH_0__'}])

if __name__=='__main__':unittest.main(verbosity=2)
