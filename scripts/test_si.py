#!/usr/bin/env python3
"""Behavioral checks with wholly synthetic temporary banks; no personal samples."""
import copy, datetime as dt, json, tempfile, unittest
from pathlib import Path
import si
TODAY=dt.date(2026,10,28)
def request():
 return {'journal':{'full_name':'Example Test Journal','abbr':'TEST','url_scope':'https://example.invalid/scope','special_rules':'none'},'si_title_draft':'Long-horizon agents','research_topic':'Persistent agent memory and planning','core_scientific_gaps':'Recovery and memory consistency over extended tasks','keywords':['agent memory','planning'],'guest_editors':[{'name':'Test person','affiliation':'Test institution','bio':'User supplied test biography','org_experience':'none'}],'intended_timeline':{'milestones':[{'label':'Submission','date':'2027-12-01'}],'status':'tentative'},'source_community':'User supplied test community','expected_submissions':20,'user_constraints':'none'}
def standard():
 fmt={'section_order':['summary','topics'],'required_sections':['summary','topics'],'strict_sections':True,'terminology':{},'limits':[{'target':'summary','unit':'words','min':1,'max':5,'source_id':'g','counting_notes':'Unicode token count','counting_method':'unicode_words'}],'format_notes':'Synthetic test only','source_ids':['g']}
 return {'journal_id':'TEST-v1','journal':{'full_name':'Example Test Journal','abbr':'TEST','aliases':['ETJ']},'status':'verified','verified_on':'2026-10-01','review_after':'2026-12-31','sources':[{'id':'g','url':'https://example.invalid/g','title':'Synthetic guideline','kind':'official_guideline','retrieved_on':'2026-10-01','snapshot_text':'Synthetic test only','authority_note':'Test fixture, not authentic official evidence'},{'id':'c','url':'https://example.invalid/cfp','title':'Synthetic public CfP','kind':'official_cfp','retrieved_on':'2026-10-01','snapshot_text':'Test only','authority_note':'Synthetic test only'}],'formats':{'proposal':fmt,'cfp':copy.deepcopy(fmt)},'rules':[],'official_cfp_examples':[{'source_id':'c','title':'Synthetic CfP','text':'Test only','published_on':'2026','format_features':[]}],'recent_issues':[],'unresolved_conflicts':[]}
def rankings(candidates):
 return {'candidate_digest':si.digest(candidates),'cfp_rankings':[{'sample_id':x['sample_id'],'semantic_score':70,'reason':'CfP-specific test ranking'} for x in candidates if x['cfp_style_eligible']], 'rankings':[{'sample_id':x['sample_id'],'semantic_score':100-i,'reason':'Synthetic controlled ranking for gate tests, not semantic evaluation'} for i,x in enumerate(candidates)]}
