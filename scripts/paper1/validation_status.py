"""Report requirement-level evidence; absent acceptance artifacts never imply pass."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def load(relative):
    path = DATA / relative
    return json.loads(path.read_text()) if path.exists() else None


def manifest_hashes_match(registry, source_hashes):
    if not registry or registry.get('source_sha256') != source_hashes:
        return False
    for ref in registry.get('runs', []):
        path = ROOT / ref['path']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
            return False
    return bool(registry.get('runs'))


def artifact_hashes_match(directory, hashes):
    return bool(hashes) and all((directory / name).is_file() and
                               hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
                               for name, expected in hashes.items())


def main():
    audit = load('validation/audit_summary.json')
    pair_review = load('validation/pair_review.json')
    token = load('validation/tokens/summary.json')
    eval_tokens = load('validation/evaluation_tokens/summary.json')
    manifest = load('training_manifests/registry.json')
    secondary = load('training_manifests/secondary/registry.json')
    evaluation = load('evaluation/build_report.json')
    eval_revision = load('validation/evaluation_revision_verification.json')
    development = load('evaluation/development_report.json')
    development_split = load('validation/development_split_review.json')
    calibration = load('validation/calibration/summary.json')
    contexts = load('evaluation/context_report.json')
    cross = load('validation/cross_split_text_summary.json')
    domains = load('validation/family_domain_overlap.json')
    reviews = load('validation/human_review/packet_manifest.json')
    fact_review = load('revisions/catalogue_flag_review_001/summary.json')
    scope_review = load('revisions/question_scope_review_001.json')
    scope_followup = load('revisions/question_scope_review_002.json')
    scope_third = load('revisions/question_scope_review_003.json')
    training_filters = load('validation/training_filter_review.json')
    background_prompts = load('validation/background_prompt_review.json')
    hashes = {f'data/paper1/exports/{name}': hashlib.sha256((DATA / 'exports' / name).read_bytes()).hexdigest()
              for name in ['ct_drafts.jsonl', 'it_drafts.jsonl']}
    prompt_review_current = bool(background_prompts and background_prompts.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (background_prompts or {}).get('source_sha256', {}).items())
    main_current = manifest_hashes_match(manifest, hashes)
    secondary_current = bool(manifest_hashes_match(secondary, hashes) and main_current and
                             secondary.get('source_main_registry_sha256') ==
                             hashlib.sha256((DATA / 'training_manifests/registry.json').read_bytes()).hexdigest())
    cross_current = bool(cross and cross.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (cross or {}).get('source_sha256', {}).items())
    domains_current = bool(domains and domains.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (domains or {}).get('source_sha256', {}).items())
    eval_tokens_current = bool(eval_tokens and eval_tokens.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (eval_tokens or {}).get('source_sha256', {}).items())
    eval_revision_current = bool(eval_revision and eval_revision.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (eval_revision or {}).get('source_sha256', {}).items())
    development_current = bool(development and development.get('source_sha256') and development.get('artifact_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in {**(development or {}).get('source_sha256', {}),
                               **(development or {}).get('artifact_sha256', {})}.items())
    development_split_current = bool(development_split and development_split.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (development_split or {}).get('source_sha256', {}).items())
    calibration_current = bool(calibration and calibration.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (calibration or {}).get('source_sha256', {}).items())
    calibration_artifacts_current = artifact_hashes_match(DATA / 'validation/calibration',
                                                          (calibration or {}).get('artifact_sha256', {}))
    filters_current = bool(training_filters and training_filters.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in (training_filters or {}).get('source_sha256', {}).items())
    eval_token_artifacts_verified = artifact_hashes_match(DATA / 'validation/evaluation_tokens', (eval_tokens or {}).get('artifact_sha256', {}))
    train_token_inputs_current = bool(token and token.get('source_sha256') == hashes and
                                     token.get('model_spec_sha256') == hashlib.sha256((DATA / 'validation/model_spec.json').read_bytes()).hexdigest())
    train_token_artifacts_verified = artifact_hashes_match(DATA / 'validation/tokens',
        {'records.jsonl': token['token_records_sha256']} if token and token.get('token_records_sha256') else {})
    states = {
        'content': {'status': 'incomplete', 'evidence': 'validation/content_review.jsonl',
                    'current_input_verified': bool(audit and audit['input_sha256'] == hashes),
                    'triage_counts': audit['content_issue_counts'] if audit else None,
                    'pair_review': {
                        'evidence': 'validation/pair_review.json',
                        'pairs_flagged': len(pair_review) if pair_review is not None else None,
                        'declared_fact_mismatches': sum('declared_fact_sets_differ' in r['issues'] for r in pair_review) if pair_review is not None else None,
                        'current_input_verified': bool(audit and audit['input_sha256'] == hashes),
                        'semantic_acceptance': False
                    },
                    'human_review_pairs_prepared': reviews['prepared_pairs'] if reviews else 0,
                    'repaired_records_pending_human_review': reviews.get('repaired_records_requiring_review', 0) if reviews else 0,
                    'assistant_review_of_original_fact_flags': {
                        'reviewed_records': fact_review['reviewed_records'], 'categories': fact_review['categories'],
                        'source_is_historical_snapshot': True, 'independent_human_acceptance': False
                    } if fact_review else None,
                    'candidate_scope_review': {
                        'initial_triage_candidates': scope_review['triage_candidates'],
                        'edited_questions': scope_review['selected_records'] + (scope_followup['selected_records'] if scope_followup else 0) + (scope_third['selected_records'] if scope_third else 0),
                        'third_review_questions': scope_third['reviewed_questions'] if scope_third else 0,
                        'third_review_scope_repairs': scope_third['selected_records'] if scope_third else 0,
                        'deferred_candidates_from_initial_queue': scope_followup['previous_queue_deferred'] if scope_followup else scope_review['deferred_records'],
                        'expanded_review_decisions': scope_followup['decisions'] if scope_followup else None,
                        'source_is_historical_snapshot': True,
                        'independent_human_acceptance': False,
                        'not_a_complete_semantic_scope_audit': True,
                        'evidence': ['revisions/question_scope_review_001.json'] +
                                    (['revisions/question_scope_review_002.json'] if scope_followup else []) +
                                    (['revisions/question_scope_review_003.json'] if scope_third else [])
                    } if scope_review else None,
                    'repeated_background_prompt_review': {
                        'current_input_verified': prompt_review_current,
                        'flagged_groups': background_prompts['flagged_groups'] if prompt_review_current else None,
                        'flagged_records': background_prompts['flagged_records'] if prompt_review_current else None,
                        'semantic_acceptance': False
                    },
                    'missing': 'Resolved factual/treatment review and actual independent labels'},
        'similarity_and_leakage': {'status': 'incomplete', 'near_scan_complete': bool(audit and audit['input_sha256'] == hashes),
                    'near_duplicate_records': audit['near_duplicate_records_outside_declared_pairs'] if audit else None,
                    'cross_split_text_scan_current': cross_current,
                    'cross_split_text_matches': cross.get('matches') if cross_current else None,
                    'heldout_families_with_equal_catalogue_eligibility_rules': cross.get('heldout_families_with_equal_eligibility_rules') if cross_current else None,
                    'candidate_domain_audit_current': domains_current,
                    'heldout_groups_contained_in_represented_domains': domains.get('contained_heldout_groups') if domains_current else None,
                    'heldout_families_contained_for_all_targets': domains.get('families_contained_for_all_targets') if domains_current else None,
                    'reviewed_training_filters': {
                        'current_input_verified': filters_current,
                        'assistant_annotated_tasks': training_filters['reviewed_training_tasks'] if filters_current else 0,
                        'catalogue_selection_equalities': training_filters['catalogue_selection_equalities'] if filters_current else None,
                        'local_selection_equalities': training_filters['local_selection_equalities'] if filters_current else None,
                        'semantic_isolation_verified': False,
                        'evidence': 'validation/training_filter_review.json'
                    },
                    'missing': 'Verified semantic family isolation; threshold scan is not semantic equivalence proof'},
        'tokenization': {'status': 'passed' if token and token.get('token_gate_pass') and train_token_inputs_current and train_token_artifacts_verified else 'incomplete',
                    'tokenized_records': token.get('tokenized_records', 0) if token else 0,
                    'current_input_verified': train_token_inputs_current,
                    'token_artifacts_verified': train_token_artifacts_verified,
                    'missing': 'Actual chosen-model tokenizer assets and verified exact pair budgets'},
        'training_manifests': {'status': 'compiled_not_accepted' if manifest else 'incomplete',
                    'trajectory_runs': manifest['trajectory_runs'] if manifest else 0,
                    'current_input_verified': main_current,
                    'fixed_budget_runs': secondary['fixed_budget_runs'] if secondary else 0,
                    'sequential_stage_runs': secondary['sequential_stage_runs'] if secondary else 0,
                    'secondary_current_input_verified': secondary_current,
                    'secondary_note': 'CT-to-IT execution remains an optional extension; schedules are prepared.',
                    'missing': 'Accepted content/splits, measured token/loss masks and MLX runtime order/restore checks'},
        'evaluation': {'status': 'incomplete', 'queries': evaluation['created_queries'] if evaluation else 0,
                    'planned_queries': 800, 'context_packets': contexts['context_packets'] if contexts else 0,
                    'family_definition_version': evaluation.get('family_definition_version') if evaluation else None,
                    'revision_checks_current': eval_revision_current,
                    'changed_semantic_tasks': eval_revision.get('changed_semantic_tasks') if eval_revision_current else None,
                    'target_role_distribution': eval_revision.get('target_role_distribution', {}).get('v3') if eval_revision_current else None,
                    'target_suitability_balance_accepted': False,
                    'development_inputs_current': development_current,
                    'development_queries': development['created_queries'] if development_current else 0,
                    'development_definition_version': development.get('development_definition_version') if development_current else None,
                    'development_partitions': development.get('partition_queries') if development_current else None,
                    'development_final_text_scan_current': development_split_current,
                    'development_final_near_text_pairs': development_split.get('matched_segment_pairs') if development_split_current else None,
                    'development_semantic_split_verified': False,
                    'calibration_evidence_current': calibration_current,
                    'calibration_status': calibration.get('status') if calibration_current else 'missing_or_stale',
                    'calibration_responses_loaded': calibration.get('loaded_response_count', 0) if calibration_current else 0,
                    'declared_observed_pilot_responses': calibration.get('responses', 0) if calibration_current and calibration.get('integrity_checks_pass') and calibration.get('data_origin') == 'observed_model_responses' else 0,
                    'calibration_protocol_checks_pass': bool(calibration_current and calibration_artifacts_current and calibration.get('declared_protocol_checks_pass')),
                    'research_measurement_validated': False,
                    'missing_queries': evaluation['missing_queries'] if evaluation else 800,
                    'token_evidence_current': eval_tokens_current,
                    'structure_preflight_pass': eval_tokens.get('structure_preflight_pass', False) if eval_tokens_current else False,
                    'tokenized_prompts': eval_tokens.get('tokenized_prompts', 0) if eval_tokens_current else 0,
                    'tokenized_source_passages': eval_tokens.get('tokenized_source_texts', 0) if eval_tokens_current else 0,
                    'token_artifacts_verified': eval_token_artifacts_verified,
                    'token_gate_pass': bool(eval_tokens_current and eval_token_artifacts_verified and eval_tokens.get('token_gate_pass', False)),
                    'missing': 'Accept revised final/development families and keys; semantic/context review, tokenizer budgets and real human/judge calibration'},
    }
    report = {'updated_utc': datetime.now(timezone.utc).isoformat(), 'goal_status': 'active',
              'research_ready': False, 'training_authorized_by_validation': False, 'requirements': states,
              'note': 'This report records evidence and open work. It does not promote draft artifacts based on fixture tests.'}
    (DATA / 'validation/status.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v['status'] for k, v in states.items()}))


if __name__ == '__main__':
    main()
