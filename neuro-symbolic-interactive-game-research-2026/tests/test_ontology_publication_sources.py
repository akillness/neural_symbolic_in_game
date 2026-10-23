"""Publication source identity and frozen, bilingual scientific declarations.

These are additional review regressions, not edits to the frozen native-case checks.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "game-track/web/dashboard/ontology-map.json"
PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"
SCENARIO = ROOT / "game-track/godot/data/sealed_lighthouse.json"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def producer():
    # A fresh module per test isolates the filesystem boundary without module-registry
    # mocking. The script adds src to sys.path during import; restore it on teardown.
    original_path = sys.path[:]
    try:
        spec = importlib.util.spec_from_file_location(
            "ontology_publication_producer", ROOT / "scripts/generate_signal_explainer.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = original_path


@pytest.mark.parametrize(
    "section,field,wrong",
    [
        (None, "schema_version", "ontology-evidence-map/v2"),
        ("source_packet", "path", "research/npc-disclosure/other-packet.json"),
        ("source_packet", "packet_id", "other-expectations-v1"),
        ("source_packet", "packet_version", "2.0.0"),
        ("source_packet", "status", "RUNTIME_RESULTS"),
        ("scenario", "path", "game-track/godot/data/other-scenario.json"),
        ("source_packet", "sha256", "0" * 64),
        ("scenario", "sha256", "0" * 64),
    ],
    ids=[
        "schema",
        "packet-path",
        "packet-id",
        "packet-version",
        "packet-status",
        "scenario-path",
        "packet-digest",
        "scenario-digest",
    ],
)
def test_direct_mechanism_rejects_one_wrong_source_identity(
    producer, tmp_path, section, field, wrong
):
    """A matching digest must not make a different source identity publishable."""
    payload = _read(MAP)
    target = payload if section is None else payload[section]
    target[field] = wrong
    isolated_map = tmp_path / "ontology-map.json"
    isolated_map.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    producer.ONTOLOGY_MAP = isolated_map
    with pytest.raises(ValueError, match=r"mechanism ontology (schema|source binding) drift"):
        producer.mechanism_svg()


def test_valid_mechanism_preserves_approved_figure_bytes(producer):
    """Identity hardening must leave the human-reviewable publication SVG unchanged."""
    approved = ROOT / "paper/latex/figures/fig_signal_mechanism.svg"
    assert producer.mechanism_svg().encode("utf-8") == approved.read_bytes()


# INDEPENDENT FROZEN SCIENTIFIC-DECLARATION ORACLE, revision 1.
# These approved EN/KO clauses are literal publication output, not source-code
# snippets, default settings, or values learned from the ontology-map under test.
# Exact equality deliberately rejects even paraphrases pending scientific review;
# this is not an NLP equivalence checker and is not independent human gold.
#
# Independent grounding (the source digests are pinned below):
# world: scenario.initial_state.world has reachable harbor_dock/lamp_store and
#        object_locations[signal_lens] = lamp_store (object -> location, not inverse).
# actor: packet.scope.eligible_actor_ids and M-001/M-007 show eligibility and policy
#        precedence, including a forbidden fact requested by an unknown actor.
# knowledge: scenario.npcs.captain_mira.knowledge lists four IDs; N-019/N-020 and
#        N-043/N-044 deny despite knows=true and regardless of prior disclosure.
# fact: scenario.initial_state.facts has only dock_saved/lighthouse_dark;
#        packet.declaration_derivation.fact_axis declares the union and ID-only scope.
# policy: scenario.disclosure_policy forbids keeper_betrayal and gates the hint at
#        2; packet B-003/B-004 establish BELOW denied / AT allowed, not the inverse.
# quest: scenario.initial_state.quest and packet.first_disclosure_effect (under
#        declaration_derivation) establish stage preservation, not observed progress.
# action: packet.declaration_derivation.first_disclosure_effect/redisplay_effect/
#        deny_effect and integration_contract.fresh_state_assertions establish
#        fresh-only additions/revision, hint-only memory, no redisplay/denial mutation.
# trace: packet.strata_denominators and integration_contract.evidence explicitly
#        distinguish frozen expectations from observed events and require bindings.
# The translations below are the approved declarations of those facts; no claim
# is made that token presence, or an automated translation, proves equivalence.
APPROVED_DECLARATIONS = {
    "world": (
        "sealed-lighthouse-v1; initial_state.world; initial_state.player",
        "Initially harbor_dock and lamp_store are reachable; signal_lens is at lamp_store. These are scenario declarations, not current player position.",
        "초기 도달 가능 장소는 harbor_dock, lamp_store이며 signal_lens는 lamp_store에 있다. 현재 플레이어 위치를 뜻하지 않는다.",
    ),
    "actor": (
        "captain_mira; initial_state.npcs.captain_mira",
        "captain_mira is the only eligible disclosure actor. Actor eligibility is checked after policy; unknown actors are denied.",
        "공개 적격 행위자는 captain_mira뿐이다. 정책 확인 후 적격성을 확인하며 미등록 행위자는 거부한다.",
    ),
    "knowledge": (
        "captain_mira.knowledge → canonical fact IDs",
        "Mira initially knows dock_saved, keeper_betrayal, lighthouse_dark and tide_marks_hint. Knowing a fact does not authorize disclosure; prior disclosed membership also does not bypass authorization.",
        "미라의 초기 지식은 dock_saved, keeper_betrayal, lighthouse_dark, tide_marks_hint이다. 지식이나 과거 공개 이력만으로 공개가 허용되지는 않는다.",
    ),
    "fact": (
        "dock_saved; keeper_betrayal; lighthouse_dark; tide_marks_hint",
        "Initial facts are dock_saved and lighthouse_dark. The four canonical IDs are the union of initial facts and Mira knowledge; keeper_betrayal is an identifier only, with no secret payload here.",
        "초기 사실은 dock_saved, lighthouse_dark이다. 네 정규 ID는 초기 사실과 미라 지식의 합집합이며 keeper_betrayal의 비밀 내용은 포함하지 않는다.",
    ),
    "policy": (
        "sealed-lighthouse-disclosure-v1; permanently_forbidden; stage_gates",
        "keeper_betrayal is permanently forbidden. tide_marks_hint requires quest.stage ≥ 2. Policy denial precedes actor/knowledge checks; denial uses mira-safe-deflection-v1 without canonical mutation.",
        "keeper_betrayal은 영구 공개 금지이다. tide_marks_hint에는 quest.stage ≥ 2가 필요하다. 정책 거부는 행위자·지식 확인보다 우선하며 mira-safe-deflection-v1만 표시하고 정규 상태를 보존한다.",
    ),
    "quest": (
        "initial_state.quest.stage; quest.flags; tide_marks_hint",
        "Initial stage is 0 with dock_saved flag. The hint gate is stage 2; disclosure preserves stage. B-003/B-004 probe stages 1/2, not observed quest progress.",
        "초기 단계는 0이며 dock_saved 플래그가 있다. 힌트 허용 단계는 2이고 공개 시 단계는 유지된다. B-003/B-004는 단계 1/2의 기대 사례이며 관측 진행도가 아니다.",
    ),
    "action": (
        "reveal_hint(actor_id, fact_id); sl-rc-003-authorized-hint",
        "Fresh authorization adds the requested fact and disclosed ID, preserves stage and increments revision once. Only tide_marks_hint adds turn-05:mira-shared-tide-marks-hint. Authorized redisplay rechecks permission with no mutation; generic allowed facts have no dialogue template.",
        "최초 허용 공개는 요청 사실과 공개 ID를 추가하고 단계를 보존하며 리비전을 한 번 증가시킨다. tide_marks_hint만 turn-05:mira-shared-tide-marks-hint를 추가한다. 재표시는 권한을 재확인하고 상태를 바꾸지 않는다. 일반 허용 사실에는 대화 템플릿이 없다.",
    ),
    "trace": (
        "prior_state_hash; next_state_hash; rule_ids; template_id; case_id",
        "Frozen expectations contain 48 normal, 4 boundary and 8 malformed cases, plus two rule-change fixtures. They are not live events. Evidence binds packet/version, rules, hashes and template; missing runtime fields cannot establish a pass or full state.",
        "동결 기대값은 정상 48건, 경계 4건, 비정상 8건과 규칙 변경 픽스처 2건이다. 실시간 이벤트가 아니다. 근거에는 패킷·버전, 규칙, 해시, 템플릿이 연결되며 누락 필드는 통과나 전체 상태의 근거가 될 수 없다.",
    ),
}


@pytest.fixture(scope="module")
def frozen_sources():
    # Pin the independently reviewed inputs, so coordinated map/source drift cannot
    # silently redefine the oracle. Never derive expected clauses from MAP.
    for path, digest in (
        (PACKET, "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"),
        (SCENARIO, "f262455e57be7204f5f597736a89379f37f3f698475fa745a48be6ef2ebb28d9"),
    ):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
    return _read(PACKET), _read(SCENARIO)


def _assert_approved_role(role):
    identifiers, english, korean = APPROVED_DECLARATIONS[role["id"]]
    assert role["identifiers"] == identifiers, f"{role['id']}.identifiers direction"
    assert role["content"]["en"] == english, f"{role['id']}.en approved declaration"
    assert role["content"]["ko"] == korean, f"{role['id']}.ko approved declaration"


@pytest.mark.parametrize("role_id", tuple(APPROVED_DECLARATIONS))
def test_eight_roles_preserve_approved_bilingual_declarations(frozen_sources, role_id):
    payload = _read(MAP)
    assert sorted(role["id"] for role in payload["roles"]) == sorted(APPROVED_DECLARATIONS)
    role = next(role for role in payload["roles"] if role["id"] == role_id)
    _assert_approved_role(role)


# Mutations deliberately retain the IDs, numeric stage boundaries and rule IDs
# that the native-case token checks accept. They alter one substantive assertion
# in memory only: no map, frozen packet, scenario, or production file is written.
@pytest.mark.parametrize(
    "role_id,field,before,after",
    [
        ("world", "en", "signal_lens is at lamp_store", "lamp_store is at signal_lens"),
        ("world", "ko", "signal_lens는 lamp_store에 있다", "lamp_store는 signal_lens에 있다"),
        ("actor", "en", "after policy", "before policy"),
        ("actor", "ko", "정책 확인 후", "정책 확인 전"),
        ("knowledge", "identifiers", "→", "←"),
        ("knowledge", "en", "does not authorize disclosure", "does authorize disclosure"),
        ("knowledge", "ko", "공개가 허용되지는 않는다", "공개가 허용된다"),
        ("knowledge", "en", "does not bypass authorization", "does bypass authorization"),
        ("fact", "en", "with no secret payload here", "with secret payload here"),
        ("fact", "ko", "비밀 내용은 포함하지 않는다", "비밀 내용은 포함한다"),
        ("policy", "en", "permanently forbidden", "permanently permitted"),
        ("policy", "ko", "영구 공개 금지이다", "영구 공개 허용이다"),
        ("policy", "en", "quest.stage ≥ 2", "quest.stage < 2"),
        ("policy", "ko", "quest.stage ≥ 2", "quest.stage < 2"),
        ("policy", "en", "without canonical mutation", "with canonical mutation"),
        ("policy", "ko", "정규 상태를 보존한다", "정규 상태를 변경한다"),
        ("quest", "en", "disclosure preserves stage", "disclosure advances stage"),
        ("quest", "ko", "공개 시 단계는 유지된다", "공개 시 단계는 증가한다"),
        ("action", "en", "Fresh authorization adds", "Redisplay authorization adds"),
        ("action", "ko", "최초 허용 공개는", "재표시 허용 공개는"),
        ("action", "en", "Only tide_marks_hint adds", "Every fact including tide_marks_hint adds"),
        ("action", "ko", "tide_marks_hint만", "tide_marks_hint를 포함한 모든 사실이"),
        (
            "action",
            "en",
            "rechecks permission with no mutation",
            "bypasses permission with mutation",
        ),
        ("action", "ko", "권한을 재확인하고 상태를 바꾸지 않는다", "권한을 무시하고 상태를 바꾼다"),
        ("trace", "en", "They are not live events", "They are live events"),
        ("trace", "ko", "실시간 이벤트가 아니다", "실시간 이벤트이다"),
    ],
    ids=[
        "world-direction-en",
        "world-direction-ko",
        "policy-precedence-en",
        "policy-precedence-ko",
        "knowledge-edge-direction",
        "knowledge-not-permission-en",
        "knowledge-not-permission-ko",
        "history-not-permission-en",
        "fact-id-not-payload-en",
        "fact-id-not-payload-ko",
        "permanent-denial-en",
        "permanent-denial-ko",
        "minimum-not-maximum-stage-en",
        "minimum-not-maximum-stage-ko",
        "denial-immutable-en",
        "denial-immutable-ko",
        "stage-preserved-en",
        "stage-preserved-ko",
        "fresh-only-en",
        "fresh-only-ko",
        "hint-only-memory-en",
        "hint-only-memory-ko",
        "redisplay-immutable-en",
        "redisplay-immutable-ko",
        "frozen-not-runtime-en",
        "frozen-not-runtime-ko",
    ],
)
def test_frozen_oracle_rejects_token_preserving_polarity_reversals(
    frozen_sources, role_id, field, before, after
):
    payload = _read(MAP)
    original = next(role for role in payload["roles"] if role["id"] == role_id)
    mutated = copy.deepcopy(original)
    target = mutated if field == "identifiers" else mutated["content"]
    assert before in target[field], "mutation must change the intended approved clause"
    target[field] = target[field].replace(before, after, 1)
    # Establish adversarial strength: the mutation still satisfies vocabulary-only
    # evidence. Comparing counts also retains repeated identifiers/stage numbers.
    packet, scenario = frozen_sources
    terms = (
        packet["scope"]["canonical_fact_ids"]
        + packet["scope"]["eligible_actor_ids"]
        + list(packet["rule_ids"])
        + [
            scenario["scenario_id"],
            scenario["disclosure_policy"]["policy_id"],
            "harbor_dock",
            "lamp_store",
            "signal_lens",
            "reveal_hint",
            "turn-05:mira-shared-tide-marks-hint",
            "sl-rc-003-authorized-hint",
            "mira-safe-deflection-v1",
        ]
    )
    original_text = json.dumps(original, ensure_ascii=False)
    mutated_text = json.dumps(mutated, ensure_ascii=False)
    for term in terms:
        assert mutated_text.count(term) == original_text.count(term), term
    assert re.findall(r"\d+", mutated_text) == re.findall(r"\d+", original_text)
    with pytest.raises(AssertionError, match=rf"{role_id}\.(identifiers|en|ko)"):
        _assert_approved_role(mutated)
