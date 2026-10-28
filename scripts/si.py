#!/usr/bin/env python3
"""Local, dependency-free SI retrieval, ingestion and deterministic checks. No network calls."""
import argparse, concurrent.futures, datetime as dt, hashlib, json, math, re, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'), parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Non-finite JSON number: '+v)))
def dump(p, obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    fd,tmp=tempfile.mkstemp(prefix='.'+p.name,dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(payload)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def norm(s): return re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', s.casefold())
def validate(x,s,path='$'):
    errors=[]; typ=s.get('type'); types={'object':dict,'array':list,'string':str,'integer':int,'number':(int,float),'boolean':bool,'null':type(None)}
    if typ and (not isinstance(x,types[typ]) or typ in ('integer','number') and isinstance(x,bool)):
        return [f'{path}: expected {typ}']
    if 'enum' in s and x not in s['enum']: errors.append(f'{path}: invalid enum value')
    if isinstance(x,dict):
        for k in s.get('required',[]):
            if k not in x: errors.append(f'{path}.{k}: required')
        for k,v in x.items():
            if k in s.get('properties',{}): errors+=validate(v,s['properties'][k],path+'.'+k)
            elif s.get('additionalProperties') is False: errors.append(f'{path}.{k}: unknown field')
    if isinstance(x,list):
        if s.get('uniqueItems') and len({json.dumps(v,sort_keys=True) for v in x})!=len(x): errors.append(f'{path}: duplicate items')
        if len(x)<s.get('minItems',0): errors.append(f'{path}: too few items')
        for i,v in enumerate(x): errors+=validate(v,s.get('items',{}),f'{path}[{i}]')
    if isinstance(x,str):
        if len(x.strip())<s.get('minLength',0): errors.append(f'{path}: blank or too short')
        if 'pattern' in s and not re.search(s['pattern'],x): errors.append(f'{path}: invalid format')
    if isinstance(x,(int,float)) and not isinstance(x,bool):
        if not math.isfinite(x): errors.append(f'{path}: non-finite number')
        if x<s.get('minimum',-math.inf) or x>s.get('maximum',math.inf): errors.append(f'{path}: outside bounds')
    return errors

def schema(name): return read(ROOT/'schemas'/f'{name}.schema.json')
def safe(root,rel):
    p=(root/rel).resolve()
    if root.resolve() not in p.parents: raise ValueError('Path must remain inside bank')
    return p

def route(req):
    if not isinstance(req,dict): return 'draft'
    if req.get('mode') in ('draft','revise','derive'): return req['mode']
    if req.get('editor_feedback'): return 'revise'
    if req.get('deliverables'): return 'derive'
    return 'draft'

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def draft_stage(req):
    if not isinstance(req,dict) or route(req)!='draft': return 'write'
    explicit=req.get('draft_stage','auto')
    if explicit in ('discover','write'): return explicit
    return 'write' if any(req.get(k) for k in ('si_title_draft','research_topic','core_scientific_gaps')) or req.get('source_proposal') else 'discover'

def request_schema(req):
    return schema('discovery-input' if draft_stage(req)=='discover' else 'input')

def prepare_discovery(bank,req,today):
    errors=input_errors(req)
    if errors: return {'mode':route(req),'draft_stage':'discover','status':'blocked','missing_inputs':errors}
    # Both independent banks are inspected; journal absence is a research task, not a discovery blocker.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(style_candidates,bank,req); b=pool.submit(standards,bank,req,today)
        profiles=a.result(); standard=b.result()
    return {'mode':'draft','draft_stage':'discover','status':'research_required','request_digest':digest(req),
        'journal_standard':standard,'private_profiles':profiles,
        'research_plan':['Resolve exact journal identity and official scope','Verify SI instructions and archive active/forthcoming/past official calls','Investigate recent primary research and unanswered questions','Compare candidate problems, methods and applications to nearest historical SIs','Return evidence-backed candidates for user selection'],
        'lookback_years':req.get('discovery_preferences',{}).get('lookback_years',5),
        'note':'Host must browse or obtain dated source snapshots. Profiles describe prior examples, not confirmed expertise or topic rankings. No proposal is generated; research evidence stays in task work files.'}

def check_discovery(req,out,today):
    errors=input_errors(req)+validate(out,schema('discovery-output'))
    if errors: return {'status':'fail','errors':errors}
    if today is None: return {'status':'fail','errors':['Current date required']}
    if out['request_digest']!=digest(req): errors.append('Discovery request changed')
    if out['language']!=req.get('language','en'): errors.append('Output language mismatch')
    sources={x['id']:x for x in out['sources']}
    if len(sources)!=len(out['sources']): errors.append('Duplicate source IDs')
    for row in out['sources']+out['search_log']:
        if not row['url'].startswith(('https://','http://')): errors.append('Source/search URL required')
        try:
            if dt.date.fromisoformat(row['checked_on'])>today: errors.append('Future research date')
        except ValueError: errors.append('Invalid research date')
    scope_ids=out['journal_identity']['scope_source_ids']
    if any(i not in sources or sources[i]['kind']!='official_scope' for i in scope_ids): errors.append('Journal identity needs official scope evidence')
    issues={x['id']:x for x in out['historical_issues']}
    if len(issues)!=len(out['historical_issues']): errors.append('Duplicate historical issue IDs')
    for issue in issues.values():
        if any(i not in sources or sources[i]['kind']!='official_si' for i in issue['source_ids']): errors.append('Historical SI needs official source')
    ids=[x['id'] for x in out['candidates']]
    if len(ids)!=len(set(ids)): errors.append('Duplicate candidate IDs')
    for c in out['candidates']:
        if any(i not in sources or sources[i]['kind']!='primary_research' for i in c['research_source_ids']): errors.append('Candidate needs primary research evidence')
        compared=[x['issue_id'] for x in c['comparisons']]
        if any(i not in issues for i in compared) or len(compared)!=len(set(compared)): errors.append('Invalid comparator IDs')
        if issues and not compared: errors.append('Candidate missing nearest historical SI comparison')
        if not issues and (not out['coverage']['no_match_explanation'].strip() or c['overlap_risk']!='unknown'): errors.append('No historical match requires unknown overlap risk and coverage explanation')
    if out['status']=='awaiting_topic_selection':
        if not scope_ids or not all(out['journal_identity'][k].strip() for k in ('full_name','abbr')): errors.append('Resolve journal identity and scope before topic selection')
        if req['journal'].get('abbr') and norm(req['journal']['abbr'])!=norm(out['journal_identity']['abbr']): errors.append('Discovery journal abbreviation mismatch; normalize aliases before research')
        categories={x['category'] for x in out['search_log']}
        if not {'scope','guidelines','active_si','forthcoming_si','past_si','research'}<=categories: errors.append('Research search coverage incomplete')
        count=len(out['candidates']); desired=req.get('discovery_preferences',{}).get('candidate_count',3)
        if not 1<=count<=5 or count<desired and not out['coverage']['fewer_candidates_reason'].strip(): errors.append('Need requested candidate count or evidence-based shortage explanation')
        if out['coverage']['lookback_years']!=req.get('discovery_preferences',{}).get('lookback_years',5): errors.append('Research lookback mismatch')
    return {'status':'fail' if errors else 'mechanical_checks_pass','errors':errors,'limitation':'Host must verify journal identity, source truth, nearest-neighbor selection and coverage. No absolute non-overlap certification.'}

def input_errors(req):
    e=validate(req,request_schema(req))
    if e: return e  # Never traverse malformed values after validation failure.
    mode=route(req)
    if req.get('draft_stage')=='discover' and mode!='draft': e.append('Discovery belongs only to Draft mode')
    if draft_stage(req)=='discover':
        if not any(req['journal'].get(k,'').strip() for k in ('full_name','abbr')): e.append('Exact target journal name or abbreviation required')
        if any(norm(req['journal'].get(k,'')) in ('iet','ieee','unknown','tbd') for k in ('full_name','abbr')): e.append('Publisher alone is ambiguous; provide exact journal')
        if req.get('editor_feedback'): e.append('Editor feedback conflicts with discovery')
        return e
    def unknowns(v,path='$'):
        if isinstance(v,str) and v.strip().casefold() in ('unknown','tbd','to be confirmed','待确认','未知'):
            e.append(path+': unresolved input')
        elif isinstance(v,dict):
            for k,x in v.items(): unknowns(x,path+'.'+k)
        elif isinstance(v,list):
            for i,x in enumerate(v): unknowns(x,f'{path}[{i}]')
    unknowns(req)
    if mode in ('revise','derive') and not req.get('source_proposal','').strip(): e.append('$.source_proposal: required for revise/derive')
    if mode=='revise' and not req.get('editor_feedback'): e.append('$.editor_feedback: required for revise')
    if mode=='derive' and not req.get('deliverables') and not req.get('include_cfp'): e.append('$.deliverables: choose derivative materials')
    if req.get('editor_feedback') and mode!='revise': e.append('Editor feedback conflicts with explicit mode; select revise to resolve feedback first')
    ids=[x['id'] for x in req.get('editor_feedback',[])]
    if len(ids)!=len(set(ids)): e.append('Duplicate editor feedback IDs')
    milestones=req['intended_timeline']['milestones']; dates={}
    labels=[x['label'] for x in milestones]
    if len(labels)!=len(set(labels)): e.append('Duplicate milestone labels')
    for i,m in enumerate(milestones):
        if bool(m.get('date'))==bool(m.get('window')): e.append(f'Milestone {i}: supply exactly one date or tentative window')
        if m.get('window') and req['intended_timeline']['status']=='confirmed': e.append('Confirmed schedule needs exact dates')
        if m.get('date'):
            try: dates[m['label']]=dt.date.fromisoformat(m['date'])
            except ValueError: e.append(f'Milestone {i}: real ISO date required')
        if m.get('after') and m['after'] not in labels: e.append('Unknown milestone dependency: '+m['after'])
    for m in milestones:
        if m.get('after') in dates and m['label'] in dates and dates[m['label']]<dates[m['after']]: e.append('Milestone precedes dependency: '+m['label'])
    for url in [req['journal']['url_scope']]+([req['submission_url']] if req.get('submission_url') else []):
        if not url.startswith(('https://','http://')): e.append('Expected official web URL')
    return e

def requested_artifacts(req,std=None):
    kinds=set(req.get('deliverables',[]))
    if route(req) in ('draft','revise'): kinds.add('proposal')
    if route(req)=='revise': kinds.add('editor_response')
    if req.get('include_cfp'): kinds.add('cfp')
    if 'proposal' in kinds: kinds.update((std or {}).get('required_artifacts',[]))
    return kinds

def journal_errors(rec,today=None):
    e=validate(rec,schema('journal'))
    if e: return e
    sources={x['id']:x for x in rec['sources']}
    if len(sources)!=len(rec['sources']): e.append('Duplicate source IDs')
    rules={x['id']:x for x in rec['rules']}
    if len(rules)!=len(rec['rules']): e.append('Duplicate rule IDs')
    for source in rec['sources']:
        if not source['url'].startswith(('https://','http://')) and source['kind']!='editor_instruction': e.append('Official source URL missing')
        try:
            date=dt.date.fromisoformat(source['retrieved_on'])
            if today and date>today: e.append('Future source retrieval date')
        except ValueError: e.append('Invalid source retrieval date')
    if not any(x['kind']=='official_guideline' for x in sources.values()): e.append('Official proposal guideline source missing')
    for kind,fmt in rec['formats'].items():
        if not set(fmt['required_sections'])<=set(fmt['section_order']): e.append('Mandatory section absent from section_order')
        for sid in fmt['source_ids']:
            if sid not in sources: e.append('Unknown format source ID')
        if kind=='proposal' and not any(sources.get(i,{}).get('kind') in ('official_guideline','editor_instruction') for i in fmt['source_ids']): e.append('Proposal format lacks authoritative guideline source')
        for limit in fmt['limits']:
            if limit['source_id'] not in sources: e.append('Unknown limit source ID')
            if limit['min']>limit['max']: e.append('Inverted numeric limit')
            if limit['target']!='*' and limit['target'] not in fmt['section_order']: e.append('Unknown limit target')
    for rule in rec['rules']:
        if rule['source_id'] not in sources: e.append('Unknown rule source ID')
        if rule.get('required_section'):
            kinds=rec['formats'] if rule['artifact']=='all' else [rule['artifact']]
            for k in kinds:
                if rule['required_section'] not in rec['formats'][k]['section_order']: e.append('Rule-defined mandatory section missing from format order')
        if rule.get('overrides'):
            if sources.get(rule['source_id'],{}).get('kind')!='editor_instruction': e.append('Override requires explicit editor_instruction source')
            for old in rule['overrides']:
                if old not in rules or old==rule['id']: e.append('Invalid override reference')
                elif rules[old].get('overrides'): e.append('Chained/cyclic overrides must be explicitly consolidated')
    for ex in rec['official_cfp_examples']:
        if sources.get(ex['source_id'],{}).get('kind')!='official_cfp': e.append('Public CfP must reference official_cfp source')
    try:
        checked=dt.date.fromisoformat(rec['verified_on']); until=dt.date.fromisoformat(rec['review_after'])
        if checked>until or (today and not checked<=today<=until): e.append('Official record stale or dates inconsistent')
    except ValueError: e.append('Invalid verification dates')
    return e

def active_rules(std):
    superseded={old for r in std.get('rules',[]) for old in r.get('overrides',[])}
    return [r for r in std.get('rules',[]) if r['id'] not in superseded]

def path_values(value,path):
    if not path: return [value]
    key,*rest=path.split('.')
    if key=='*' and isinstance(value,list): return [v for item in value for v in path_values(item,'.'.join(rest))]
    if isinstance(value,dict) and key in value: return path_values(value[key],'.'.join(rest))
    return []

CONCEPTS={
 'agent':['智能体','agentic','agents','autonomous'], 'healthcare':['医疗','健康','health','biomedical'],
 'federated':['联邦','fssl','federation'], 'semi-supervised':['半监督'], 'edge':['边缘','端侧'],
 'trustworthy':['可信','trustworthiness'], 'security':['安全','cybersecurity'], 'privacy':['隐私'],
 'memory':['记忆','persistent'], 'planning':['规划','plan'], 'long-horizon':['长程','长时程'],
 'visual':['视觉','graphics','rendering'], 'world':['世界','4d','scene'],
 'molecular':['分子','biological','bio-nano'], 'mathematical':['数学','numerical','optimization'],
 'scientific':['科学计算','实验仪器','instrument','measurement'], 'feedback':['闭环','closed-loop'],
 'social':['社会','society'], 'explainability':['可解释','explainable'], 'iot':['物联网']}
def tokens(s):
    s=s.casefold(); words=set(re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*|[\u4e00-\u9fff]+',s))
    for concept,aliases in CONCEPTS.items():
        if concept in s or any(a in s for a in aliases): words.add(concept)
    return words

def style_candidates(bank,req):
    idx=read(bank/'index.json'); query=' '.join(str(req.get(k,'')) for k in ('si_title_draft','research_topic','core_scientific_gaps','keywords'))
    q=tokens(query); result=[]
    for entry in idx['private_style_bank']:
        path=safe(bank,entry['record']); rec=read(path)
        if not rec.get('retrieval',{}).get('proposal_eligible',True): continue
        doc=tokens(rec['title']+' '+' '.join(rec.get('keywords',[])))
        score=len(q&doc)/math.sqrt(max(1,len(q)*len(doc)))
        result.append({'sample_id':rec['sample_id'],'sample_type':rec['sample_type'],'title':rec['title'],
          'keywords':rec.get('keywords',[]),'lexical_concept_score':round(score,6),
          'proposal_paradigm':safe(path.parent,rec['proposal_paradigm_file']).read_text(),
          'quality_flags':rec.get('quality_flags',[]),
          'cfp_paradigm':safe(path.parent,rec['cfp_paradigm_file']).read_text() if rec['sample_type']=='A' and rec.get('retrieval',{}).get('cfp_style_eligible') else None,
          'cfp_style_eligible':rec['sample_type']=='A' and rec.get('retrieval',{}).get('cfp_style_eligible',False)})
    return sorted(result,key=lambda x:(-x['lexical_concept_score'],x['sample_id']))

def standards(bank,req,today):
    j=req.get('journal',{}); targets=[norm(j.get('abbr','')),norm(j.get('full_name',''))]; targets=[x for x in targets if x]
    found=[]
    for entry in read(bank/'index.json')['journal_standards_bank']:
        rec=read(safe(bank,entry['record']))
        errors=journal_errors(rec,today)
        if validate(rec,schema('journal')): return {'status':'blocked','errors':errors}
        names=[rec['journal']['abbr'],rec['journal']['full_name']]+rec['journal'].get('aliases',[])
        if any(t in [norm(n) for n in names] for t in targets): found.append(rec)
    if len(found)!=1: return {'status':'missing' if not found else 'ambiguous','records':found,'questions':['Provide exact journal SI proposal guidelines and official public CfP sources.']}
    rec=found[0]; e=journal_errors(rec,today)
    names=[norm(n) for n in [rec['journal']['abbr'],rec['journal']['full_name']]+rec['journal'].get('aliases',[])]
    if any(t not in names for t in targets): e.append('Journal abbreviation/full name mismatch')
    if rec['status']!='verified' or rec['unresolved_conflicts']: e.append('Rules unverified or conflicting')
    for path in rec.get('required_input_paths',[]):
        values=path_values(req,path)
        if not values or any(v is None or v=='' or v==[] for v in values): e.append('Journal-required input missing: '+path)
    return {'status':'blocked' if e else 'ready','record':rec,'errors':e}

def prepare(bank,req,today):
    if draft_stage(req)=='discover': return prepare_discovery(bank,req,today)
    e=input_errors(req)
    if validate(req,schema('input')):
        return {'mode':route(req),'status':'blocked','missing_inputs':e,'journal_standard':{'status':'not_checked'},'style_candidates':[],'candidate_digest':digest([])}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(style_candidates,bank,req); b=pool.submit(standards,bank,req,today)
        styles=a.result(); std=b.result()
    return {'mode':route(req),'status':'blocked' if e or std['status']!='ready' else 'awaiting_semantic_ranking',
      'missing_inputs':e,'journal_standard':std,'style_candidates':styles,'candidate_digest':digest(styles),
      'ranking_instruction':'Score all Proposal candidates and separately all eligible Type A CfP candidates; copy candidate_digest. Scores are retrieval relevance only, never proposal grades.'}

def compile_context(bank,req,ranks,today):
    if draft_stage(req)=='discover': return prepare_discovery(bank,req,today)
    prep=prepare(bank,req,today)
    if validate(req,schema('input')): return {'status':'blocked','mode':route(req),'missing_inputs':prep['missing_inputs'],'slots':{}}
    candidates=prep['style_candidates']; e=validate(ranks,schema('rankings'))
    if e: raise ValueError('; '.join(e))
    if ranks['candidate_digest']!=prep['candidate_digest']: raise ValueError('Stale candidate rankings')
    ids={x['sample_id'] for x in candidates}; supplied=[x.get('sample_id') for x in ranks.get('rankings',[])]
    if set(supplied)!=ids or len(supplied)!=len(ids): e.append('Rank each candidate once; no unknown/duplicate/missing sample IDs')
    if e: raise ValueError('; '.join(e))
    wants='cfp' in requested_artifacts(req,prep.get('journal_standard',{}).get('record',{}))
    cfp_ids={x['sample_id'] for x in candidates if x['cfp_style_eligible']}
    cfp_rows=ranks.get('cfp_rankings',[])
    if wants and (set(r['sample_id'] for r in cfp_rows)!=cfp_ids or len(cfp_rows)!=len(cfp_ids)): raise ValueError('Separately rank all and only eligible Type A CfP examples')
    ordered=sorted(ranks['rankings'],key=lambda x:(-x['semantic_score'],x['sample_id']))
    selected=ordered[:2]; byid={x['sample_id']:x for x in candidates}; idx=read(bank/'index.json')
    entries={x['sample_id']:x for x in idx['private_style_bank']}; examples=[]
    def example(row,role):
        p=safe(bank,entries[row['sample_id']]['record']); rec=read(p)
        value={'sample_id':rec['sample_id'],'sample_type':rec['sample_type'],'role':role,'score':row['semantic_score'],'reason':row['reason'],
          'proposal_paradigm':safe(p.parent,rec['proposal_paradigm_file']).read_text(),'quality_flags':rec.get('quality_flags',[])}
        if role=='cfp_style':
            if rec['sample_type']!='A': raise ValueError('Type B cannot supply CfP style')
            value['cfp_paradigm']=safe(p.parent,rec['cfp_paradigm_file']).read_text()
        value['raw_excerpts_injected']=False  # Curated paradigms only; raw claims remain provenance, not exemplars.
        return value
    for row in selected: examples.append(example(row,'proposal_style_and_content'))
    if wants:
        for row in sorted(cfp_rows,key=lambda r:(-r['semantic_score'],r['sample_id']))[:2]: examples.append(example(row,'cfp_style'))
    blocked=prep['status']=='blocked'
    return {'status':'blocked' if blocked else 'ready_for_draft','mode':prep['mode'],'missing_inputs':prep['missing_inputs'],
      'binding':{'request_digest':digest(req),'standard_digest':digest(prep['journal_standard'].get('record',{})),'compiled_on':today.isoformat(),'candidate_digest':prep['candidate_digest']},
      'requested_artifacts':sorted(requested_artifacts(req,prep['journal_standard'].get('record',{}))),
      'style_top2':[x['sample_id'] for x in selected], 'style_warning':'No private examples' if not selected else 'Only one private example' if len(selected)==1 else '', 'low_style_fit':any(x['semantic_score']<40 for x in selected),
      'slots':{'FEW_SHOT_STYLE_EXAMPLES':examples,'JOURNAL_STANDARD_TEMPLATE':prep['journal_standard']},
      'remaining_host_gates':['official source refresh if needed','recent same-journal SI overlap audit','scope breadth assessment','factual evidence verification','semantic journal-rule check']}

def check_output(req,ctx,out,today=None,bank=None):
    if draft_stage(req)=='discover': return check_discovery(req,out,today)
    e=input_errors(req)+validate(out,schema('output')); notes=[]
    if validate(out,schema('output')) or not isinstance(ctx,dict):
        return {'status':'fail','errors':e or ['Malformed context'],'manual_checks':[]}
    if e: return {'status':'fail','errors':e,'manual_checks':[]}
    if today is None: e.append('Current user-local date required for output validation')
    ready=out['status']=='ready'
    std=ctx.get('slots',{}).get('JOURNAL_STANDARD_TEMPLATE',{}).get('record',{})
    if out['status']=='blocked':
        if out['artifacts'] or not out['unresolved_questions']: e.append('Blocked output must contain questions and no completed artifacts')
        return {'status':'fail' if e else 'blocked_response_valid','errors':e,'manual_checks':[]}
    if ctx.get('status')!='ready_for_draft': e.append('Generation blocked by context')
    binding=ctx.get('binding',{})
    if binding.get('request_digest')!=digest(req): e.append('Request changed since context compilation')
    if binding.get('standard_digest')!=digest(std): e.append('Standard context integrity mismatch')
    e+=journal_errors(std,today)
    if e: return {'status':'fail','errors':e,'manual_checks':[]}
    if bank is not None:
        live=standards(bank,req,today)
        if live['status']!='ready' or digest(live.get('record',{}))!=binding['standard_digest']: e.append('Active journal bank changed or blocked; recompile')
    elif ready: e.append('Ready validation requires current bank recheck')
    if out['mode']!=route(req): e.append('Output mode mismatch')
    if out['language']!=req.get('language','en'): e.append('Output language mismatch')
    expected=requested_artifacts(req,std); produced=[x['kind'] for x in out['artifacts']]
    if not expected<=set(produced): e.append('Requested artifacts missing')
    if len(produced)!=len(set(produced)): e.append('Duplicate artifact kinds')
    if set(produced)-expected: e.append('Unrequested artifacts; resolve scope before generation')
    evidence={x['id']:x for x in out['evidence_ledger']}
    if len(evidence)!=len(out['evidence_ledger']): e.append('Duplicate evidence IDs')
    source_ids={x['id'] for x in std['sources']}
    rules=active_rules(std)
    def attestation(rows,ident,art):
        found=[r for r in rows if r['id']==ident and r['artifact']==art['kind']]
        if len(found)!=1: return False
        r=found[0]
        return r['status']=='pass' and bool(r['evidence'].strip()) and r['artifact_digest']==digest(art) and bool(r['source_ids']) and set(r['source_ids'])<=source_ids
    for art in out['artifacts']:
        sections=art['sections']; ids=[x['id'] for x in sections]; fmt=std['formats'].get(art['kind'])
        if len(ids)!=len(set(ids)): e.append('Duplicate section IDs')
        if any(not x['text'].strip() for x in sections): e.append('Blank section text')
        if fmt:
            order=fmt['section_order']; required=set(fmt['required_sections'])
            required.update(r['required_section'] for r in rules if r['strength']=='mandatory' and r['artifact'] in (art['kind'],'all') and r.get('required_section'))
            if not required<=set(ids): e.append(art['kind']+': missing official sections')
            if fmt['strict_sections'] and set(ids)-set(order): e.append(art['kind']+': unauthorized section')
            positions=[order.index(i) for i in ids if i in order]
            if positions!=sorted(positions): e.append(art['kind']+': wrong official section order')
            for n,limit in enumerate(fmt['limits']):
                ident=f"limit:{art['kind']}:{n}"
                method=limit.get('counting_method','manual')
                selected=sections if limit['target']=='*' else [x for x in sections if x['id']==limit['target']]
                if not selected: e.append('Limit target missing: '+limit['target']); continue
                if method=='manual' or limit['unit'] in ('pages','custom') or (out['language']=='zh' and limit['unit']=='words'):
                    notes.append(ident+': journal-specific counting/render evidence required')
                    if ready and not attestation(out.get('manual_checks',[]),ident,art): e.append('Unresolved manual limit: '+ident)
                    continue
                if (method=='characters')!=(limit['unit']=='characters'): e.append('Counting method/unit mismatch'); continue
                text='\n'.join(x['text'] for x in selected)
                if limit.get('include_title'): text=art['title']+'\n'+text
                if limit.get('include_headings'): text+='\n'+'\n'.join(x['heading'] for x in selected)
                count=len(text) if method=='characters' else len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",text))
                counts=art if limit['target']=='*' else selected[0]
                for item in ('figure','table'):
                    equivalent=limit.get(item+'_equivalent',0)
                    if equivalent and item+'_count' not in counts: e.append('Missing '+item+' count for '+ident)
                    count+=equivalent*counts.get(item+'_count',0)
                if not limit['min']<=count<=limit['max']: e.append(f'{ident}: count {count} outside official limits')
            if ready and not attestation(out.get('rule_checks',[]),'format:'+art['kind'],art): e.append('Format/terminology evidence missing: '+art['kind'])
        for rule in rules:
            if rule['strength']=='mandatory' and rule['artifact'] in (art['kind'],'all'):
                if ready and not attestation(out.get('rule_checks',[]),rule['id'],art): e.append('Mandatory rule not evidenced: '+rule['id'])
    if route(req)=='revise':
        wanted=[x['id'] for x in req['editor_feedback']]; trace=out['revision_trace']; got=[x['issue_id'] for x in trace]
        if set(wanted)!=set(got) or len(got)!=len(set(got)): e.append('Revision trace must cover every feedback ID exactly once')
        proposal_text='\n'.join(s['text'] for a in out['artifacts'] if a['kind']=='proposal' for s in a['sections'])
        for fix in trace:
            if not set(fix['evidence_ids'])<=set(evidence): e.append('Unknown revision evidence ID')
            if fix['disposition']=='clarification_needed' and ready: e.append('Unresolved editor feedback')
            if fix['disposition']=='applied':
                if not fix['after'].strip() or fix['after'] not in proposal_text: e.append('Applied revision not found in revised Proposal')
                if fix['before'] and fix['before'] not in req['source_proposal']: e.append('Before quote absent from source Proposal')
    # Compare only facts explicitly reported; host must also verify all prose agrees with this manifest.
    canonical=[]
    for art in out['artifacts']:
        facts=art.get('canonical_facts',{})
        if art['kind'] in ('proposal','cfp'):
            if ready and not {'title','guest_editors','milestones'}<=set(facts): e.append('Identity/date manifest missing: '+art['kind'])
            if facts:
                canonical.append(facts)
                if facts['title']!=art['title']: e.append('Title differs from canonical manifest')
                if 'guest_editors' in facts:
                    actual={(x['name'],x['affiliation']) for x in facts['guest_editors']}
                    user={(x['name'],x['affiliation']) for x in req['guest_editors']}
                    if actual!=user: e.append('GE roster differs from current request')
                    for x in facts['guest_editors']:
                        supplied=next((g for g in req['guest_editors'] if g['name']==x['name']),{})
                        if x.get('email') and x['email']!=supplied.get('email'): e.append('GE email unsupported by current request')
                allowed={(m['label'],m.get('date',m.get('window'))) for m in req['intended_timeline']['milestones']}
                if any((m['label'],m['value']) not in allowed for m in facts.get('milestones',[])): e.append('Date unsupported by current request')
    if len(canonical)>1 and len({f['title'] for f in canonical})>1: e.append('Proposal/CfP title mismatch')
    if ready:
        if out['unresolved_questions']: e.append('Unresolved questions prevent ready status')
        if route(req)=='draft' and set(out['title_variants'])!={'conservative','cutting_edge','concise'}: e.append('Draft needs three title options in companion report')
        if out['scope_assessment']['breadth']=='unknown': e.append('Scope breadth unresolved')
        for row in out['overlap_audit']['search_log']:
            try:
                checked=dt.date.fromisoformat(row['checked_on'])
                if today and checked>today: e.append('Future overlap search date')
            except ValueError: e.append('Invalid overlap search date')
            if not row['url'].startswith(('https://','http://')): e.append('Overlap evidence URL missing')
        for gate,status in out['checks'].items():
            na=gate=='pair_consistency' and len(out['artifacts'])==1 and route(req)=='draft'
            if status!='pass' and not (na and status=='not_applicable'): e.append('Evidence gate not passed: '+gate)
            if not out.get('check_evidence',{}).get(gate): e.append('Gate rationale missing: '+gate)
        if not out['overlap_audit']['search_log']: e.append('Overlap search evidence missing')
        if not evidence or not out.get('fact_claims'): e.append('Claim-to-evidence mapping missing')
        for item in evidence.values():
            if item['status']=='unverified': e.append('Unverified evidence in ready output: '+item['id'])
            if item['status']=='verified':
                try:
                    date=dt.date.fromisoformat(item['verified_on'])
                    if today and date>today: e.append('Future evidence date')
                except ValueError: e.append('Invalid evidence verification date')
                if not item.get('verification_method'): e.append('Evidence verification method missing')
        artifacts={a['kind']:a for a in out['artifacts']}
        for claim in out.get('fact_claims',[]):
            valid=claim['evidence_ids'] and set(claim['evidence_ids'])<=set(evidence)
            if not valid: e.append('Missing/unknown claim evidence IDs'); continue
            if claim['kind'] in ('literature','novelty') and any(evidence[i]['status']!='verified' for i in claim['evidence_ids']): e.append('Literature/novelty requires primary-source verification')
            section=next((s for s in artifacts.get(claim['artifact'],{}).get('sections',[]) if s['id']==claim['section_id']),None)
            if not section or claim['claim'] not in section['text']: e.append('Claim anchor absent from artifact')
    return {'status':'fail' if e else 'mechanical_checks_pass','errors':e,'manual_checks':notes,
      'limitation':'Evidence records and hashes establish traceability, not source authenticity or semantic truth; host verification is still required.'}

def ingest(bank,kind,src):
    src=Path(src).resolve()
    if kind=='X':
        rec=read(src/'record.json'); errors=validate(rec,schema('private'))
        if errors: raise ValueError('; '.join(errors))
        if rec['sample_type']=='B' and rec['retrieval'].get('cfp_style_eligible'): errors.append('Type B CfP eligibility forbidden')
        if rec['sample_type']=='A' and not safe(src,rec.get('cfp_paradigm_file') or 'NOT_FOUND').is_file(): errors.append('Type A requires separately parsed CfP')
        if not safe(src,rec['proposal_paradigm_file']).is_file(): errors.append('Proposal paradigm missing')
        for path in src.rglob('*'):
            if path.is_symlink(): errors.append('Symlinks prohibited in sample bundle')
        retr=rec['retrieval']
        if rec['sample_type']=='B' and rec.get('source_content_boundary',{}).get('embedded_cfp_detected') and not retr.get('proposal_text_file'): errors.append('Type B embedded CfP requires filtered retrieval view')
        textfile=retr.get('proposal_text_file','proposal.extracted.json')
        if not safe(src,textfile).is_file(): errors.append('Proposal retrieval text missing')
        if rec['sample_type']=='A' and not safe(src,'cfp.extracted.json').is_file(): errors.append('Type A CfP extraction missing')
        if not (src/'provenance.json').is_file(): errors.append('Source provenance missing')
        else:
            for source in read(src/'provenance.json'):
                if hashlib.sha256(safe(src,source['stored_path']).read_bytes()).hexdigest()!=source['sha256']: errors.append('Source hash mismatch')
        ident=rec['sample_id']; dest=bank/'private-style'/ident
    else:
        rec=read(src); errors=journal_errors(rec)
        if errors: raise ValueError('; '.join(errors))
        ident=rec['journal_id']; dest=bank/'journal-standards'/ident
        valid_ids={s['id'] for s in rec.get('sources',[])}
        for fmt in rec.get('formats',{}).values():
            for sid in fmt.get('source_ids',[]):
                if sid not in valid_ids: errors.append('Unknown format source ID')
            for lim in fmt.get('limits',[]):
                if lim['source_id'] not in valid_ids: errors.append('Unknown limit source ID')
        for rule in rec.get('rules',[]):
            if rule['source_id'] not in valid_ids: errors.append('Unknown rule source ID')
        for ex in rec.get('official_cfp_examples',[]):
            if ex['source_id'] not in valid_ids: errors.append('Unknown CfP source ID')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',ident): errors.append('Unsafe bank ID')
    idx=read(bank/'index.json'); key='private_style_bank' if kind=='X' else 'journal_standards_bank'
    if dest.exists(): errors.append('Record exists; create versioned ID and explicitly retire prior index entry')
    if errors: raise ValueError('; '.join(errors))
    if kind=='X':
        import shutil
        shutil.copytree(src,dest); entry={'sample_id':ident,'sample_type':rec['sample_type'],'record':str((dest/'record.json').relative_to(bank))}
    else:
        dump(dest/'record.json',rec); entry={'journal_id':ident,'record':str((dest/'record.json').relative_to(bank))}
    idx[key].append(entry); dump(bank/'index.json',idx)
    return {'stored':str(dest),'bank':key,'note':'Stored provenance assertion is not independent verification.'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--bank',type=Path,default=ROOT/'banks'); sub=ap.add_subparsers(dest='cmd',required=True)
    for name in ('prepare','compile'):
        a=sub.add_parser(name); a.add_argument('--request',required=True); a.add_argument('--today',required=True); a.add_argument('--out',required=True)
        if name=='compile': a.add_argument('--rankings')
    a=sub.add_parser('check'); a.add_argument('--today',required=True); a.add_argument('--request',required=True); a.add_argument('--context'); a.add_argument('--output',required=True); a.add_argument('--out',required=True)
    a=sub.add_parser('ingest'); a.add_argument('--kind',choices=['X','Y'],required=True); a.add_argument('--source',required=True)
    args=ap.parse_args()
    try:
        if args.cmd=='prepare': result=prepare(args.bank,read(args.request),dt.date.fromisoformat(args.today))
        elif args.cmd=='compile': result=compile_context(args.bank,read(args.request),read(args.rankings) if args.rankings else {},dt.date.fromisoformat(args.today))
        elif args.cmd=='check': result=check_output(read(args.request),read(args.context) if args.context else {},read(args.output),dt.date.fromisoformat(args.today),args.bank)
        else: result=ingest(args.bank,args.kind,args.source)
        if hasattr(args,'out'): dump(args.out,result)
        else: print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError,AttributeError) as exc: ap.exit(2,str(exc)+'\n')
if __name__=='__main__': main()
