#!/usr/bin/env python3
"""Validate preliminary naming delivery, not legal truth or aesthetic quality.

Reads reviewer-authored records and locally retained receipts. A positive result
means required evidence was supplied, not that a trademark is legally available.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path

V3_WEIGHTS = {'first_impression':25, 'distinctiveness':20, 'meaning_fit':20,
              'english_transmission':15, 'family_extension':10, 'visual_narrative':10}


def fresh(value, hours, now):
    try:
        at = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if at.tzinfo is None:
            return False
        return 0 <= (now-at).total_seconds() <= hours*3600
    except (ValueError, TypeError, AttributeError):
        return False


def number(value, lower=0, upper=math.inf):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and lower <= value <= upper)


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def identity(value):
    return value.strip().casefold() if isinstance(value,str) else ''


def domain_name(value):
    if not isinstance(value,str) or not value.isascii() or len(value)>253:
        return False
    labels=value.split('.')
    return len(labels)>=2 and all(
        1<=len(label)<=63 and label[0].isalnum() and label[-1].isalnum()
        and all(ch.isalnum() or ch=='-' for ch in label) for label in labels)


def validate_project(project):
    if not isinstance(project, dict):
        raise ValueError('Project must be an object')
    for key in ('markets', 'required_checks'):
        values=project.get(key)
        if (not isinstance(values,list) or not values or not all(nonblank(v) for v in values)
                or len(set(values))!=len(values)):
            raise ValueError(key+' must be a nonempty list of distinct strings')
    for key in ('currency','rubric_version'):
        if not nonblank(project.get(key)):
            raise ValueError(key+' must be a nonempty string')
    if 'reviewer' in project and not nonblank(project['reviewer']):
        raise ValueError('Configured reviewer must be a nonempty string')
    if project.get('rubric_version')!='v3' or project.get('weights')!=V3_WEIGHTS:
        raise ValueError('This validator supports only the frozen v3 rubric and its exact weights')
    if not number(project.get('threshold'),90,100):
        raise ValueError('v3 preliminary threshold must be finite and within 90..100')
    if set(project['required_checks'])!={'us_trademark','public_use'}:
        raise ValueError('Full preliminary validation requires both trademark and public-use checks')
    for key in ('domain_budget','quote_max_age_hours','screen_max_age_hours'):
        if not number(project.get(key)):
            raise ValueError(key+' must be a finite nonnegative number')


def names_first(c, now):
    try:
        first=datetime.fromisoformat(c['first_impression_recorded_at'].replace('Z','+00:00'))
        later=datetime.fromisoformat(c['source_reviewed_at'].replace('Z','+00:00'))
        return first.tzinfo is not None and later.tzinfo is not None and first<later<=now
    except (ValueError, TypeError, AttributeError, KeyError):
        return False


def evidence_errors(item, root, age, now):
    errors=[]
    for field in ('source_url', 'observation'):
        if not isinstance(item.get(field),str) or not item[field].strip():
            errors.append('missing '+field)
    if not str(item.get('source_url','')).startswith(('https://','http://')):
        errors.append('source URL required')
    if not fresh(item.get('checked_at'),age,now):
        errors.append('stale, future, or invalid evidence timestamp')
    files=item.get('receipt_files')
    if not isinstance(files,list) or not files:
        errors.append('missing receipt files')
    else:
        for path in files:
            if not isinstance(path,str):
                errors.append('invalid receipt path'); continue
            p=(root/path).resolve()
            if not p.is_relative_to(root.resolve()) or not p.is_file() or p.stat().st_size==0:
                errors.append('missing, empty, or out-of-scope receipt: '+path)
    return errors


def audit(project,candidates,checks,quotes,evidence_root,now=None):
    validate_project(project)
    for label, records in (('candidates', candidates),('checks',checks),('quotes',quotes)):
        if not isinstance(records,list) or any(not isinstance(r,dict) for r in records):
            raise ValueError(label+' must be an array of objects')
    now=now or datetime.now(timezone.utc)
    root=Path(evidence_root)
    weights=project['weights']
    if not weights or any(not number(v,0,100) for v in weights.values()) or sum(weights.values())!=100:
        raise ValueError('Project weights must sum to 100')
    routes=project['routes']
    if (not isinstance(routes,dict) or not routes or not all(nonblank(r) for r in routes)
            or any(not isinstance(n,int) or isinstance(n,bool) or n<1 for n in routes.values())):
        raise ValueError('Project route quotas must be positive integers')
    normalized=[str(c.get('name','')).strip().casefold() for c in candidates]
    duplicates={n for n,count in Counter(normalized).items() if count>1}
    result=[]
    counts={route:0 for route in routes}
    operations={route:Counter() for route in routes}
    for c in candidates:
        name=c.get('name',''); route=c.get('route'); reasons=[]; rejected=False
        if not nonblank(name) or name.strip().casefold() in duplicates:
            reasons.append('empty or duplicate candidate name')
        if route not in routes:
            reasons.append('unknown route')
        for field in ('operation','source_kind','origin','first_impression','pronunciation','fit','generator','primary_domain'):
            if not nonblank(c.get(field)): reasons.append('missing '+field)
        if not domain_name(c.get('primary_domain')):
            reasons.append('invalid complete primary domain')
        if project.get('require_names_first_timestamps') and not names_first(c,now):
            reasons.append('names-first review order not evidenced')
        family=c.get('family',{})
        if any(not nonblank(family.get(m)) for m in project.get('family_modules',[])):
            reasons.append('incomplete product-family test')
        review=c.get('review',{})
        if not nonblank(review.get('reviewer')) or identity(review['reviewer'])==identity(c.get('generator')):
            reasons.append('independent reviewer required')
        if project.get('reviewer') and identity(review.get('reviewer'))!=identity(project['reviewer']):
            reasons.append('configured principal reviewer required')
        if review.get('rubric_version')!=project['rubric_version']:
            reasons.append('wrong rubric version')
        scores=review.get('scores',{})
        valid_scores=set(scores)==set(weights) and all(number(scores[k],0,weights[k]) for k in weights)
        score=sum(scores.values()) if valid_scores else None
        if not valid_scores: reasons.append('invalid score breakdown')
        elif score<project['threshold']:
            reasons.append('quality below threshold'); rejected=True
        if any(not nonblank(review.get('reasons',{}).get(k)) for k in weights):
            reasons.append('missing score rationale')
        # This preliminary-only interface intentionally cannot certify human/legal outcomes.
        if review.get('human_test')!='NOT_DONE' or review.get('legal_clearance')!='NOT_DONE':
            reasons.append('human or legal result outside preliminary validator scope')
        for kind in project['required_checks']:
            for market in project['markets']:
                matched=[r for r in checks if r.get('name')==name and r.get('kind')==kind and r.get('market')==market]
                if not matched:
                    reasons.append('missing '+market+' '+kind); continue
                # Require exactly one current review record per gate. Historical receipts live separately.
                if len(matched)!=1:
                    reasons.append('ambiguous review records for '+kind); continue
                r=matched[0]
                if identity(r.get('reviewer'))==identity(c.get('generator')) or (project.get('reviewer') and identity(r.get('reviewer'))!=identity(project['reviewer'])):
                    reasons.append(kind+' requires independent principal review')
                if r.get('status')=='CONFLICT': rejected=True
                if r.get('status')!='PASS_SCREEN' or r.get('coverage_complete') is not True or not nonblank(r.get('reviewer')):
                    reasons.append(kind+' not completed/passed')
                reasons.extend(kind+': '+e for e in evidence_errors(r,root,project['screen_max_age_hours'],now))
        selected=[q for q in quotes if q.get('domain')==c.get('primary_domain')]
        if len(selected)!=1:
            reasons.append('one exact primary-domain quote required')
        else:
            q=selected[0]
            if q.get('status') not in ('AVAILABLE_REGISTRATION','FIXED_PRICE_SALE'):
                reasons.append('domain not demonstrably purchasable')
            if q.get('currency')!=project['currency']:
                reasons.append('unverified currency conversion')
            if not number(q.get('initial_total'),0,project['domain_budget']):
                reasons.append('initial domain cost missing or exceeds budget')
            if not number(q.get('minimum_years'),1) or not number(q.get('renewal_per_year'),0):
                reasons.append('domain term/renewal missing')
            if not nonblank(q.get('provider')): reasons.append('quote provider missing')
            reasons.extend('quote: '+e for e in evidence_errors(q,root,project['quote_max_age_hours'],now))
        status='REJECTED' if rejected else 'PENDING' if reasons else 'QUALIFIED_PRELIMINARY'
        if status=='QUALIFIED_PRELIMINARY':
            counts[route]+=1; operations[route][c['operation']]+=1
        result.append({'name':name,'route':route,'score':score,'status':status,'reasons':reasons})
    return {'checked_at':now.isoformat(),'rubric_version':project['rubric_version'],
            'complete':all(counts[r]>=routes[r] for r in routes),
            'qualified_counts':counts,'targets':routes,'operations':operations,
            'candidates':result,'scope':'Preliminary evidence validation only; no legal or human clearance'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True); p.add_argument('--candidates',required=True)
    p.add_argument('--checks',required=True); p.add_argument('--quotes',required=True)
    p.add_argument('--evidence-root',required=True); p.add_argument('--output')
    a=p.parse_args()
    out=audit(read_json(a.project),read_json(a.candidates),read_json(a.checks),read_json(a.quotes),Path(a.evidence_root))
    content=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        with Path(a.output).open('x',encoding='utf-8') as f: f.write(content)
    print(content)
    return 0 if out['complete'] else 2


if __name__=='__main__':
    raise SystemExit(main())
