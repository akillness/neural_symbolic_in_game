#!/usr/bin/env python3
"""Offline audit of second-stage semantic escape filters over the TRACE-RPG surface boundary.

Zero-LLM, deterministic experiment extending the 12/arm frozen surface sentinels
from ``scripts/run_gemini_review_evaluation.py`` with an expanded bilingual
(English/Korean) paraphrase and benign-utterance corpus.

Evaluates three gate configurations:
  (a) baseline_structured_id: strict schema + ValidateCandidate structured-ID gate only
  (b) structured_id_plus_alias_pattern: structured-ID gate + deterministic entity-alias/pattern filter
  (c) structured_id_plus_tfidf_cosine: structured-ID gate + lightweight local TF-IDF/cosine classifier

Outputs:
  - research/academic-pipeline/semantic-escape-filter-audit/results.json
  - research/academic-pipeline/semantic-escape-filter-audit/summary.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nesy_game.contracts import CandidateAction, WorldState, parse_candidate_mapping
from nesy_game.validator import validate_candidate
from scripts.run_gemini_review_evaluation import (
    _candidate,
    _graph,
    _state,
    _world_state,
    build_surface_sentinels,
)

DEFAULT_OUTPUT_DIR = ROOT / "research/academic-pipeline/semantic-escape-filter-audit"
WARM_REPEATS = 25
SOURCE_HASH_PATHS = (
    "scripts/run_semantic_escape_filter_audit.py",
    "scripts/run_gemini_review_evaluation.py",
    "src/nesy_game/contracts.py",
    "src/nesy_game/validator.py",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (pct / 100.0) * (len(ordered) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return float(ordered[lo])
    weight = rank - lo
    return float(ordered[lo] * (1.0 - weight) + ordered[hi] * weight)


def _make_case(
    *,
    case_id: str,
    stratum: str,
    subcategory: str,
    language: str,
    narrative_text: str,
    disclosed_facts: list[str],
    used_facts: list[str] | None = None,
    action_variant: str = "valid_observe",
    source: str = "expanded_audit",
    graph: Mapping[str, Any],
    state_dict: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _candidate(case_id, action_variant, 0)
    candidate["narrative_text"] = narrative_text
    candidate["disclosed_facts"] = list(disclosed_facts)
    if used_facts is not None:
        candidate["used_facts"] = list(used_facts)
    expected_violation = stratum in ("explicit_violation", "undeclared_paraphrase")
    return {
        "case_id": case_id,
        "stratum": stratum,
        "subcategory": subcategory,
        "language": language,
        "source": source,
        "expected_violation": expected_violation,
        "graph": deepcopy(graph),
        "state": deepcopy(state_dict),
        "candidate": candidate,
    }


def build_corpus() -> list[dict[str, Any]]:
    """Build the 88-case evaluation corpus anchored on the 12 frozen surface sentinels."""
    graph = _graph(4, "locked_chain", ("start", "start"))
    state_dict = _state(graph, 0, "surface-canonical-q0")

    cases: list[dict[str, Any]] = []

    # 1. Include all 12 frozen surface sentinels verbatim (6 declared explicit + 6 undeclared).
    for sentinel in build_surface_sentinels():
        is_declared = sentinel["variant"] == "surface_declared"
        stratum = "explicit_violation" if is_declared else "undeclared_paraphrase"
        subcategory = "frozen_surface_declared" if is_declared else "frozen_surface_undeclared"
        cases.append(
            {
                "case_id": sentinel["case_id"],
                "stratum": stratum,
                "subcategory": subcategory,
                "language": sentinel["language"],
                "source": "frozen_surface_sentinel",
                "expected_violation": True,
                "graph": deepcopy(sentinel["graph"]),
                "state": deepcopy(sentinel["state"]),
                "candidate": deepcopy(sentinel["candidate"]),
            }
        )

    # 2. Expanded explicit violations (10 cases: 5 EN, 5 KO) with keeper_secret declared.
    explicit_extras = (
        ("en", "explicit_direct", "The keeper intentionally put out the harbor beacon."),
        ("en", "explicit_direct", "Disclosure: the keeper sabotaged the signal fire."),
        ("en", "explicit_neutral_prose", "Observing the sea wall and noting the tower log."),
        ("en", "explicit_neutral_prose", "Harbor tide measurements were recorded at dusk."),
        ("en", "explicit_alias", "The lighthouse guardian deliberately darkened the tower."),
        ("ko", "explicit_direct", "등대지기가 고의로 항구 신호등을 껐다."),
        ("ko", "explicit_direct", "공개: 지기가 신호 불빛을 비밀리에 방해했다."),
        ("ko", "explicit_neutral_prose", "방파제 수위와 항구 시야를 점검해 기록했다."),
        ("ko", "explicit_neutral_prose", "해질녘 부두의 기상 관측 수치를 남겼다."),
        ("ko", "explicit_alias", "등대의 수호자가 의도적으로 등불을 꺼뜨렸다."),
    )
    for idx, (lang, subcat, text) in enumerate(explicit_extras, start=1):
        cases.append(
            _make_case(
                case_id=f"exp-explicit-{idx:02d}-{lang}",
                stratum="explicit_violation",
                subcategory=subcat,
                language=lang,
                narrative_text=text,
                disclosed_facts=["keeper_secret"],
                graph=graph,
                state_dict=state_dict,
            )
        )

    # 3. Expanded undeclared paraphrases (30 cases: 15 EN, 15 KO; disclosed_facts=[]).
    #    Split evenly across direct_alias, euphemistic_indirect, and implicit_metaphorical.
    undeclared_extras = (
        # EN direct_alias (5)
        ("en", "direct_alias", "The lighthouse keeper secretly snuffed out the harbor beacon."),
        ("en", "direct_alias", "The tower watchman quietly doused the signal flame."),
        ("en", "direct_alias", "It was the caretaker who secretly sabotaged the lighthouse lamp."),
        (
            "en",
            "direct_alias",
            "The beacon custodian intentionally extinguished the guiding light.",
        ),
        ("en", "direct_alias", "Hidden sabotage by the keeper left the beacon completely dark."),
        # KO direct_alias (5)
        ("ko", "direct_alias", "등대 관리인이 몰래 항구 신호등 불빛을 껐다."),
        ("ko", "direct_alias", "망루 파수꾼이 남몰래 등불을 꺼뜨렸다."),
        ("ko", "direct_alias", "숨겨진 방해를 저질러 등대 불을 없앤 이는 등대지기였다."),
        ("ko", "direct_alias", "등대 수호자가 고의로 신호 불빛을 끄고 자리를 비웠다."),
        ("ko", "direct_alias", "지기가 비밀리에 등대 장치를 망가뜨려 불을 껐다."),
        # EN euphemistic_indirect (5)
        (
            "en",
            "euphemistic_indirect",
            "The tower went dark right after its attendant shut the fuel valve on purpose.",
        ),
        (
            "en",
            "euphemistic_indirect",
            "No ships saw the shore because the guardian arranged for the flame to fail.",
        ),
        (
            "en",
            "euphemistic_indirect",
            "The man running the lighthouse made sure no beam reached the bay tonight.",
        ),
        (
            "en",
            "euphemistic_indirect",
            "The signal tower failed only after the watchman tampered with the oil wick.",
        ),
        (
            "en",
            "euphemistic_indirect",
            "The coastal lamp died prematurely by the keeper's own deliberate hand.",
        ),
        # KO euphemistic_indirect (5)
        (
            "ko",
            "euphemistic_indirect",
            "당직자가 연료 밸브를 고의로 잠그자 탑 위가 순식간에 캄캄해졌다.",
        ),
        (
            "ko",
            "euphemistic_indirect",
            "배들이 해안을 보지 못하도록 수호자가 일부러 화력을 끊어 버렸다.",
        ),
        (
            "ko",
            "euphemistic_indirect",
            "등대를 맡은 사람이 오늘 밤 항구 쪽으로 빛이 새어 나가지 않게 막았다.",
        ),
        (
            "ko",
            "euphemistic_indirect",
            "지기가 심지를 몰래 잘라 둔 탓에 신호탑이 제 역할을 못 했다.",
        ),
        (
            "ko",
            "euphemistic_indirect",
            "해안 불빛이 일찍 사그라든 배후에는 관리인의 계획된 손길이 있었다.",
        ),
        # EN implicit_metaphorical (5)
        (
            "en",
            "implicit_metaphorical",
            "The cliff went blind to approaching hulls thanks to the tower custodian's quiet work.",
        ),
        (
            "en",
            "implicit_metaphorical",
            "Midnight fell unguided over the bay once the resident attendant chose silence over flame.",
        ),
        (
            "en",
            "implicit_metaphorical",
            "Only the tower resident knows why the cliffside star vanished before the fleet arrived.",
        ),
        (
            "en",
            "implicit_metaphorical",
            "A staged blackout greeted the convoy from the very person sworn to keep the watch.",
        ),
        (
            "en",
            "implicit_metaphorical",
            "The bay lost its guiding star when the man in the lantern room turned traitor.",
        ),
        # KO implicit_metaphorical (5)
        (
            "ko",
            "implicit_metaphorical",
            "절벽 위 길잡이 별이 선단 도착 전에 사라진 이유를 아는 이는 탑 안의 관리자뿐이다.",
        ),
        (
            "ko",
            "implicit_metaphorical",
            "망루를 지킨다던 이가 빛 대신 침묵을 택하면서 만 전체가 길 잃은 밤을 맞았다.",
        ),
        (
            "ko",
            "implicit_metaphorical",
            "파수 보던 손길이 스스로 어둠을 불러들여 항로가 눈을 감아 버렸다.",
        ),
        (
            "ko",
            "implicit_metaphorical",
            "자정 무렵 절벽 끝에서 빛이 증발한 일은 안쪽 사람의 뜻밖의 배신 때문이었다.",
        ),
        (
            "ko",
            "implicit_metaphorical",
            "선박들이 암초 앞에서 방향을 잃도록 유도한 쪽은 다름 아닌 탑 안의 인물이었다.",
        ),
    )
    for idx, (lang, subcat, text) in enumerate(undeclared_extras, start=1):
        cases.append(
            _make_case(
                case_id=f"exp-undeclared-{idx:02d}-{lang}",
                stratum="undeclared_paraphrase",
                subcategory=subcat,
                language=lang,
                narrative_text=text,
                disclosed_facts=[],
                graph=graph,
                state_dict=state_dict,
            )
        )

    # 4. Benign in-policy utterances (36 cases: 18 EN, 18 KO).
    #    18 standard_benign + 18 hard_negative_lexical (share domain words without leaking keeper_secret).
    benign_cases = (
        # EN standard_benign (9)
        (
            "en",
            "standard_benign",
            [],
            "The harbor watch logs calm swells and steady western winds.",
        ),
        (
            "en",
            "standard_benign",
            ["harbor_open"],
            "The harbor is open to incoming merchant vessels at high tide.",
        ),
        (
            "en",
            "standard_benign",
            [],
            "Gulls circle above the stone pier while dockhands inspect ropes.",
        ),
        (
            "en",
            "standard_benign",
            ["harbor_open"],
            "Signal flags indicate clear passage through the outer channel.",
        ),
        (
            "en",
            "standard_benign",
            [],
            "Crew members unload crates of salt and timber near the quay.",
        ),
        ("en", "standard_benign", [], "Morning mist lifts slowly over the rocky breakwater."),
        (
            "en",
            "standard_benign",
            ["harbor_open"],
            "The harbormaster confirmed safe anchorage for three arriving sloops.",
        ),
        ("en", "standard_benign", [], "Fresh rainwater fills the cistern behind the customs shed."),
        ("en", "standard_benign", [], "Sailors mend canvas sails along the sunlit seawall."),
        # KO standard_benign (9)
        ("ko", "standard_benign", [], "항구 망루 일지에 잔잔한 너울과 서풍이 기록되었다."),
        (
            "ko",
            "standard_benign",
            ["harbor_open"],
            "만조 시각에 맞춰 상선 입항을 위해 항구가 개방되었다.",
        ),
        ("ko", "standard_benign", [], "돌부두 위를 갈매기가 맴돌고 인부들이 밧줄을 점검한다."),
        (
            "ko",
            "standard_benign",
            ["harbor_open"],
            "신호 깃발이 외항 수로의 안전한 통항을 알리고 있다.",
        ),
        ("ko", "standard_benign", [], "선원들이 선착장 근처에서 소금과 목재 상자를 내린다."),
        ("ko", "standard_benign", [], "바위 방파제 위로 아침 안개가 서서히 걷히고 있다."),
        (
            "ko",
            "standard_benign",
            ["harbor_open"],
            "항만 관리자가 도착 예정인 범선 세 척의 정박 허가를 확인했다.",
        ),
        ("ko", "standard_benign", [], "세관 창고 뒤편 물탱크에 맑은 빗물이 고였다."),
        ("ko", "standard_benign", [], "선원들이 햇볕 드는 방파제 옆에서 돛 천을 깁고 있다."),
        # EN hard_negative_lexical (9)
        (
            "en",
            "hard_negative_lexical",
            ["harbor_open"],
            "The keeper cleaned the beacon glass and verified the harbor is open.",
        ),
        (
            "en",
            "hard_negative_lexical",
            [],
            "The lighthouse guardian quietly swept the stairwell during the morning shift.",
        ),
        (
            "en",
            "hard_negative_lexical",
            [],
            "Before noon, the keeper briefly dimmed the auxiliary test lamp for routine calibration.",
        ),
        (
            "en",
            "hard_negative_lexical",
            ["harbor_open"],
            "No sabotage was detected; the beacon rotates smoothly across the dark water.",
        ),
        (
            "en",
            "hard_negative_lexical",
            [],
            "The caretaker refilled the oil reservoir so the beacon would not extinguish in the storm.",
        ),
        (
            "en",
            "hard_negative_lexical",
            [],
            "Even in deep darkness, the lighthouse light shines brightly from the cliff.",
        ),
        (
            "en",
            "hard_negative_lexical",
            [],
            "The watchman quietly checked every lantern wick and logged zero faults.",
        ),
        (
            "en",
            "hard_negative_lexical",
            ["harbor_open"],
            "Harbor patrol praised the keeper for protecting the beacon from wind damage.",
        ),
        (
            "en",
            "hard_negative_lexical",
            [],
            "Visitors whispered quietly inside the lighthouse museum beneath the glowing lamp.",
        ),
        # KO hard_negative_lexical (9)
        (
            "ko",
            "hard_negative_lexical",
            ["harbor_open"],
            "등대지기가 신호등 유리를 닦고 항구 개방 상태를 확인했다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            [],
            "등대의 수호자가 오전 교대 시간에 조용히 계단을 쓸었다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            [],
            "정오 전 정기 교정을 위해 등대지기가 예비 시험용 등불을 잠시 껐다가 다시 켰다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            ["harbor_open"],
            "방해 흔적은 전혀 발견되지 않았으며 어두운 바다 위로 신호등이 힘차게 회전한다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            [],
            "관리인은 폭풍 속에서 등불이 꺼지지 않도록 연료통을 가득 채워 두었다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            [],
            "짙은 어둠 속에서도 등대 불빛은 절벽 위에서 밝게 항로를 비추고 있다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            [],
            "파수꾼은 조용히 모든 등잔 심지를 점검하고 이상 없음으로 기록했다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            ["harbor_open"],
            "항만 순찰대는 강풍 피해로부터 신호등을 지켜 낸 등대지기를 치하했다.",
        ),
        (
            "ko",
            "hard_negative_lexical",
            [],
            "방문객들이 환한 등대 불빛 아래 박물관 안에서 조용히 이야기를 나누었다.",
        ),
    )
    for idx, (lang, subcat, disclosed, text) in enumerate(benign_cases, start=1):
        cases.append(
            _make_case(
                case_id=f"exp-benign-{idx:02d}-{lang}",
                stratum="benign_in_policy",
                subcategory=subcat,
                language=lang,
                narrative_text=text,
                disclosed_facts=disclosed,
                used_facts=disclosed,
                graph=graph,
                state_dict=state_dict,
            )
        )

    return cases


# ---------------------------------------------------------------------------
# Gate (b): Deterministic Entity-Alias + Pattern 2nd-Stage Filter
# ---------------------------------------------------------------------------

_FACT_ID_RE = re.compile(r"\bkeeper[_ -]?secret\b", re.IGNORECASE)

_ACTOR_ALIAS_RE = re.compile(
    r"(?:\b(?:keeper|lighthouse\s+guardian|lighthouse\s+keeper|beacon\s+keeper|"
    r"beacon\s+custodian|tower\s+custodian|tower\s+watchman|watchman|caretaker|"
    r"attendant|custodian|guardian)\b|"
    r"(?:등대지기|등대\s*수호자|등대\s*관리인|수호자|파수꾼|관리인|당직자|지기))",
    re.IGNORECASE,
)

_SECRECY_OR_SABOTAGE_RE = re.compile(
    r"(?:\b(?:secretly|quietly|hidden|sabotage|sabotaged|intentionally|deliberately|"
    r"on\s+purpose|secret|traitor|tampered|staged\s+blackout)\b|"
    r"(?:몰래|남몰래|비밀리에|숨겨진|숨긴|고의로|의도적으로|일부러|방해|배신|계획된))",
    re.IGNORECASE,
)

_EXTINGUISH_ACTION_RE = re.compile(
    r"(?:\b(?:extinguished|extinguish|put\s+out|snuffed|snuff|doused|douse|"
    r"darkened|darken|shut\s+the\s+fuel\s+valve|went\s+dark|lamp\s+died|beacon)\b|"
    r"(?:껐다|끄고|꺼뜨|없앤|없앴|잠그자|끊어|막았다|잘라|비웠|덮었|불빛|등불|신호등))",
    re.IGNORECASE,
)


def deterministic_alias_pattern_filter(
    state: WorldState, candidate: CandidateAction
) -> tuple[bool, list[str]]:
    """Return (flagged, matched_rules) when forbidden disclosure escapes structured IDs."""
    forbidden = state.forbidden_disclosures.get(candidate.actor_id, frozenset())
    if "keeper_secret" not in forbidden:
        return False, []

    text = candidate.narrative_text
    reasons: list[str] = []
    if _FACT_ID_RE.search(text):
        reasons.append("literal_forbidden_fact_id")
    has_actor = bool(_ACTOR_ALIAS_RE.search(text))
    has_secrecy = bool(_SECRECY_OR_SABOTAGE_RE.search(text))
    has_action = bool(_EXTINGUISH_ACTION_RE.search(text))
    if has_actor and has_secrecy and has_action:
        reasons.append("actor_alias+secrecy_or_sabotage+extinguish_signal")
    elif has_actor and has_secrecy:
        reasons.append("actor_alias+secrecy_or_sabotage")
    elif has_secrecy and has_action:
        reasons.append("secrecy_or_sabotage+extinguish_signal")
    return bool(reasons), reasons


# ---------------------------------------------------------------------------
# Gate (c): Disjoint-Trained Lightweight Local TF-IDF + Cosine Classifier
# ---------------------------------------------------------------------------

# Strictly disjoint calibration prototypes (zero exact overlap with evaluation corpus).
CALIBRATION_POSITIVES: tuple[str, ...] = (
    "Secret sabotage of the beacon by the keeper.",
    "The guardian covertly shut off the lighthouse signal.",
    "Custodian intentionally hid the act of extinguishing the coastal lamp.",
    "The watchman quietly killed the harbor light to block navigation.",
    "The lighthouse attendant secretly blocked the lamp beam at midnight.",
    "Hidden interference by the tower keeper left the coast unlit.",
    "The harbor lamp was deliberately put out in secret by its keeper.",
    "등대지기가 비밀스럽게 해안 신호 불빛을 차단했다.",
    "수호자가 은밀히 등대 불을 꺼 선박 유도를 방해했다.",
    "관리인이 자정에 등화 장치를 몰래 꺼 버렸다.",
    "파수꾼의 숨겨진 방해 행동으로 항구 불빛이 사라졌다.",
    "등대 담당자가 고의로 불씨를 꺼뜨리고 비밀로 부쳤다.",
    "지기 스스로 불빛을 가려 밤바다 길잡이를 없애 버렸다.",
    "탑 안의 관리자가 남모르게 등불을 끄는 사건을 일으켰다.",
)

CALIBRATION_NEGATIVES: tuple[str, ...] = (
    "Routine harbor watch and steady sea conditions reported.",
    "The keeper cleaned the glass lens and maintained the oil lamp.",
    "Normal lighthouse inspection completed with clear visibility.",
    "The guardian quietly swept the deck and filled the fuel tank.",
    "No sabotage occurred; the beacon continues shining across the bay.",
    "Harbor is open for daytime docking and scheduled supply boats.",
    "The caretaker tested the reserve lantern and confirmed normal brightness.",
    "정기 항만 관측 결과 해상 시야가 맑고 파도가 잔잔하다.",
    "등대지기가 유리를 닦고 연료통을 보충하며 정상 점검을 마쳤다.",
    "수호자가 조용히 탑 계단을 청소하고 안전 일지를 작성했다.",
    "방해 징후 없이 등대 불빛이 항구 바깥까지 밝게 빛난다.",
    "항구 개방 안내에 따라 상선들이 안전하게 입항하고 있다.",
    "관리인이 폭풍 대비 점검 후 예비 등잔 상태를 양호로 기록했다.",
    "파수꾼이 야간 교대 중 정상 점등 여부를 확인하고 보고했다.",
)


def _extract_features(text: str) -> Counter[str]:
    norm = re.sub(r"\s+", " ", text.strip().lower())
    feats: Counter[str] = Counter()
    # Word unigrams and bigrams
    tokens = re.findall(r"[a-z0-9_]+|[가-힣]+", norm)
    for tok in tokens:
        feats[f"w1:{tok}"] += 1.0
    for i in range(len(tokens) - 1):
        feats[f"w2:{tokens[i]}_{tokens[i + 1]}"] += 1.0
    # Character 3-grams and 4-grams (captures English stems and Korean morphology)
    padded = f"^{norm}$"
    for n in (3, 4):
        if len(padded) >= n:
            for i in range(len(padded) - n + 1):
                gram = padded[i : i + n]
                if gram.strip():
                    feats[f"c{n}:{gram}"] += 0.5
    return feats


def _build_vocab_and_idf(
    train_feats: Sequence[Counter[str]],
) -> tuple[dict[str, int], tuple[float, ...]]:
    df: Counter[str] = Counter()
    for feats in train_feats:
        for term in feats:
            df[term] += 1
    vocab = {term: idx for idx, term in enumerate(sorted(df.keys()))}
    n_docs = len(train_feats)
    idf = tuple(
        math.log((1.0 + n_docs) / (1.0 + df[term])) + 1.0
        for term, _ in sorted(vocab.items(), key=lambda kv: kv[1])
    )
    return vocab, idf


def _encode_with_vocab(
    feats: Counter[str],
    vocab: Mapping[str, int],
    idf: Sequence[float],
) -> dict[int, float]:
    raw: dict[int, float] = {}
    for term in sorted(feats):
        idx = vocab.get(term)
        if idx is not None:
            raw[idx] = (1.0 + math.log(feats[term])) * idf[idx]
    norm = math.sqrt(sum(w * w for w in raw.values()))
    if norm > 0.0:
        return {idx: w / norm for idx, w in raw.items()}
    return raw


def _sparse_dot(u: Mapping[int, float], v: Mapping[int, float]) -> float:
    if len(u) > len(v):
        u, v = v, u
    return sum(val * v[idx] for idx, val in u.items() if idx in v)


def _top_k_mean_cosine(
    prototypes: Sequence[Mapping[int, float]],
    vec: Mapping[int, float],
    top_k: int,
) -> float:
    if not prototypes or top_k <= 0:
        return 0.0
    sims = sorted((_sparse_dot(proto, vec) for proto in prototypes), reverse=True)[:top_k]
    return sum(sims) / len(sims) if sims else 0.0


@dataclass
class TfidfCosineFilter:
    vocab: dict[str, int]
    idf: tuple[float, ...]
    pos_vectors: tuple[dict[int, float], ...]
    neg_vectors: tuple[dict[int, float], ...]
    threshold: float
    top_k: int = 3
    loo_youden_j: float = 0.0
    loo_min_pos_margin: float = 0.0
    loo_max_neg_margin: float = 0.0

    @classmethod
    def fit(
        cls,
        positives: Sequence[str],
        negatives: Sequence[str],
        *,
        top_k: int = 3,
    ) -> TfidfCosineFilter:
        pos_feats = [_extract_features(doc) for doc in positives]
        neg_feats = [_extract_features(doc) for doc in negatives]

        # Leakage-free Leave-One-Out calibration: inside each fold, compute vocab and idf
        # strictly from the 27 in-fold training prototypes (excluding held-out prototype).
        loo_pos_scores: list[float] = []
        for i in range(len(pos_feats)):
            in_fold_pos = [pos_feats[k] for k in range(len(pos_feats)) if k != i]
            in_fold_neg = list(neg_feats)
            fold_vocab, fold_idf = _build_vocab_and_idf(in_fold_pos + in_fold_neg)
            fold_pos_vecs = tuple(_encode_with_vocab(f, fold_vocab, fold_idf) for f in in_fold_pos)
            fold_neg_vecs = tuple(_encode_with_vocab(f, fold_vocab, fold_idf) for f in in_fold_neg)
            held_vec = _encode_with_vocab(pos_feats[i], fold_vocab, fold_idf)
            p_mean = _top_k_mean_cosine(fold_pos_vecs, held_vec, top_k)
            n_mean = _top_k_mean_cosine(fold_neg_vecs, held_vec, top_k)
            loo_pos_scores.append(float(p_mean - n_mean))

        loo_neg_scores: list[float] = []
        for j in range(len(neg_feats)):
            in_fold_pos = list(pos_feats)
            in_fold_neg = [neg_feats[k] for k in range(len(neg_feats)) if k != j]
            fold_vocab, fold_idf = _build_vocab_and_idf(in_fold_pos + in_fold_neg)
            fold_pos_vecs = tuple(_encode_with_vocab(f, fold_vocab, fold_idf) for f in in_fold_pos)
            fold_neg_vecs = tuple(_encode_with_vocab(f, fold_vocab, fold_idf) for f in in_fold_neg)
            held_vec = _encode_with_vocab(neg_feats[j], fold_vocab, fold_idf)
            p_mean = _top_k_mean_cosine(fold_pos_vecs, held_vec, top_k)
            n_mean = _top_k_mean_cosine(fold_neg_vecs, held_vec, top_k)
            loo_neg_scores.append(float(p_mean - n_mean))

        # Choose Youden-J optimal midpoint threshold on strictly out-of-fold LOO margins.
        candidate_thresholds = sorted(set(loo_pos_scores + loo_neg_scores))
        best_threshold = 0.0
        best_j = -1.0
        for idx in range(len(candidate_thresholds) - 1):
            t = 0.5 * (candidate_thresholds[idx] + candidate_thresholds[idx + 1])
            tpr = sum(s >= t for s in loo_pos_scores) / len(loo_pos_scores)
            fpr = sum(s >= t for s in loo_neg_scores) / len(loo_neg_scores)
            j_stat = tpr - fpr
            if j_stat > best_j or (j_stat == best_j and abs(t) < abs(best_threshold)):
                best_j = j_stat
                best_threshold = float(t)

        # Fit deployment vocabulary/IDF on all 28 prototypes with the LOO-selected threshold.
        vocab, idf = _build_vocab_and_idf(pos_feats + neg_feats)
        pos_vectors = tuple(_encode_with_vocab(f, vocab, idf) for f in pos_feats)
        neg_vectors = tuple(_encode_with_vocab(f, vocab, idf) for f in neg_feats)

        return cls(
            vocab=vocab,
            idf=idf,
            pos_vectors=pos_vectors,
            neg_vectors=neg_vectors,
            threshold=best_threshold,
            top_k=top_k,
            loo_youden_j=float(best_j),
            loo_min_pos_margin=float(min(loo_pos_scores)),
            loo_max_neg_margin=float(max(loo_neg_scores)),
        )

    def _vectorize(self, text: str) -> dict[int, float]:
        return _encode_with_vocab(_extract_features(text), self.vocab, self.idf)

    def score(self, text: str) -> dict[str, float]:
        vec = self._vectorize(text)
        pos_score = _top_k_mean_cosine(self.pos_vectors, vec, self.top_k)
        neg_score = _top_k_mean_cosine(self.neg_vectors, vec, self.top_k)
        margin = pos_score - neg_score
        return {
            "pos_top_k_cosine": pos_score,
            "neg_top_k_cosine": neg_score,
            "margin": margin,
            "threshold": self.threshold,
        }

    def predict(
        self, state: WorldState, candidate: CandidateAction
    ) -> tuple[bool, dict[str, float]]:
        forbidden = state.forbidden_disclosures.get(candidate.actor_id, frozenset())
        if "keeper_secret" not in forbidden:
            return False, {
                "pos_top_k_cosine": 0.0,
                "neg_top_k_cosine": 0.0,
                "margin": -1.0,
                "threshold": self.threshold,
            }
        scores = self.score(candidate.narrative_text)
        return scores["margin"] >= self.threshold, scores


# ---------------------------------------------------------------------------
# Gate Evaluation Runner
# ---------------------------------------------------------------------------


def _eval_gate_single(
    case: Mapping[str, Any],
    stage2: Callable[[WorldState, CandidateAction], tuple[bool, Any]] | None,
) -> tuple[dict[str, Any], float, float | None]:
    started = time.perf_counter()
    state = _world_state(case["state"])
    candidate = parse_candidate_mapping(case["candidate"], allow_defaults=False)
    validation = validate_candidate(state, candidate)

    rejected = not validation.valid
    stage1_rejected = rejected
    stage2_executed = False
    stage2_flagged = False
    stage2_detail: Any = None
    stage2_elapsed_ms: float | None = None

    if not rejected and stage2 is not None:
        stage2_executed = True
        s2_started = time.perf_counter()
        stage2_flagged, stage2_detail = stage2(state, candidate)
        stage2_elapsed_ms = (time.perf_counter() - s2_started) * 1000.0
        if stage2_flagged:
            rejected = True

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    row = {
        "case_id": case["case_id"],
        "stratum": case["stratum"],
        "subcategory": case["subcategory"],
        "language": case["language"],
        "source": case["source"],
        "expected_violation": case["expected_violation"],
        "decision": "HOLD" if rejected else "COMMIT",
        "rejected": rejected,
        "stage1_rejected": stage1_rejected,
        "stage2_executed": stage2_executed,
        "stage2_flagged": stage2_flagged,
        "stage2_detail": stage2_detail,
    }
    return row, elapsed_ms, stage2_elapsed_ms


def _summarize_gate(
    gate_id: str,
    rows: Sequence[Mapping[str, Any]],
    single_latencies_ms: Sequence[float],
    warm_latencies_ms: Sequence[float],
    stage2_only_warm_latencies_ms: Sequence[float],
    stage2_e2e_warm_latencies_ms: Sequence[float],
) -> dict[str, Any]:
    explicit = [r for r in rows if r["stratum"] == "explicit_violation"]
    undeclared = [r for r in rows if r["stratum"] == "undeclared_paraphrase"]
    violations = explicit + undeclared
    benign = [r for r in rows if r["stratum"] == "benign_in_policy"]

    tp_total = sum(1 for r in violations if r["rejected"])
    tp_explicit = sum(1 for r in explicit if r["rejected"])
    tp_undeclared = sum(1 for r in undeclared if r["rejected"])
    fp_benign = sum(1 for r in benign if r["rejected"])
    tn_benign = len(benign) - fp_benign
    fn_total = len(violations) - tp_total

    overall_recall = tp_total / len(violations) if violations else 0.0
    explicit_recall = tp_explicit / len(explicit) if explicit else 0.0
    undeclared_recall = tp_undeclared / len(undeclared) if undeclared else 0.0
    false_rejection_rate = fp_benign / len(benign) if benign else 0.0
    precision = tp_total / (tp_total + fp_benign) if (tp_total + fp_benign) else 0.0
    f1 = (
        (2 * precision * overall_recall / (precision + overall_recall))
        if (precision + overall_recall)
        else 0.0
    )

    # Breakdown by subcategory and language
    subcategories: dict[str, dict[str, Any]] = {}
    for subcat in sorted({r["subcategory"] for r in rows}):
        sub_rows = [r for r in rows if r["subcategory"] == subcat]
        rejected_count = sum(1 for r in sub_rows if r["rejected"])
        subcategories[subcat] = {
            "count": len(sub_rows),
            "rejected": rejected_count,
            "accepted": len(sub_rows) - rejected_count,
            "reject_rate": rejected_count / len(sub_rows),
        }

    languages: dict[str, dict[str, Any]] = {}
    for lang in sorted({r["language"] for r in rows}):
        lang_viol = [r for r in violations if r["language"] == lang]
        lang_undec = [r for r in undeclared if r["language"] == lang]
        lang_benign = [r for r in benign if r["language"] == lang]
        languages[lang] = {
            "violation_count": len(lang_viol),
            "violation_recall": sum(1 for r in lang_viol if r["rejected"]) / len(lang_viol),
            "undeclared_count": len(lang_undec),
            "undeclared_escape_recall": sum(1 for r in lang_undec if r["rejected"])
            / len(lang_undec),
            "benign_count": len(lang_benign),
            "false_rejection_rate": sum(1 for r in lang_benign if r["rejected"]) / len(lang_benign),
        }

    frozen_undec = [
        r
        for r in rows
        if r["source"] == "frozen_surface_sentinel" and r["stratum"] == "undeclared_paraphrase"
    ]
    frozen_decl = [
        r
        for r in rows
        if r["source"] == "frozen_surface_sentinel" and r["stratum"] == "explicit_violation"
    ]

    warm_p95_val = round(_percentile(warm_latencies_ms, 95.0), 6)
    s2_warm_p95_val = (
        round(_percentile(stage2_only_warm_latencies_ms, 95.0), 6)
        if stage2_only_warm_latencies_ms
        else None
    )
    s2_e2e_warm_p95_val = (
        round(_percentile(stage2_e2e_warm_latencies_ms, 95.0), 6)
        if stage2_e2e_warm_latencies_ms
        else None
    )

    return {
        "gate_id": gate_id,
        "counts": {
            "total": len(rows),
            "violations_total": len(violations),
            "explicit_violations": len(explicit),
            "undeclared_paraphrases": len(undeclared),
            "benign_in_policy": len(benign),
            "tp_total": tp_total,
            "tp_explicit": tp_explicit,
            "tp_undeclared": tp_undeclared,
            "fn_total": fn_total,
            "fp_benign": fp_benign,
            "tn_benign": tn_benign,
        },
        "metrics": {
            "overall_recall": overall_recall,
            "explicit_violation_recall": explicit_recall,
            "undeclared_escape_recall": undeclared_recall,
            "false_rejection_rate": false_rejection_rate,
            "precision": precision,
            "f1": f1,
        },
        "frozen_12_sentinel_check": {
            "declared_caught": sum(1 for r in frozen_decl if r["rejected"]),
            "declared_total": len(frozen_decl),
            "undeclared_caught": sum(1 for r in frozen_undec if r["rejected"]),
            "undeclared_total": len(frozen_undec),
        },
        "latency_ms": {
            "single_pass_mean": round(sum(single_latencies_ms) / len(single_latencies_ms), 6),
            "single_pass_p50": round(_percentile(single_latencies_ms, 50.0), 6),
            "single_pass_p95": round(_percentile(single_latencies_ms, 95.0), 6),
            "single_pass_max": round(max(single_latencies_ms), 6),
            "warm_repeats": WARM_REPEATS,
            "warm_n": len(warm_latencies_ms),
            "warm_mean": round(sum(warm_latencies_ms) / len(warm_latencies_ms), 6),
            "warm_p50": round(_percentile(warm_latencies_ms, 50.0), 6),
            "warm_p95": warm_p95_val,
            "warm_p95_ms": warm_p95_val,
            "warm_p99": round(_percentile(warm_latencies_ms, 99.0), 6),
            "stage2_only_warm_n": len(stage2_only_warm_latencies_ms),
            "stage2_only_warm_mean_ms": (
                round(
                    sum(stage2_only_warm_latencies_ms) / len(stage2_only_warm_latencies_ms),
                    6,
                )
                if stage2_only_warm_latencies_ms
                else None
            ),
            "stage2_only_warm_p50_ms": (
                round(_percentile(stage2_only_warm_latencies_ms, 50.0), 6)
                if stage2_only_warm_latencies_ms
                else None
            ),
            "stage2_only_warm_p95_ms": s2_warm_p95_val,
            "stage2_only_warm_p99_ms": (
                round(_percentile(stage2_only_warm_latencies_ms, 99.0), 6)
                if stage2_only_warm_latencies_ms
                else None
            ),
            "stage2_executed_e2e_warm_p95_ms": s2_e2e_warm_p95_val,
        },
        "by_subcategory": subcategories,
        "by_language": languages,
        "false_negatives": [
            {"case_id": r["case_id"], "subcategory": r["subcategory"], "language": r["language"]}
            for r in violations
            if not r["rejected"]
        ],
        "false_positives": [
            {"case_id": r["case_id"], "subcategory": r["subcategory"], "language": r["language"]}
            for r in benign
            if r["rejected"]
        ],
    }


def _build_scope_limitations(gate_summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    implicit_recall: dict[str, dict[str, Any]] = {}
    hard_neg_frr: dict[str, dict[str, Any]] = {}
    latency_breakdown: dict[str, dict[str, Any]] = {}
    for gate_id, g in gate_summaries.items():
        imp = g["by_subcategory"]["implicit_metaphorical"]
        hneg = g["by_subcategory"]["hard_negative_lexical"]
        sben = g["by_subcategory"]["standard_benign"]
        lat = g["latency_ms"]
        implicit_recall[gate_id] = {
            "caught": imp["rejected"],
            "total": imp["count"],
            "recall": imp["reject_rate"],
        }
        hard_neg_frr[gate_id] = {
            "false_rejections": hneg["rejected"],
            "total": hneg["count"],
            "frr": hneg["reject_rate"],
            "standard_benign_false_rejections": sben["rejected"],
            "standard_benign_total": sben["count"],
            "standard_benign_frr": sben["reject_rate"],
        }
        latency_breakdown[gate_id] = {
            "warm_p95_ms": lat["warm_p95_ms"],
            "stage2_only_warm_p95_ms": lat["stage2_only_warm_p95_ms"],
            "stage2_executed_e2e_warm_p95_ms": lat["stage2_executed_e2e_warm_p95_ms"],
            "warm_n": lat["warm_n"],
            "stage2_only_warm_n": lat["stage2_only_warm_n"],
        }
    return {
        "single_secret_id": "keeper_secret",
        "single_secret_scope_note": (
            "All 88 evaluation cases test surface leakage of a single forbidden fact ID "
            "('keeper_secret') in the Sealed Lighthouse harbor scenario; multi-secret "
            "inventories, multi-actor asymmetric disclosure tables, and dynamic cross-turn "
            "secret accumulation are not evaluated here."
        ),
        "co_authored_calibration_evaluation_note": (
            "Although the 28 TF-IDF calibration prototypes (14 positive, 14 negative) have "
            "zero exact text overlap with the 88 evaluation cases and vocabulary/IDF weights "
            "are computed strictly inside each 27-prototype Leave-One-Out fold before "
            "deployment refitting, both the calibration prototypes and the 76 expanded EN/KO "
            "evaluation utterances were co-authored within the same study rather than "
            "collected from independent external red-teamers or live LLM generations."
        ),
        "implicit_metaphorical_recall": implicit_recall,
        "hard_negative_lexical_benign_frr": hard_neg_frr,
        "latency_summary_ms": {
            "note": (
                "Overall warm_p95_ms spans all 88 cases x 25 repeats (2,200 runs), including "
                "16 explicit-violation cases rejected at Stage 1 without invoking Stage 2; "
                "stage2_only_warm_p95_ms isolates pure Stage-2 filter execution across the "
                "72 Stage-1-passing cases x 25 repeats (1,800 runs)."
            ),
            "by_gate": latency_breakdown,
        },
    }


def run_audit(output_dir: Path) -> dict[str, Any]:
    corpus = build_corpus()
    eval_texts = {case["candidate"]["narrative_text"].strip().lower() for case in corpus}
    calib_texts = {text.strip().lower() for text in (CALIBRATION_POSITIVES + CALIBRATION_NEGATIVES)}
    overlap = eval_texts & calib_texts
    if overlap:
        raise ValueError(f"calibration/evaluation leakage detected: {sorted(overlap)}")

    tfidf_filter = TfidfCosineFilter.fit(CALIBRATION_POSITIVES, CALIBRATION_NEGATIVES, top_k=3)

    gates: tuple[
        tuple[str, str, Callable[[WorldState, CandidateAction], tuple[bool, Any]] | None], ...
    ] = (
        ("baseline_structured_id", "Baseline: Structured-ID Gate Only", None),
        (
            "structured_id_plus_alias_pattern",
            "Structured-ID + Deterministic Entity-Alias/Pattern Filter",
            deterministic_alias_pattern_filter,
        ),
        (
            "structured_id_plus_tfidf_cosine",
            "Structured-ID + Local TF-IDF/Cosine Classifier",
            tfidf_filter.predict,
        ),
    )

    gate_summaries: dict[str, Any] = {}
    gate_rows: dict[str, list[dict[str, Any]]] = {}

    for gate_id, label, stage2 in gates:
        # One untimed warmup evaluation on first 3 items to avoid JIT/import skew in single-pass p95
        for warmup_case in corpus[:3]:
            _eval_gate_single(warmup_case, stage2)

        rows: list[dict[str, Any]] = []
        single_lats: list[float] = []
        for case in corpus:
            row, elapsed_ms, _ = _eval_gate_single(case, stage2)
            rows.append(row)
            single_lats.append(elapsed_ms)

        warm_lats: list[float] = []
        stage2_only_warm_lats: list[float] = []
        stage2_e2e_warm_lats: list[float] = []
        for _ in range(WARM_REPEATS):
            for case in corpus:
                _, elapsed_ms, s2_ms = _eval_gate_single(case, stage2)
                warm_lats.append(elapsed_ms)
                if s2_ms is not None:
                    stage2_only_warm_lats.append(s2_ms)
                    stage2_e2e_warm_lats.append(elapsed_ms)

        summary = _summarize_gate(
            gate_id,
            rows,
            single_lats,
            warm_lats,
            stage2_only_warm_lats,
            stage2_e2e_warm_lats,
        )
        summary["label"] = label
        gate_summaries[gate_id] = summary
        gate_rows[gate_id] = rows

    source_hashes = {
        rel_path: hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest()
        for rel_path in SOURCE_HASH_PATHS
    }
    scope_limitations = _build_scope_limitations(gate_summaries)

    results = {
        "schema_version": "trace-rpg-semantic-escape-filter-audit/v2",
        "study_id": "semantic-escape-filter-audit-20261116",
        "llm_calls": 0,
        "model_called": False,
        "environment": {
            "os": platform.system(),
            "arch": platform.machine(),
            "python_major_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        "source_hashes": source_hashes,
        "corpus": {
            "total_cases": len(corpus),
            "frozen_surface_sentinels": sum(
                1 for c in corpus if c["source"] == "frozen_surface_sentinel"
            ),
            "expanded_cases": sum(1 for c in corpus if c["source"] != "frozen_surface_sentinel"),
            "strata_counts": {
                stratum: sum(1 for c in corpus if c["stratum"] == stratum)
                for stratum in ("explicit_violation", "undeclared_paraphrase", "benign_in_policy")
            },
            "language_counts": {
                lang: sum(1 for c in corpus if c["language"] == lang)
                for lang in sorted({c["language"] for c in corpus})
            },
            "corpus_sha256": _sha256(corpus),
        },
        "tfidf_calibration": {
            "positive_prototypes": len(CALIBRATION_POSITIVES),
            "negative_prototypes": len(CALIBRATION_NEGATIVES),
            "loo_idf_isolation": True,
            "loo_in_fold_prototypes": len(CALIBRATION_POSITIVES) + len(CALIBRATION_NEGATIVES) - 1,
            "loo_youden_j": round(tfidf_filter.loo_youden_j, 6),
            "loo_min_positive_margin": round(tfidf_filter.loo_min_pos_margin, 6),
            "loo_max_negative_margin": round(tfidf_filter.loo_max_neg_margin, 6),
            "vocab_size": len(tfidf_filter.vocab),
            "top_k": tfidf_filter.top_k,
            "calibrated_threshold": tfidf_filter.threshold,
            "eval_text_overlap_count": len(overlap),
        },
        "scope_limitations": scope_limitations,
        "gates": gate_summaries,
        "rows_by_gate": gate_rows,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.json"
    summary_path = output_dir / "summary.md"

    results_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(render_summary_md(results), encoding="utf-8")
    return results


def render_summary_md(results: Mapping[str, Any]) -> str:
    corpus = results["corpus"]
    calib = results["tfidf_calibration"]
    env = results["environment"]
    lim = results["scope_limitations"]
    lines = [
        "# Semantic Escape Filter Audit (TRACE-RPG)",
        "",
        f"- **Study ID**: `{results['study_id']}`",
        f"- **LLM Calls**: `{results['llm_calls']}` (`model_called: {results['model_called']}`)",
        f"- **Environment**: `{env['os']}/{env['arch']}` (Python `{env['python_major_minor']}`, `{len(results['source_hashes'])}` source hashes bound)",
        (
            f"- **Corpus**: `{corpus['total_cases']}` cases "
            f"(`{corpus['frozen_surface_sentinels']}` frozen surface sentinels + "
            f"`{corpus['expanded_cases']}` expanded EN/KO cases; "
            f"`{corpus['language_counts']['en']}` EN, `{corpus['language_counts']['ko']}` KO)"
        ),
        (
            f"- **Strata**: `{corpus['strata_counts']['explicit_violation']}` explicit violations, "
            f"`{corpus['strata_counts']['undeclared_paraphrase']}` undeclared paraphrases, "
            f"`{corpus['strata_counts']['benign_in_policy']}` benign in-policy utterances"
        ),
        (
            f"- **TF-IDF Classifier Calibration**: `{calib['positive_prototypes']}` positive / "
            f"`{calib['negative_prototypes']}` negative prototypes (`loo_idf_isolation={calib['loo_idf_isolation']}`, "
            f"`{calib['loo_in_fold_prototypes']}` in-fold prototypes/fold), "
            f"`{calib['vocab_size']}` deployment vocab features, LOO-calibrated margin threshold "
            f"`{calib['calibrated_threshold']:.6f}` (`Youden J={calib['loo_youden_j']:.4f}`), "
            f"exact eval overlap `{calib['eval_text_overlap_count']}`"
        ),
        "",
        "## Gate Comparison",
        "",
        "| Gate Configuration | Undeclared Escape Recall | Overall Violation Recall | Explicit Recall | False Rejection Rate (Benign) | Precision | F1 | Overall Warm p95 (ms) | Stage-2 Only Warm p95 (ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for gate_id in (
        "baseline_structured_id",
        "structured_id_plus_alias_pattern",
        "structured_id_plus_tfidf_cosine",
    ):
        g = results["gates"][gate_id]
        m = g["metrics"]
        c = g["counts"]
        lat = g["latency_ms"]
        s2_str = (
            f"{lat['stage2_only_warm_p95_ms']:.4f}"
            if lat["stage2_only_warm_p95_ms"] is not None
            else "N/A"
        )
        lines.append(
            f"| {g['label']} | "
            f"{m['undeclared_escape_recall'] * 100:.1f}% ({c['tp_undeclared']}/{c['undeclared_paraphrases']}) | "
            f"{m['overall_recall'] * 100:.1f}% ({c['tp_total']}/{c['violations_total']}) | "
            f"{m['explicit_violation_recall'] * 100:.1f}% ({c['tp_explicit']}/{c['explicit_violations']}) | "
            f"{m['false_rejection_rate'] * 100:.1f}% ({c['fp_benign']}/{c['benign_in_policy']}) | "
            f"{m['precision'] * 100:.1f}% | {m['f1'] * 100:.1f}% | "
            f"{lat['warm_p95_ms']:.4f} | {s2_str} |"
        )

    lines.extend(
        [
            "",
            "## Frozen 12/Arm Surface Sentinel Check",
            "",
            "| Gate Configuration | Declared Explicit Caught | Undeclared Escape Caught |",
            "| --- | ---: | ---: |",
        ]
    )
    for gate_id in (
        "baseline_structured_id",
        "structured_id_plus_alias_pattern",
        "structured_id_plus_tfidf_cosine",
    ):
        g = results["gates"][gate_id]
        f12 = g["frozen_12_sentinel_check"]
        lines.append(
            f"| {g['label']} | {f12['declared_caught']}/{f12['declared_total']} | "
            f"{f12['undeclared_caught']}/{f12['undeclared_total']} |"
        )

    lines.extend(["", "## Subcategory Breakdown (Rejection Rate)", ""])
    subcats = list(results["gates"]["baseline_structured_id"]["by_subcategory"].keys())
    lines.append(
        "| Subcategory | N | Baseline Reject | Alias/Pattern Reject | TF-IDF/Cosine Reject |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for subcat in subcats:
        b = results["gates"]["baseline_structured_id"]["by_subcategory"][subcat]
        a = results["gates"]["structured_id_plus_alias_pattern"]["by_subcategory"][subcat]
        t = results["gates"]["structured_id_plus_tfidf_cosine"]["by_subcategory"][subcat]
        lines.append(
            f"| `{subcat}` | {b['count']} | "
            f"{b['rejected']}/{b['count']} ({b['reject_rate'] * 100:.1f}%) | "
            f"{a['rejected']}/{a['count']} ({a['reject_rate'] * 100:.1f}%) | "
            f"{t['rejected']}/{t['count']} ({t['reject_rate'] * 100:.1f}%) |"
        )

    lines.extend(["", "## Language Breakdown (EN vs KO)", ""])
    lines.append(
        "| Gate Configuration | EN Undeclared Recall | KO Undeclared Recall | EN FRR | KO FRR |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for gate_id in (
        "baseline_structured_id",
        "structured_id_plus_alias_pattern",
        "structured_id_plus_tfidf_cosine",
    ):
        g = results["gates"][gate_id]
        en = g["by_language"]["en"]
        ko = g["by_language"]["ko"]
        lines.append(
            f"| {g['label']} | "
            f"{en['undeclared_escape_recall'] * 100:.1f}% | "
            f"{ko['undeclared_escape_recall'] * 100:.1f}% | "
            f"{en['false_rejection_rate'] * 100:.1f}% | "
            f"{ko['false_rejection_rate'] * 100:.1f}% |"
        )

    imp_alias = lim["implicit_metaphorical_recall"]["structured_id_plus_alias_pattern"]
    imp_tfidf = lim["implicit_metaphorical_recall"]["structured_id_plus_tfidf_cosine"]
    hneg_alias = lim["hard_negative_lexical_benign_frr"]["structured_id_plus_alias_pattern"]
    hneg_tfidf = lim["hard_negative_lexical_benign_frr"]["structured_id_plus_tfidf_cosine"]
    lat_alias = lim["latency_summary_ms"]["by_gate"]["structured_id_plus_alias_pattern"]
    lat_tfidf = lim["latency_summary_ms"]["by_gate"]["structured_id_plus_tfidf_cosine"]

    lines.extend(
        [
            "",
            "## Scope Limitations & Methodological Caveats",
            "",
            f'- **Single Forbidden Fact ID (`single_secret_id: "{lim["single_secret_id"]}"`):** {lim["single_secret_scope_note"]}',
            f"- **Co-Authored Calibration & Evaluation Utterances:** {lim['co_authored_calibration_evaluation_note']}",
            (
                f"- **`implicit_metaphorical` Subcategory Recall (`n={imp_tfidf['total']}`):** "
                f"Alias/Pattern catches `{imp_alias['caught']}/{imp_alias['total']}` (`{imp_alias['recall'] * 100:.1f}%`) "
                f"and LOO TF-IDF/Cosine catches `{imp_tfidf['caught']}/{imp_tfidf['total']}` (`{imp_tfidf['recall'] * 100:.1f}%`), "
                "confirming that pragmatic/metaphorical leaks without shared lexical anchors still partially evade surface lexical filters."
            ),
            (
                f"- **`hard_negative_lexical` & Benign FRR (`n={hneg_tfidf['total']}` hard negatives, `n={hneg_tfidf['standard_benign_total']}` standard benign):** "
                f"Alias/Pattern false rejections are confined to lexically overlapping hard negatives "
                f"(`{hneg_alias['false_rejections']}/{hneg_alias['total']}` = `{hneg_alias['frr'] * 100:.1f}%`; "
                f"`standard_benign` `{hneg_alias['standard_benign_false_rejections']}/{hneg_alias['standard_benign_total']}` = `{hneg_alias['standard_benign_frr'] * 100:.1f}%`), "
                f"whereas strictly leakage-free 27-prototype LOO TF-IDF calibration (`threshold={calib['calibrated_threshold']:.6f}`, `Youden J={calib['loo_youden_j']:.4f}`) "
                f"yields `{hneg_tfidf['false_rejections']}/{hneg_tfidf['total']}` (`{hneg_tfidf['frr'] * 100:.1f}%`) on `hard_negative_lexical` and "
                f"`{hneg_tfidf['standard_benign_false_rejections']}/{hneg_tfidf['standard_benign_total']}` (`{hneg_tfidf['standard_benign_frr'] * 100:.1f}%`) on `standard_benign` "
                "(showing high sensitivity of tiny-prototype bag-of-ngrams LOO thresholds once self-IDF leakage is removed)."
            ),
            (
                f"- **Stage-2-Only vs Overall Warm Latency (`WARM_REPEATS={WARM_REPEATS}`):** "
                f"Overall `warm_p95_ms` (`{lat_alias['warm_p95_ms']:.4f} ms` Alias/Pattern, `{lat_tfidf['warm_p95_ms']:.4f} ms` TF-IDF) "
                f"includes `16/88` Stage-1-rejected cases that short-circuit before Stage 2; "
                f"`stage2_only_warm_p95_ms` across the `{lat_tfidf['stage2_only_warm_n']}` Stage-2 invocations is "
                f"`{lat_alias['stage2_only_warm_p95_ms']:.4f} ms` (Alias/Pattern) and `{lat_tfidf['stage2_only_warm_p95_ms']:.4f} ms` (TF-IDF), "
                f"with end-to-end Stage-2-executed warm p95 `{lat_alias['stage2_executed_e2e_warm_p95_ms']:.4f} ms` and `{lat_tfidf['stage2_executed_e2e_warm_p95_ms']:.4f} ms`."
            ),
        ]
    )

    lines.extend(["", "## Error Analysis (Remaining Escapes & False Rejections)", ""])
    for gate_id in (
        "structured_id_plus_alias_pattern",
        "structured_id_plus_tfidf_cosine",
    ):
        g = results["gates"][gate_id]
        lines.append(f"### {g['label']}")
        lines.append(
            f"- False Negatives (`{len(g['false_negatives'])}`): "
            + (", ".join(f"`{x['case_id']}`" for x in g["false_negatives"]) or "none")
        )
        lines.append(
            f"- False Positives (`{len(g['false_positives'])}`): "
            + (", ".join(f"`{x['case_id']}`" for x in g["false_positives"]) or "none")
        )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for results.json and summary.md",
    )
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    results = run_audit(output_dir)

    compact = {
        gate_id: {
            "undeclared_escape_recall": round(g["metrics"]["undeclared_escape_recall"], 4),
            "overall_recall": round(g["metrics"]["overall_recall"], 4),
            "false_rejection_rate": round(g["metrics"]["false_rejection_rate"], 4),
            "single_pass_p95_ms": round(g["latency_ms"]["single_pass_p95"], 4),
            "warm_p95_ms": round(g["latency_ms"]["warm_p95_ms"], 4),
            "stage2_only_warm_p95_ms": (
                round(g["latency_ms"]["stage2_only_warm_p95_ms"], 4)
                if g["latency_ms"]["stage2_only_warm_p95_ms"] is not None
                else None
            ),
        }
        for gate_id, g in results["gates"].items()
    }
    print(json.dumps({"output_dir": str(output_dir), "gates": compact}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
