"""Live-derived regressions: EVOLIA fuzzy has 424 results, beyond one page."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'us_trademark_screen.py'
spec = importlib.util.spec_from_file_location('us_paged_test', SCRIPT)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


def source(serial):
    return {'id':str(serial),'wordmark':'FIXTURE '+str(serial),'alive':True,
            'registered':True,'registrationId':str(serial),'goodsAndServices':['Software'],
            'ownerName':['Fixture Corporation (CORPORATION; USA)'],
            'ownerFullText':['(APPLICANT) Fixture Corporation (CORPORATION; USA); Fixture address']}


def page(ids,total=3):
    return {'hits':{'totalValue':total,'totalRelation':'eq',
                    'hits':[{'source':source(i)} for i in ids]}}


class Response:
    headers = {}
    def __init__(self,payload,status=200):
        self.payload,self.status_code=payload,status
    def json(self):
        return self.payload


class Session:
    def __init__(self,*responses):
        self.responses=list(responses); self.calls=[]
    def post(self,endpoint,**kwargs):
        self.calls.append(kwargs['json'])
        return self.responses.pop(0)


def test_all_pages_required_and_preserved():
    session=Session(Response(page([1,2])),Response(page([3])))
    with patch.object(screen,'PAGE_SIZE',2):
        result=screen.query_receipt(session,'wordmark:FIXTURE~2')
    assert result['status']=='COMPLETE'
    assert [x['from'] for x in session.calls]==[0,2]
    assert result['returned']==result['total']==3
    assert len(result['records'])==3
    assert len(result['pages'])==2
    assert result['pages'][1]['raw_payload']==page([3])


def test_second_page_access_failure_is_retained_and_not_retried():
    session=Session(Response(page([1,2])),Response({'message':'denied'},403))
    with patch.object(screen,'PAGE_SIZE',2):
        result=screen.query_receipt(session,'wordmark:FIXTURE~2')
    assert result['status']!='COMPLETE'
    assert len(session.calls)==2
    assert result['pages'][1]['HTTP']==403


def test_duplicate_records_across_pages_do_not_prove_completeness():
    session=Session(Response(page([1,2])),Response(page([2])))
    with patch.object(screen,'PAGE_SIZE',2):
        result=screen.query_receipt(session,'wordmark:FIXTURE~2')
    assert result['status']!='COMPLETE'
    assert len(session.calls)==2
    assert 'duplicate' in result['error'].lower()


def test_changing_total_is_not_silently_accepted():
    session=Session(Response(page([1,2])),Response(page([3],total=4)))
    with patch.object(screen,'PAGE_SIZE',2):
        result=screen.query_receipt(session,'wordmark:FIXTURE~2')
    assert result['status']!='COMPLETE'
    assert len(session.calls)==2
    assert len(result['pages'])==2


def test_short_nonfinal_page_does_not_skip_unseen_records():
    session=Session(Response(page([1],total=3)))
    with patch.object(screen,'PAGE_SIZE',2):
        result=screen.query_receipt(session,'wordmark:FIXTURE~2')
    assert result['status']!='COMPLETE'
    assert len(session.calls)==1
