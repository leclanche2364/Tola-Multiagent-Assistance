# QA S7 Sign-Off Draft — Curriculum Registry (Batch S7)

**Batch:** S7 — Curriculum Registry  
**Date:** 2026-09-30  
**Environment:** Local (macOS 13.7.8, Python 3.14)  
**Model route:** N/A (deterministic code only)  
**Fixture version:** S7 v1.0  

---

## Functional Tests

| Test ID | Description | Result |
|---------|-------------|--------|
| S7-01 | Handbook source: correct version | PASS |
| S7-01 | Assignment guidance source: correct version | PASS |
| S7-01 | IntenSIQ topic source: correct version | PASS |
| S7-01 | Source version=None returns latest | PASS |
| S7-01 | Source version missing returns None | PASS |
| S7-02 | Assignment node links to guidance source | PASS |
| S7-02 | Assignment node provenance matches source | PASS |
| S7-02 | Handbook node links to handbook source | PASS |
| S7-02 | Nodes from different sources are distinct | PASS |
| S7-02 | Assignment node content preserved | PASS |
| S7-03 | IntenSIQ topic mapped to curriculum node | PASS |
| S7-03 | Mapping persists after creation | PASS |
| S7-03 | Multiple IntenSIQ topics mapped | PASS |
| S7-03 | get_mappings_for_node works | PASS |
| S7-03 | Mapping rejects unknown node | PASS |
| S7-03 | Mapping rejects duplicate ID | PASS |
| S7-04 | Handbook node provenance complete | PASS |
| S7-04 | validate_all_nodes passes (all traceable) | PASS |
| S7-04 | validate_all_nodes passes (multiple sources) | PASS |
| S7-04 | Node stores source version at creation | PASS |
| S7-04 | Outcome linked to traceable node | PASS |
| S7-04 | Topic link from/to must exist | PASS |
| S7-04 | get_nodes_by_source works | PASS |
| S7-04 | get_nodes_by_source empty when none | PASS |
| S7-05 | replace_source returns old and new | PASS |
| S7-05 | Superseded source still retrievable | PASS |
| S7-05 | get_source_history returns all versions | PASS |
| S7-05 | Nodes on old version still traceable | PASS |
| S7-05 | replace_source preserves name and type | PASS |
| S7-05 | replace_source rejects same version | PASS |
| S7-05 | replace_source rejects unknown source | PASS |
| S7-05 | History preserved across multiple replacements | PASS |
| S7-05 | v1 content unchanged after v2 replacement | PASS |
| S7-05 | get_source with no version returns latest | PASS |
| S7-05 | get_source_history empty for unknown source | PASS |

## Edge Cases

| Test ID | Description | Result |
|---------|-------------|--------|
| Edge | Untraceable node rejected (no source) | PASS |
| Edge | Untraceable node rejected (wrong version) | PASS |
| Edge | Duplicate source version rejected | PASS |
| Edge | Duplicate source version different source_id allowed | PASS |
| Edge | Duplicate node_id rejected | PASS |
| Edge | Source missing ID raises | PASS |
| Edge | Source missing type raises | PASS |
| Edge | Source unknown type raises | PASS |
| Edge | Source missing version raises | PASS |
| Edge | Source missing hash raises | PASS |
| Edge | Node missing provenance raises | PASS |
| Edge | Node missing provenance key raises | PASS |
| Edge | Outcome added and retrieved | PASS |
| Edge | Outcome rejects unknown node | PASS |
| Edge | Outcome rejects duplicate ID | PASS |
| Edge | Outcome rejects empty mastery_dimensions | PASS |
| Edge | Outcome rejects non-string mastery_dimension | PASS |
| Edge | get_outcomes_by_node works | PASS |
| Edge | Topic link added and retrieved | PASS |
| Edge | Topic link rejects unknown from_node | PASS |
| Edge | Topic link rejects unknown to_node | PASS |
| Edge | Topic link rejects unknown link_type | PASS |
| Edge | Topic link rejects duplicate ID | PASS |
| Edge | get_topic_links_for_node works | PASS |
| Edge | get_topic_links_to_node works | PASS |
| Edge | validate_returns_counts | PASS |
| Edge | validate_rejects_untraceable_node | PASS |
| Edge | get_state_returns_complete_state | PASS |
| Edge | get_state_sources_preserved | PASS |
| Edge | get_state_complete_with_links | PASS |
| Edge | Fixtures are deterministic | PASS |
| Edge | Version comparison (numeric) | PASS |
| Edge | Version comparison (equal) | PASS |
| Edge | Version comparison (with suffix) | PASS |
| Edge | Registry uses injected clock | PASS |
| Edge | Registry default clock is utcnow | PASS |

## Integration

| Test ID | Description | Result |
|---------|-------------|--------|
| Integration | Full curriculum ingestion flow | PASS |
| Integration | Source replacement then validation | PASS |
| Integration | Complete history preserved | PASS |

## Test Counts

- Prior suite (S0–S6): **365 tests**
- New S7 tests: **78 tests**
- Combined total: **443 tests**
- All green: **YES**
- Failures: **0**
- Errors: **0**

## Deviations

None. All S7-01..S7-05 QA criteria met. Edge cases for untraceable node rejection, superseded source retrieval, and duplicate source version handling are covered. No network calls, no real clocks, no prompt hard-coding.

## Files Changed

- `scholar/curriculum/registry.py` — new (versioned curriculum registry)
- `scholar/fixtures/curriculum.py` — new (deterministic fixtures)
- `scholar/tests/test_s7_curriculum.py` — new (S7-01..S7-05 + edge cases)

## Constraints Check

- contracts.py: **unchanged**
- event_outbox.py: **unchanged**
- events/consumer.py: **unchanged**
- No git operations performed

---

**Overall:** PASS  
**Approved by:** (pending)  
**Notes:** Ready for sign-off.