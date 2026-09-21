"""Behavioral delivery gates: fixtures are fictional, never domain/TM evidence."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'validate_delivery.py'


@pytest.fixture
def gate():
    assert SCRIPT.exists(), 'Missing executable delivery gate: incomplete evidence can enter shortlist'
    spec = importlib.util.spec_from_file_location('delivery_gate', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sample():
    project = {'rubric_version': 'v3', 'weights': {'first_impression': 25, 'distinctiveness': 20,
        'meaning_fit': 20, 'english_transmission': 15, 'family_extension': 10, 'visual_narrative': 10},
        'threshold': 90, 'routes': {'A': 1, 'B': 1}, 'markets': ['US'],
        'currency': 'USD', 'domain_budget': 10000, 'quote_max_age_hours': 24,
        'screen_max_age_hours': 48, 'required_checks': ['us_trademark', 'public_use'],
        'family_modules': ['Memory','Runtime','Studio','Skills','Workspace','Enterprise']}
    candidate = {'name': 'FixtureName', 'route': 'A', 'generator': 'generator-1',
        'operation': 'blend', 'source_kind': 'coined', 'origin': 'Fictional test construction',
        'first_impression': 'A clear first association recorded before the story.',
        'pronunciation': 'Desk prediction only.', 'fit': 'Fictional fit for gate test.',
        'family': {m: 'FixtureName '+m for m in project['family_modules']},
        'review': {'reviewer': 'root', 'rubric_version': 'v3',
            'scores': {'first_impression': 24, 'distinctiveness': 18, 'meaning_fit': 18, 'english_transmission': 14,
                       'family_extension': 9, 'visual_narrative': 9},
            'reasons': {k: 'Independent fixture rationale.' for k in project['weights']},
            'human_test': 'NOT_DONE', 'legal_clearance': 'NOT_DONE'},
        'primary_domain': 'fixturename.test'}
    checks = [{'name': 'FixtureName', 'kind': kind, 'status': 'PASS_SCREEN',
        'market': 'US', 'checked_at': '2026-09-14T15:00:00+00:00',
        'reviewer': 'root', 'source_url': 'https://example.test/source',
        'observation': 'Synthetic complete fixture, not live evidence.',
        'receipt_files': ['receipt.json'], 'coverage_complete': True}
        for kind in project['required_checks']]
    quote = {'domain': 'fixturename.test', 'status': 'AVAILABLE_REGISTRATION',
        'provider': 'Fixture registrar', 'source_url': 'https://example.test/quote',
        'checked_at': '2026-09-14T15:00:00+00:00', 'currency': 'USD',
        'initial_total': 165.4, 'minimum_years': 2, 'renewal_per_year': 82.7,
        'observation': 'Synthetic exact domain availability and price.',
        'receipt_files': ['quote.txt']}
    return project, candidate, checks, quote


def evaluate(gate, sample, tmp_path):
    (tmp_path/'receipt.json').write_text('{"status":"COMPLETE"}')
    (tmp_path/'quote.txt').write_text('Synthetic fixture receipt')
    p,c,checks,q = sample
    return gate.audit(p,[c],checks,[q],tmp_path,datetime(2026,9,14,16,tzinfo=timezone.utc))


def test_complete_candidate_passes_but_missing_second_route_blocks_overall(gate,sample,tmp_path):
    out=evaluate(gate,sample,tmp_path)
    assert out['candidates'][0]['status']=='QUALIFIED_PRELIMINARY'
    assert out['candidates'][0]['score']==92
    assert out['qualified_counts']=={'A':1,'B':0}
    assert out['complete'] is False


@pytest.mark.parametrize('update',[
    {'status':'NO_REGISTRY_RECORD'}, {'status':'INQUIRY'}, {'initial_total':10000.01},
    {'checked_at':'2026-08-14T15:00:00+00:00'}, {'checked_at':'2030-01-01T00:00:00+00:00'},
    {'currency':'EUR'}, {'minimum_years':None}, {'renewal_per_year':None},
    {'receipt_files':[]}, {'initial_total':float('nan')}, {'domain':'different.test'}])
def test_quote_evidence_not_just_rdap_or_estimate(gate,sample,tmp_path,update):
    sample[3].update(update)
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


@pytest.mark.parametrize('update',[
    {'status':'UNKNOWN'}, {'coverage_complete':False}, {'receipt_files':[]},
    {'checked_at':'2026-09-01T00:00:00+00:00'}, {'market':'EU'}, {'source_url':''}])
def test_missing_or_failed_us_screen_never_passes(gate,sample,tmp_path,update):
    sample[2][0].update(update)
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


def test_conflict_cannot_be_outweighed_by_score(gate,sample,tmp_path):
    sample[2][0]['status']='CONFLICT'
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='REJECTED'


@pytest.mark.parametrize('field,value',[
    ('reviewer','generator-1'), ('rubric_version','legacy'), ('scores',{'first_impression':100}),
    ('reasons',{}), ('human_test','PASSED'), ('legal_clearance','CLEARED')])
def test_unsupported_quality_or_external_claim_is_not_delivered(gate,sample,tmp_path,field,value):
    sample[1]['review'][field]=value
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']!='QUALIFIED_PRELIMINARY'


def test_low_score_is_not_rounded_up_to_quota(gate,sample,tmp_path):
    sample[1]['review']['scores']['first_impression']=20
    out=evaluate(gate,sample,tmp_path)['candidates'][0]
    assert out['score']==88
    assert out['status']=='REJECTED'


def test_same_name_cannot_fill_both_routes(gate,sample,tmp_path):
    evaluate(gate,sample,tmp_path)
    p,c,checks,q=sample
    other=copy.deepcopy(c); other['route']='B'
    out=gate.audit(p,[c,other],checks,[q],tmp_path,datetime(2026,9,14,16,tzinfo=timezone.utc))
    assert out['complete'] is False
    assert all(x['status']!='QUALIFIED_PRELIMINARY' for x in out['candidates'])


def test_missing_artifact_file_invalidates_evidence(gate,sample,tmp_path):
    sample[2][0]['receipt_files']=['missing.json']
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


@pytest.mark.parametrize('update',[
    {'markets': []}, {'required_checks': []}, {'markets':['']},
    {'threshold': float('nan')}, {'threshold': True}, {'threshold': 101},
    {'quote_max_age_hours': float('inf')}, {'screen_max_age_hours': -1},
    {'domain_budget': float('inf')}, {'currency': ''},
    {'markets':['US','US']}, {'required_checks':['public_use','public_use']},
])
def test_invalid_project_cannot_disable_evidence_gates(gate,sample,tmp_path,update):
    sample[0].update(update)
    with pytest.raises(ValueError):
        evaluate(gate,sample,tmp_path)


def test_whitespace_candidate_fields_do_not_pass(gate,sample,tmp_path):
    sample[1]['origin']='   '
    sample[1]['review']['reviewer']='   '
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


@pytest.mark.parametrize('update',[
    {'weights': {'bogus':100}}, {'threshold':80}, {'rubric_version':'unknown'},
    {'required_checks':['bogus']}, {'required_checks':['public_use']},
])
def test_full_preliminary_v3_cannot_be_relabeled_to_bypass_contract(gate,sample,tmp_path,update):
    sample[0].update(update)
    with pytest.raises(ValueError):
        evaluate(gate,sample,tmp_path)


def test_configured_principal_reviewer_must_match(gate,sample,tmp_path):
    sample[0]['reviewer']='principal'
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


def test_generator_cannot_certify_screening_evidence(gate,sample,tmp_path):
    for check in sample[2]: check['reviewer']=sample[1]['generator']
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


def test_padded_generator_identity_cannot_impersonate_independence(gate,sample,tmp_path):
    sample[1]['generator']=' ROOT '
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


@pytest.mark.parametrize('update',[{'reviewer':''},{'routes':{' ':1}}])
def test_malformed_configured_reviewer_and_route_rejected(gate,sample,tmp_path,update):
    sample[0].update(update)
    with pytest.raises(ValueError):
        evaluate(gate,sample,tmp_path)


def test_blank_primary_domain_never_qualifies(gate,sample,tmp_path):
    sample[1]['primary_domain']=''
    sample[3]['domain']=''
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


@pytest.mark.parametrize('invalid',['example','https://example.com','name space.com','-name.com',42])
def test_primary_domain_must_be_a_complete_ascii_domain(gate,sample,tmp_path,invalid):
    sample[1]['primary_domain']=invalid
    sample[3]['domain']=invalid
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


def test_configured_names_first_order_requires_chronological_timestamps(gate,sample,tmp_path):
    sample[0]['require_names_first_timestamps']=True
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'
    sample[1]['first_impression_recorded_at']='2026-09-14T14:00:00+00:00'
    sample[1]['source_reviewed_at']='2026-09-14T15:00:00+00:00'
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='QUALIFIED_PRELIMINARY'
    sample[1]['source_reviewed_at']='2026-09-14T13:00:00+00:00'
    assert evaluate(gate,sample,tmp_path)['candidates'][0]['status']=='PENDING'


def test_cli_two_routes_and_exclusive_output(gate,sample,tmp_path):
    evaluate(gate,sample,tmp_path)
    project,candidate,checks,quote=sample
    other=copy.deepcopy(candidate)
    other.update(name='SecondFixture',route='B',primary_domain='secondfixture.test')
    other_checks=[dict(r,name=other['name']) for r in checks]
    other_quote=dict(quote,domain=other['primary_domain'])
    current=datetime.now(timezone.utc).isoformat()
    for item in checks+other_checks+[quote,other_quote]:
        item['checked_at']=current
    data={'project':project,'candidates':[candidate,other],
          'checks':checks+other_checks,'quotes':[quote,other_quote]}
    command=[sys.executable,str(SCRIPT)]
    for key,value in data.items():
        path=tmp_path/(key+'.json')
        path.write_text(json.dumps(value))
        command.extend(['--'+key,str(path)])
    destination=tmp_path/'validated.json'
    command.extend(['--evidence-root',str(tmp_path),'--output',str(destination)])
    completed=subprocess.run(command,capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
    assert json.loads(completed.stdout)['qualified_counts']=={'A':1,'B':1}
    original=destination.read_bytes()
    repeated=subprocess.run(command,capture_output=True,text=True)
    assert repeated.returncode!=0
    assert destination.read_bytes()==original