def make_synthetic_bank(bank):
 """Artificial fixtures only. No real samples or personal information."""
 index={'version':1,'private_style_bank':[],'journal_standards_bank':[]}
 for i in range(1,11):
  ident=f'SYN-{i:02}'; typ='A' if i<=5 else 'B'; folder=bank/'private-style'/ident
  folder.mkdir(parents=True)
  rec={'sample_id':ident,'sample_type':typ,'title':f'Synthetic test topic {i}','keywords':['test','agent'],
       'proposal_paradigm_file':'proposal.paradigm.md','retrieval':{'proposal_eligible':True,'cfp_style_eligible':typ=='A'},'quality_flags':['Synthetic test only']}
  (folder/'proposal.paradigm.md').write_text('Synthetic pattern: stated gap followed by bounded scope. Not an actual proposal.')
  if typ=='A':
   rec['cfp_paradigm_file']='cfp.paradigm.md'
   (folder/'cfp.paradigm.md').write_text('Synthetic call: short motivation followed by research topics.')
  si.dump(folder/'record.json',rec)
  si.dump(folder/'proposal.style-eligible.json',{'paragraphs':[{'paragraph_id':'kept','text':'Synthetic filtered content'}]})
  index['private_style_bank'].append({'sample_id':ident,'sample_type':typ,'record':f'private-style/{ident}/record.json'})
 si.dump(bank/'index.json',index)

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.bank=Path(self.tmp.name)/'bank'
  make_synthetic_bank(self.bank)
  self.req=request()
 def tearDown(self): self.tmp.cleanup()
 def install_standard(self,obj=None):
  f=Path(self.tmp.name)/'journal.json'; si.dump(f,obj or standard()); return si.ingest(self.bank,'Y',f)
 def context(self):
  self.install_standard(); prep=si.prepare(self.bank,self.req,TODAY); return si.compile_context(self.bank,self.req,rankings(prep['style_candidates']),TODAY)
 def test_whitespace_sections_rejected(self):
  ctx=self.context(); out=self.ready_output(); out['artifacts'][0]['sections'][0]['text']='   '
  self.assertTrue(any('blank' in e.lower() for e in si.check_output(self.req,ctx,out,TODAY,self.bank)['errors']))
 def test_missing_official_does_not_promote_private(self):
  result=si.prepare(self.bank,self.req,TODAY); self.assertEqual(result['status'],'blocked'); self.assertEqual(result['journal_standard']['status'],'missing'); self.assertEqual(len(result['style_candidates']),10)
 def test_mandatory_input_and_types(self):
  del self.req['core_scientific_gaps']; self.req['expected_submissions']=True
  self.assertGreaterEqual(len(si.input_errors(self.req)),2)
 def test_unknown_is_not_none(self):
  self.req['journal']['special_rules']='unknown'; self.assertTrue(si.input_errors(self.req))
 def test_modes_and_sources(self):
  self.req['editor_feedback']=[{'id':'E1','comment':'Narrow scope'}]; self.assertEqual(si.route(self.req),'revise'); self.assertTrue(si.input_errors(self.req))
  self.req['mode']='derive'; self.req['source_proposal']='source'; self.req['deliverables']=['cfp']; self.req['editor_feedback']=[]; self.assertFalse(si.input_errors(self.req))
 def test_stale_and_identity(self):
  obj=standard(); obj['review_after']='2026-10-01'; self.install_standard(obj)
  self.assertEqual(si.standards(self.bank,self.req,TODAY)['status'],'blocked')
  self.req['journal']['full_name']='Wrong Journal'; self.assertIn('mismatch',' '.join(si.standards(self.bank,self.req,TODAY)['errors']))
 def test_type_b_cfp_boundary(self):
  self.install_standard(); self.req['mode']='derive'; self.req['source_proposal']='source'; self.req['deliverables']=['cfp']
  prep=si.prepare(self.bank,self.req,TODAY); ranks=rankings(prep['style_candidates'])
  for r in ranks['rankings']: r['semantic_score']=100 if r['sample_id']=='SYN-10' else 90 if r['sample_id']=='SYN-06' else 50
  ctx=si.compile_context(self.bank,self.req,ranks,TODAY); self.assertEqual(set(ctx['style_top2']),{'SYN-10','SYN-06'})
  for ex in ctx['slots']['FEW_SHOT_STYLE_EXAMPLES']:
   if ex['role']=='cfp_style': self.assertEqual(ex['sample_type'],'A')
   if ex['sample_type']=='B': self.assertNotIn('cfp_paradigm',ex)
 def test_semantic_ranking_must_cover_all(self):
  prep=si.prepare(self.bank,self.req,TODAY); r=rankings(prep['style_candidates']); r['rankings'].pop()
  with self.assertRaises(ValueError): si.compile_context(self.bank,self.req,r,TODAY)
 def test_official_order_and_limits_override_private(self):
  ctx=self.context(); out={'status':'draft','mode':'draft','language':'en','title_variants':{},'artifacts':[{'kind':'proposal','title':'test','sections':[{'id':'topics','heading':'Topics','text':'a'},{'id':'summary','heading':'Summary','text':'one two three four five six'},{'id':'bios','heading':'Bios','text':'not allowed'}]}],'revision_trace':[],'evidence_ledger':[],'overlap_audit':{'lookback_years':3,'search_log':[],'comparisons':[],'assessment':'test'},'scope_assessment':{'breadth':'balanced','reason':'test','adjustments':[]},'checks':{k:'pending' for k in ('facts','scope','overlap','journal_rules','pair_consistency')},'editorial_checklist':[],'unresolved_questions':[]}
  result=si.check_output(self.req,ctx,out,TODAY,self.bank); self.assertTrue(any('order' in e for e in result['errors'])); self.assertTrue(any('count' in e for e in result['errors'])); self.assertTrue(any('unauthorized' in e for e in result['errors']))
  out['artifacts'][0]['sections']=[{'id':'summary','heading':'Summary','text':'four words are here'},{'id':'topics','heading':'Topics','text':'a'}]
  self.assertEqual(si.check_output(self.req,ctx,out,TODAY,self.bank)['status'],'mechanical_checks_pass')
  out['status']='ready'; self.assertEqual(si.check_output(self.req,ctx,out,TODAY,self.bank)['status'],'fail')
 def test_duplicate_official_match(self):
  self.install_standard(); obj=standard(); obj['journal_id']='TEST-v2'; self.install_standard(obj)
  self.assertEqual(si.standards(self.bank,self.req,TODAY)['status'],'ambiguous')
 def test_bad_ingestion_does_not_mutate(self):
  obj=standard(); obj['formats']['proposal']['source_ids']=['missing']; f=Path(self.tmp.name)/'bad.json'; si.dump(f,obj)
  with self.assertRaises(ValueError): si.ingest(self.bank,'Y',f)
  self.assertFalse(si.read(self.bank/'index.json')['journal_standards_bank'])
 def test_wrong_topic_filtered(self):
  p=self.bank/'private-style/SYN-09/proposal.style-eligible.json'; pars=si.read(p)['paragraphs']; self.assertNotIn('excluded_synthetic_paragraph',[x['paragraph_id'] for x in pars])
 def test_revision_trace_missing(self):
  ctx=self.context(); self.req['mode']='revise'; self.req['source_proposal']='text'; self.req['editor_feedback']=[{'id':'E1','comment':'fix'}]
  result=si.check_output(self.req,ctx,{'status':'draft','artifacts':[],'revision_trace':[]}); self.assertEqual(result['status'],'fail')
 def ready_output(self):
  art={'kind':'proposal','title':self.req['si_title_draft'],'sections':[{'id':'summary','heading':'Summary','text':'A supported statement.'},{'id':'topics','heading':'Topics','text':'Evidence-grounded topics.'}],'canonical_facts':{'title':self.req['si_title_draft'],'guest_editors':[{'name':x['name'],'affiliation':x['affiliation']} for x in self.req['guest_editors']],'milestones':[{'label':x['label'],'value':x.get('date',x.get('window'))} for x in self.req['intended_timeline']['milestones']]}}
  return {'status':'ready','mode':si.route(self.req),'language':'en','title_variants':{'conservative':'Test title','cutting_edge':'Test frontier title','concise':'Test'},'artifacts':[art],'revision_trace':[],'evidence_ledger':[{'id':'u1','claim':'A supported statement.','source':'Current user supplied test request','verified_on':'not independently verified','status':'user_supplied'}],'fact_claims':[{'claim':'A supported statement.','artifact':'proposal','section_id':'summary','evidence_ids':['u1'],'kind':'other'}],'overlap_audit':{'lookback_years':3,'search_log':[{'query':'test','url':'https://example.invalid/calls','checked_on':'2026-10-28','result':'Synthetic test evidence'}],'comparisons':[],'assessment':'Fixture only'},'scope_assessment':{'breadth':'balanced','reason':'fixture','adjustments':[]},'checks':{k:'pass' for k in ('facts','scope','overlap','journal_rules','pair_consistency')},'check_evidence':{k:'Synthetic review evidence; not a real proposal' for k in ('facts','scope','overlap','journal_rules','pair_consistency')},'rule_checks':[{'id':'format:proposal','artifact':'proposal','status':'pass','evidence':'Fixture format checked','source_ids':['g'],'artifact_digest':si.digest(art)}],'manual_checks':[],'editorial_checklist':[],'unresolved_questions':[]}
 def check(self,ctx,out): return si.check_output(self.req,ctx,out,TODAY,self.bank)
 def test_positive_ready_with_traceability(self):
  ctx=self.context(); self.assertEqual(self.check(ctx,self.ready_output())['status'],'mechanical_checks_pass')
 def test_malformed_input_returns_block_not_crash(self):
  for key,value in [('journal',None),('intended_timeline',[]),('source_proposal',4),('guest_editors',None)]:
   r=request(); r[key]=value; result=si.prepare(self.bank,r,TODAY); self.assertEqual(result['status'],'blocked')
 def test_required_section_cannot_be_blank(self):
  ctx=self.context(); out=self.ready_output(); out['artifacts'][0]['sections'][0]['text']=' '
  self.assertEqual(self.check(ctx,out)['status'],'fail')
 def test_request_bound_context(self):
  ctx=self.context(); self.req['expected_submissions']=99
  self.assertTrue(any('Request changed' in e for e in self.check(ctx,self.ready_output())['errors']))
 def test_expired_context_rechecked(self):
  ctx=self.context(); result=si.check_output(self.req,ctx,self.ready_output(),dt.date(2027,1,1),self.bank)
  self.assertTrue(any('stale' in e for e in result['errors']))
 def test_live_bank_changed(self):
  ctx=self.context(); path=self.bank/'journal-standards/TEST-v1/record.json'; data=si.read(path); data['formats']['proposal']['format_notes']='Changed'; si.dump(path,data)
  self.assertTrue(any('Active journal' in e for e in self.check(ctx,self.ready_output())['errors']))
 def test_page_limit_requires_current_artifact_proof(self):
  std=standard(); std['formats']['proposal']['limits']=[{'target':'*','unit':'pages','min':1,'max':1,'source_id':'g','counting_notes':'Rendered page'}]; self.install_standard(std)
  prep=si.prepare(self.bank,self.req,TODAY); ctx=si.compile_context(self.bank,self.req,rankings(prep['style_candidates']),TODAY); out=self.ready_output()
  self.assertTrue(any('manual limit' in e for e in self.check(ctx,out)['errors']))
  out['manual_checks']=[{'id':'limit:proposal:0','artifact':'proposal','status':'pass','evidence':'Synthetic render measurement: one page','source_ids':['g'],'artifact_digest':si.digest(out['artifacts'][0])}]
  self.assertEqual(self.check(ctx,out)['status'],'mechanical_checks_pass')
  out['artifacts'][0]['sections'][1]['text']='Changed after render'
  self.assertEqual(self.check(ctx,out)['status'],'fail')
 def test_rule_section_is_enforced(self):
  std=standard(); std['formats']['proposal']['section_order'].append('conflicts'); std['rules']=[{'id':'coi','artifact':'proposal','requirement':'Conflict statement','source_id':'g','strength':'mandatory','required_section':'conflicts'}]; self.install_standard(std)
  prep=si.prepare(self.bank,self.req,TODAY); ctx=si.compile_context(self.bank,self.req,rankings(prep['style_candidates']),TODAY)
  errors=self.check(ctx,self.ready_output())['errors']; self.assertTrue(any('missing official sections' in e for e in errors)); self.assertTrue(any('Mandatory rule' in e for e in errors))
 def test_invalid_journal_structure_rejected(self):
  for mutation in ('order','source','bounds'):
   std=standard()
   if mutation=='order': std['formats']['proposal']['required_sections'].append('unknown')
   if mutation=='source': std['sources'].append(copy.deepcopy(std['sources'][0]))
   if mutation=='bounds': std['formats']['proposal']['limits'][0]['min']=999
   self.assertTrue(si.journal_errors(std,TODAY))
 def test_journal_required_contact_fields(self):
  std=standard(); std['required_input_paths']=['guest_editors.*.email']; self.install_standard(std)
  self.assertEqual(si.prepare(self.bank,self.req,TODAY)['status'],'blocked')
  self.req['guest_editors'][0]['email']='test@example.invalid'; self.assertEqual(si.prepare(self.bank,self.req,TODAY)['status'],'awaiting_semantic_ranking')
 def test_tentative_window_and_dependency(self):
  self.req['intended_timeline']['milestones']=[{'label':'Publication','window':'Q3 2028'}]; self.assertFalse(si.input_errors(self.req))
  self.req['intended_timeline']['milestones']=[{'label':'Submission','date':'2027-12-01'},{'label':'Decision','date':'2027-01-01','after':'Submission'}]; self.assertTrue(si.input_errors(self.req))
 def test_conflicting_explicit_mode_and_feedback(self):
  self.req.update(mode='derive',source_proposal='source',deliverables=['cfp'],editor_feedback=[{'id':'E1','comment':'fix'}]); self.assertTrue(si.input_errors(self.req))
 def test_revise_and_derivatives_not_dropped(self):
  self.req.update(mode='revise',source_proposal='source',deliverables=['cfp','cover_letter'],editor_feedback=[{'id':'E1','comment':'fix'}])
  self.assertEqual(si.requested_artifacts(self.req),{'proposal','editor_response','cfp','cover_letter'})
 def test_official_required_cfp_generates_style_request(self):
  std=standard(); std['required_artifacts']=['cfp']; self.install_standard(std); prep=si.prepare(self.bank,self.req,TODAY); ctx=si.compile_context(self.bank,self.req,rankings(prep['style_candidates']),TODAY)
  self.assertIn('cfp',ctx['requested_artifacts']); self.assertTrue(any(x['role']=='cfp_style' for x in ctx['slots']['FEW_SHOT_STYLE_EXAMPLES']))
 def test_cfp_ranks_are_independent_and_type_checked(self):
  self.install_standard(); self.req['include_cfp']=True; prep=si.prepare(self.bank,self.req,TODAY); ranks=rankings(prep['style_candidates'])
  for x in ranks['cfp_rankings']: x['semantic_score']=100 if x['sample_id']=='SYN-03' else 10
  ctx=si.compile_context(self.bank,self.req,ranks,TODAY)
  self.assertEqual([x for x in ctx['slots']['FEW_SHOT_STYLE_EXAMPLES'] if x['role']=='cfp_style'][0]['sample_id'],'SYN-03')
  ranks['cfp_rankings'][0]['sample_id']='SYN-10'
  with self.assertRaises(ValueError): si.compile_context(self.bank,self.req,ranks,TODAY)
 def test_empty_private_bank_degrades_without_invention(self):
  self.install_standard(); idx=si.read(self.bank/'index.json'); idx['private_style_bank']=[]; si.dump(self.bank/'index.json',idx)
  prep=si.prepare(self.bank,self.req,TODAY); ctx=si.compile_context(self.bank,self.req,rankings([]),TODAY)
  self.assertEqual(ctx['style_top2'],[]); self.assertEqual(ctx['style_warning'],'No private examples')
 def test_stale_candidate_digest(self):
  prep=si.prepare(self.bank,self.req,TODAY); ranks=rankings(prep['style_candidates']); ranks['candidate_digest']='wrong'
  with self.assertRaises(ValueError): si.compile_context(self.bank,self.req,ranks,TODAY)
 def test_unverified_or_orphan_evidence_blocks_ready(self):
  ctx=self.context(); out=self.ready_output(); out['evidence_ledger'][0]['status']='unverified'; self.assertEqual(self.check(ctx,out)['status'],'fail')
  out=self.ready_output(); out['fact_claims'][0]['evidence_ids']=['missing']; self.assertEqual(self.check(ctx,out)['status'],'fail')
  out=self.ready_output(); out['fact_claims'][0]['kind']='literature'; self.assertEqual(self.check(ctx,out)['status'],'fail')
 def test_false_ge_and_date_manifest(self):
  ctx=self.context(); out=self.ready_output(); out['artifacts'][0]['canonical_facts']['guest_editors'][0]['name']='Invented'
  self.assertTrue(any('GE roster' in e for e in self.check(ctx,out)['errors']))
  out=self.ready_output(); out['artifacts'][0]['canonical_facts']['milestones'][0]['value']='2099-01-01'; self.assertTrue(any('Date unsupported' in e for e in self.check(ctx,out)['errors']))
 def test_output_language_mode(self):
  ctx=self.context(); out=self.ready_output(); out.update(mode='derive',language='zh'); errors=self.check(ctx,out)['errors']; self.assertTrue(any('mode mismatch' in e for e in errors)); self.assertTrue(any('language mismatch' in e for e in errors))
 def test_nan_rejected(self):
  prep=si.prepare(self.bank,self.req,TODAY); ranks=rankings(prep['style_candidates']); ranks['rankings'][0]['semantic_score']=float('nan')
  with self.assertRaises(ValueError): si.compile_context(self.bank,self.req,ranks,TODAY)
 def test_blocked_response_does_not_need_fake_prose(self):
  out=self.ready_output(); out.update(status='blocked',artifacts=[],unresolved_questions=['Please provide official rules']); self.assertEqual(self.check({},out)['status'],'blocked_response_valid')
 def test_raw_claims_not_injected(self):
  ctx=self.context()
  for ex in ctx['slots']['FEW_SHOT_STYLE_EXAMPLES']:
   self.assertFalse(ex['raw_excerpts_injected']); self.assertNotIn('proposal_excerpts',ex)
 def test_invalid_private_bundle_rejected_before_copy(self):
  source=Path(self.tmp.name)/'incomplete'; source.mkdir(); si.dump(source/'record.json',{})
  with self.assertRaises(ValueError): si.ingest(self.bank,'X',source)
 def test_safe_path_rejects_escape(self):
  with self.assertRaises(ValueError): si.safe(self.bank,'../../secret')

 def discovery_request(self): return {'mode':'draft','journal':{'abbr':'TEST'}}
 def discovery_output(self,req):
  sources=[{'id':i,'url':'https://example.invalid/'+i,'title':'Synthetic '+i,'kind':kind,'checked_on':'2026-10-28','finding':'Synthetic evidence'} for i,kind in [('scope','official_scope'),('si','official_si'),('paper','primary_research')]]
  candidate={'id':'c1','title':'Synthetic candidate','scientific_question':'Synthetic question','why_now':'Synthetic evidence-based timing','journal_fit':'Synthetic scope fit','topics':['Synthetic topic'],'scope_risk':'Bounded in fixture','community_feasibility':'Potential community, no commitments','research_source_ids':['paper'],'comparisons':[{'issue_id':'si1','shared_problem':'Fixture overlap','shared_methods':'Fixture overlap','shared_applications':'Fixture overlap','difference':'Fixture distinction','residual_risk':'Coverage limited'}],'overlap_risk':'medium','recommendation':'Discuss before drafting'}
  return {'mode':'draft','draft_stage':'discover','status':'awaiting_topic_selection','request_digest':si.digest(req),'language':'en','journal_identity':{'full_name':'Example Test Journal','abbr':'TEST','scope_source_ids':['scope']},'sources':sources,'search_log':[{'query':'Synthetic search','url':'https://example.invalid/search','checked_on':'2026-10-28','category':c,'result':'Synthetic result'} for c in ('scope','guidelines','active_si','forthcoming_si','past_si','research')],'coverage':{'lookback_years':5,'limitations':['Synthetic fixture, not live research'],'no_match_explanation':'','fewer_candidates_reason':'Only one synthetic candidate in this test'},'historical_issues':[{'id':'si1','title':'Synthetic old SI','status':'published','period':'2025','scope':'Synthetic scope','source_ids':['si']}],'candidates':[candidate],'unresolved_questions':[],'next_action':'Ask user to select or refine topic; do not write Proposal yet'}
 def test_journal_only_starts_discovery_without_ge(self):
  req=self.discovery_request(); result=si.prepare(self.bank,req,TODAY)
  self.assertEqual(result['mode'],'draft'); self.assertEqual(result['status'],'research_required'); self.assertEqual(result['journal_standard']['status'],'missing')
  self.assertEqual(si.compile_context(self.bank,req,{},TODAY)['status'],'research_required')
 def test_explicit_write_still_requires_full_inputs(self):
  req=self.discovery_request(); req['draft_stage']='write'
  self.assertEqual(si.prepare(self.bank,req,TODAY)['status'],'blocked')
 def test_publisher_only_discovery_blocked(self):
  req=self.discovery_request(); req['journal']['abbr']='IET'
  self.assertEqual(si.prepare(self.bank,req,TODAY)['status'],'blocked')
 def test_discovery_does_not_override_revision(self):
  req=request(); req.update(mode='revise',draft_stage='discover',source_proposal='source',editor_feedback=[{'id':'E1','comment':'Fix'}])
  self.assertTrue(si.input_errors(req))
 def test_discovery_positive_traceability(self):
  req=self.discovery_request(); self.assertEqual(si.check_output(req,{},self.discovery_output(req),TODAY,self.bank)['status'],'mechanical_checks_pass')
 def test_discovery_no_history_cannot_claim_low_overlap(self):
  req=self.discovery_request(); out=self.discovery_output(req); out['historical_issues']=[]; out['candidates'][0]['comparisons']=[]; out['candidates'][0]['overlap_risk']='low'
  self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'fail')
  out['candidates'][0]['overlap_risk']='unknown'; out['coverage']['no_match_explanation']='No official calls found in synthetic search boundary'
  self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'mechanical_checks_pass')
 def test_discovery_requires_primary_evidence(self):
  req=self.discovery_request(); out=self.discovery_output(req); out['candidates'][0]['research_source_ids']=['scope']
  self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'fail')
 def test_discovery_search_coverage_gate(self):
  req=self.discovery_request(); out=self.discovery_output(req); out['search_log']=[]
  self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'fail')
 def test_discovery_request_and_dates_bound(self):
  req=self.discovery_request(); out=self.discovery_output(req); out['request_digest']='stale'; out['sources'][0]['checked_on']='2099-01-01'
  self.assertGreaterEqual(len(si.check_discovery(req,out,TODAY)['errors']),2)
 def test_discovery_cannot_release_proposal_artifacts(self):
  req=self.discovery_request(); out=self.discovery_output(req); out['artifacts']=[{'kind':'proposal'}]
  self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'fail')

 def test_discovery_incomplete_needs_no_invented_sources(self):
  req=self.discovery_request(); out=self.discovery_output(req)
  out.update(status='research_incomplete',sources=[],search_log=[],historical_issues=[],candidates=[],journal_identity={'full_name':'','abbr':'TEST','scope_source_ids':[]},unresolved_questions=['Need official source access'])
  self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'mechanical_checks_pass')
  out['status']='awaiting_topic_selection'; self.assertEqual(si.check_discovery(req,out,TODAY)['status'],'fail')

if __name__=='__main__': unittest.main(verbosity=2)
