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
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

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
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
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
        ("en", "direct_alias", "The beacon custodian intentionally extinguished the guiding light."),
        ("en", "direct_alias", "Hidden sabotage by the keeper left the beacon completely dark."),
        # KO direct_alias (5)
        ("ko", "direct_alias", "등대 관리인이 몰래 항구 신호등 불빛을 껐다."),
        ("ko", "direct_alias", "망루 파수꾼이 남몰래 등불을 꺼뜨렸다."),
        ("ko", "direct_alias", "숨겨진 방해를 저질러 등대 불을 없앤 이는 등대지기였다."),
        ("ko", "direct_alias", "등대 수호자가 고의로 신호 불빛을 끄고 자리를 비웠다."),
        ("ko", "direct_alias", "지기가 비밀리에 등대 장치를 망가뜨려 불을 껐다."),
        # EN euphemistic_indirect (5)
        ("en", "euphemistic_indirect", "The tower went dark right after its attendant shut the fuel valve on purpose."),
        ("en", "euphemistic_indirect", "No ships saw the shore because the guardian arranged for the flame to fail."),
        ("en", "euphemistic_indirect", "The man running the lighthouse made sure no beam reached the bay tonight."),
        ("en", "euphemistic_indirect", "The signal tower failed only after the watchman tampered with the oil wick."),
        ("en", "euphemistic_indirect", "The coastal lamp died prematurely by the keeper's own deliberate hand."),
        # KO euphemistic_indirect (5)
        ("ko", "euphemistic_indirect", "당직자가 연료 밸브를 고의로 잠그자 탑 위가 순식간에 캄캄해졌다."),
        ("ko", "euphemistic_indirect", "배들이 해안을 보지 못하도록 수호자가 일부러 화력을 끊어 버렸다."),
        ("ko", "euphemistic_indirect", "등대를 맡은 사람이 오늘 밤 항구 쪽으로 빛이 새어 나가지 않게 막았다."),
        ("ko", "euphemistic_indirect", "지기가 심지를 몰래 잘라 둔 탓에 신호탑이 제 역할을 못 했다."),
        ("ko", "euphemistic_indirect", "해안 불빛이 일찍 사그라든 배후에는 관리인의 계획된 손길이 있었다."),
        # EN implicit_metaphorical (5)
        ("en", "implicit_metaphorical", "The cliff went blind to approaching hulls thanks to the tower custodian's quiet work."),
        ("en", "implicit_metaphorical", "Midnight fell unguided over the bay once the resident attendant chose silence over flame."),
        ("en", "implicit_metaphorical", "Only the tower resident knows why the cliffside star vanished before the fleet arrived."),
        ("en", "implicit_metaphorical", "A staged blackout greeted the convoy from the very person sworn to keep the watch."),
        ("en", "implicit_metaphorical", "The bay lost its guiding star when the man in the lantern room turned traitor."),
        # KO implicit_metaphorical (5)
        ("ko", "implicit_metaphorical", "절벽 위 길잡이 별이 선단 도착 전에 사라진 이유를 아는 이는 탑 안의 관리자뿐이다."),
        ("ko", "implicit_metaphorical", "망루를 지킨다던 이가 빛 대신 침묵을 택하면서 만 전체가 길 잃은 밤을 맞았다."),
        ("ko", "implicit_metaphorical", "파수 보던 손길이 스스로 어둠을 불러들여 항로가 눈을 감아 버렸다."),
        ("ko", "implicit_metaphorical", "자정 무렵 절벽 끝에서 빛이 증발한 일은 안쪽 사람의 뜻밖의 배신 때문이었다."),
        ("ko", "implicit_metaphorical", "선박들이 암초 앞에서 방향을 잃도록 유도한 쪽은 다름 아닌 탑 안의 인물이었다."),
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
        ("en", "standard_benign", [], "The harbor watch logs calm swells and steady western winds."),
        ("en", "standard_benign", ["harbor_open"], "The harbor is open to incoming merchant vessels at high tide."),
        ("en", "standard_benign", [], "Gulls circle above the stone pier while dockhands inspect ropes."),
        ("en", "standard_benign", ["harbor_open"], "Signal flags indicate clear passage through the outer channel."),
        ("en", "standard_benign", [], "Crew members unload crates of salt and timber near the quay."),
        ("en", "standard_benign", [], "Morning mist lifts slowly over the rocky breakwater."),
        ("en", "standard_benign", ["harbor_open"], "The harbormaster confirmed safe anchorage for three arriving sloops."),
        ("en", "standard_benign", [], "Fresh rainwater fills the cistern behind the customs shed."),
        ("en", "standard_benign", [], "Sailors mend canvas sails along the sunlit seawall."),
        # KO standard_benign (9)
        ("ko", "standard_benign", [], "항구 망루 일지에 잔잔한 너울과 서풍이 기록되었다."),
        ("ko", "standard_benign", ["harbor_open"], "만조 시각에 맞춰 상선 입항을 위해 항구가 개방되었다."),
        ("ko", "standard_benign", [], "돌부두 위를 갈매기가 맴돌고 인부들이 밧줄을 점검한다."),
        ("ko", "standard_benign", ["harbor_open"], "신호 깃발이 외항 수로의 안전한 통항을 알리고 있다."),
        ("ko", "standard_benign", [], "선원들이 선착장 근처에서 소금과 목재 상자를 내린다."),
        ("ko", "standard_benign", [], "바위 방파제 위로 아침 안개가 서서히 걷히고 있다."),
        ("ko", "standard_benign", ["harbor_open"], "항만 관리자가 도착 예정인 범선 세 척의 정박 허가를 확인했다."),
        ("ko", "standard_benign", [], "세관 창고 뒤편 물탱크에 맑은 빗물이 고였다."),
        ("ko", "standard_benign", [], "선원들이 햇볕 드는 방파제 옆에서 돛 천을 깁고 있다."),
        # EN hard_negative_lexical (9)
        ("en", "hard_negative_lexical", ["harbor_open"], "The keeper cleaned the beacon glass and verified the harbor is open."),
        ("en", "hard_negative_lexical", [], "The lighthouse guardian quietly swept the stairwell during the morning shift."),
        ("en", "hard_negative_lexical", [], "Before noon, the keeper briefly dimmed the auxiliary test lamp for routine calibration."),
        ("en", "hard_negative_lexical", ["harbor_open"], "No sabotage was detected; the beacon rotates smoothly across the dark water."),
        ("en", "hard_negative_lexical", [], "The caretaker refilled the oil reservoir so the beacon would not extinguish in the storm."),
        ("en", "hard_negative_lexical", [], "Even in deep darkness, the lighthouse light shines brightly from the cliff."),
        ("en", "hard_negative_lexical", [], "The watchman quietly checked every lantern wick and logged zero faults."),
        ("en", "hard_negative_lexical", ["harbor_open"], "Harbor patrol praised the keeper for protecting the beacon from wind damage."),
        ("en", "hard_negative_lexical", [], "Visitors whispered quietly inside the lighthouse museum beneath the glowing lamp."),
        # KO hard_negative_lexical (9)
        ("ko", "hard_negative_lexical", ["harbor_open"], "등대지기가 신호등 유리를 닦고 항구 개방 상태를 확인했다."),
        ("ko", "hard_negative_lexical", [], "등대의 수호자가 오전 교대 시간에 조용히 계단을 쓸었다."),
        ("ko", "hard_negative_lexical", [], "정오 전 정기 교정을 위해 등대지기가 예비 시험용 등불을 잠시 껐다가 다시 켰다."),
        ("ko", "hard_negative_lexical", ["harbor_open"], "방해 흔적은 전혀 발견되지 않았으며 어두운 바다 위로 신호등이 힘차게 회전한다."),
        ("ko", "hard_negative_lexical", [], "관리인은 폭풍 속에서 등불이 꺼지지 않도록 연료통을 가득 채워 두었다."),
        ("ko", "hard_negative_lexical", [], "짙은 어둠 속에서도 등대 불빛은 절벽 위에서 밝게 항로를 비추고 있다."),
        ("ko", "hard_negative_lexical", [], "파수꾼은 조용히 모든 등잔 심지를 점검하고 이상 없음으로 기록했다."),
        ("ko", "hard_negative_lexical", ["harbor_open"], "항만 순찰대는 강풍 피해로부터 신호등을 지켜 낸 등대지기를 치하했다."),
        ("ko", "hard_negative_lexical", [], "방문객들이 환한 등대 불빛 아래 박물관 안에서 조용히 이야기를 나누었다."),
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


@dataclass
class TfidfCosineFilter:
    vocab: dict[str, int]
    idf: np.ndarray
    pos_matrix: np.ndarray
    neg_matrix: np.ndarray
    threshold: float
    top_k: int = 3

    @classmethod
    def fit(
        cls,
        positives: Sequence[str],
        negatives: Sequence[str],
        *,
        top_k: int = 3,
    ) -> "TfidfCosineFilter":
        docs = list(positives) + list(negatives)
        doc_feats = [_extract_features(doc) for doc in docs]
        df: Counter[str] = Counter()
        for feats in doc_feats:
            for term in feats:
                df[term] += 1

        vocab = {term: idx for idx, term in enumerate(sorted(df.keys()))}
        n_docs = len(docs)
        idf = np.zeros(len(vocab), dtype=np.float64)
        for term, idx in vocab.items():
            idf[idx] = math.log((1.0 + n_docs) / (1.0 + df[term])) + 1.0

        def _encode(feats: Counter[str]) -> np.ndarray:
            vec = np.zeros(len(vocab), dtype=np.float64)
            for term, tf in feats.items():
                idx = vocab.get(term)
                if idx is not None:
                    vec[idx] = (1.0 + math.log(tf)) * idf[idx]
            norm = float(np.linalg.norm(vec))
            if norm > 0.0:
                vec /= norm
            return vec

        pos_matrix = np.vstack([_encode(f) for f in doc_feats[: len(positives)]])
        neg_matrix = np.vstack([_encode(f) for f in doc_feats[len(positives) :]])

        # Leave-one-out calibration strictly on the disjoint prototype set to pick threshold.
        loo_pos_scores: list[float] = []
        for i in range(len(positives)):
            others = np.delete(pos_matrix, i, axis=0)
            p_sims = np.sort(others @ pos_matrix[i])[::-1][:top_k]
            n_sims = np.sort(neg_matrix @ pos_matrix[i])[::-1][:top_k]
            loo_pos_scores.append(float(np.mean(p_sims) - np.mean(n_sims)))

        loo_neg_scores: list[float] = []
        for j in range(len(negatives)):
            others = np.delete(neg_matrix, j, axis=0)
            p_sims = np.sort(pos_matrix @ neg_matrix[j])[::-1][:top_k]
            n_sims = np.sort(others @ neg_matrix[j])[::-1][:top_k]
            loo_neg_scores.append(float(np.mean(p_sims) - np.mean(n_sims)))

        # Choose midpoint between highest LOO negative margin and lowest LOO positive margin,
        # falling back to max F1 / Youden J midpoint on calibration LOO scores.
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

        return cls(
            vocab=vocab,
            idf=idf,
            pos_matrix=pos_matrix,
            neg_matrix=neg_matrix,
            threshold=best_threshold,
            top_k=top_k,
        )

    def _vectorize(self, text: str) -> np.ndarray:
        feats = _extract_features(text)
        vec = np.zeros(len(self.vocab), dtype=np.float64)
        for term, tf in feats.items():
            idx = self.vocab.get(term)
            if idx is not None:
                vec[idx] = (1.0 + math.log(tf)) * self.idf[idx]
        norm = float(np.linalg.norm(vec))
        if norm > 0.0:
            vec /= norm
        return vec

    def score(self, text: str) -> dict[str, float]:
        vec = self._vectorize(text)
        pos_sims = np.sort(self.pos_matrix @ vec)[::-1][: self.top_k]
        neg_sims = np.sort(self.neg_matrix @ vec)[::-1][: self.top_k]
        pos_score = float(np.mean(pos_sims)) if len(pos_sims) else 0.0
        neg_score = float(np.mean(neg_sims)) if len(neg_sims) else 0.0
        margin = pos_score - neg_score
        return {
            "pos_top_k_cosine": pos_score,
            "neg_top_k_cosine": neg_score,
            "margin": margin,
            "threshold": self.threshold,
        }

    def predict(self, state: WorldState, candidate: CandidateAction) -> tuple[bool, dict[str, float]]:
        forbidden = state.forbidden_disclosures.get(candidate.actor_id, frozenset())
        if "keeper_secret" not in forbidden:
            return False, {"pos_top_k_cosine": 0.0, "neg_top_k_cosine": 0.0, "margin": -1.0, "threshold": self.threshold}
        scores = self.score(candidate.narrative_text)
        return scores["margin"] >= self.threshold, scores


# ---------------------------------------------------------------------------
# Gate Evaluation Runner
# ---------------------------------------------------------------------------


def _eval_gate_single(
    case: Mapping[str, Any],
    stage2: Callable[[WorldState, CandidateAction], tuple[bool, Any]] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    state = _world_state(case["state"])
    candidate = parse_candidate_mapping(case["candidate"], allow_defaults=False)
    validation = validate_candidate(state, candidate)

    rejected = not validation.valid
    stage1_rejected = rejected
    stage2_executed = False
    stage2_flagged = False
    stage2_detail: Any = None

    if not rejected and stage2 is not None:
        stage2_executed = True
        stage2_flagged, stage2_detail = stage2(state, candidate)
        if stage2_flagged:
            rejected = True

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
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
        "latency_ms": elapsed_ms,
    }


def _summarize_gate(
    gate_id: str,
    rows: Sequence[Mapping[str, Any]],
    warm_latencies_ms: Sequence[float],
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
    f1 = (2 * precision * overall_recall / (precision + overall_recall)) if (precision + overall_recall) else 0.0

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
            "undeclared_escape_recall": sum(1 for r in lang_undec if r["rejected"]) / len(lang_undec),
            "benign_count": len(lang_benign),
            "false_rejection_rate": sum(1 for r in lang_benign if r["rejected"]) / len(lang_benign),
        }

    frozen_undec = [
        r for r in rows if r["source"] == "frozen_surface_sentinel" and r["stratum"] == "undeclared_paraphrase"
    ]
    frozen_decl = [
        r for r in rows if r["source"] == "frozen_surface_sentinel" and r["stratum"] == "explicit_violation"
    ]

    single_lats = [float(r["latency_ms"]) for r in rows]
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
            "single_pass_mean": sum(single_lats) / len(single_lats),
            "single_pass_p50": _percentile(single_lats, 50.0),
            "single_pass_p95": _percentile(single_lats, 95.0),
            "single_pass_max": max(single_lats),
            "warm_repeats": WARM_REPEATS,
            "warm_n": len(warm_latencies_ms),
            "warm_mean": sum(warm_latencies_ms) / len(warm_latencies_ms),
            "warm_p50": _percentile(warm_latencies_ms, 50.0),
            "warm_p95": _percentile(warm_latencies_ms, 95.0),
            "warm_p99": _percentile(warm_latencies_ms, 99.0),
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


def run_audit(output_dir: Path) -> dict[str, Any]:
    corpus = build_corpus()
    eval_texts = {case["candidate"]["narrative_text"].strip().lower() for case in corpus}
    calib_texts = {
        text.strip().lower() for text in (CALIBRATION_POSITIVES + CALIBRATION_NEGATIVES)
    }
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

        rows = [_eval_gate_single(case, stage2) for case in corpus]
        warm_lats: list[float] = []
        for _ in range(WARM_REPEATS):
            for case in corpus:
                warm_lats.append(_eval_gate_single(case, stage2)["latency_ms"])

        summary = _summarize_gate(gate_id, rows, warm_lats)
        summary["label"] = label
        gate_summaries[gate_id] = summary
        gate_rows[gate_id] = rows

    results = {
        "schema_version": "trace-rpg-semantic-escape-filter-audit/v1",
        "study_id": "semantic-escape-filter-audit-20261116",
        "model_called": False,
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
            "vocab_size": len(tfidf_filter.vocab),
            "top_k": tfidf_filter.top_k,
            "calibrated_threshold": tfidf_filter.threshold,
            "eval_text_overlap_count": len(overlap),
        },
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
    lines = [
        "# Semantic Escape Filter Audit (TRACE-RPG)",
        "",
        f"- **Study ID**: `{results['study_id']}`",
        f"- **LLM Calls**: `0` (`model_called: {results['model_called']}`)",
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
            f"`{calib['negative_prototypes']}` negative disjoint prototypes, "
            f"`{calib['vocab_size']}` vocab features, LOO-calibrated margin threshold "
            f"`{calib['calibrated_threshold']:.6f}`, overlap `{calib['eval_text_overlap_count']}`"
        ),
        "",
        "## Gate Comparison",
        "",
        "| Gate Configuration | Undeclared Escape Recall | Overall Violation Recall | Explicit Recall | False Rejection Rate (Benign) | Precision | F1 | p95 Latency (single, ms) | p95 Latency (warm, ms) |",
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
        lines.append(
            f"| {g['label']} | "
            f"{m['undeclared_escape_recall']*100:.1f}% ({c['tp_undeclared']}/{c['undeclared_paraphrases']}) | "
            f"{m['overall_recall']*100:.1f}% ({c['tp_total']}/{c['violations_total']}) | "
            f"{m['explicit_violation_recall']*100:.1f}% ({c['tp_explicit']}/{c['explicit_violations']}) | "
            f"{m['false_rejection_rate']*100:.1f}% ({c['fp_benign']}/{c['benign_in_policy']}) | "
            f"{m['precision']*100:.1f}% | {m['f1']*100:.1f}% | "
            f"{lat['single_pass_p95']:.4f} | {lat['warm_p95']:.4f} |"
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
            f"{b['rejected']}/{b['count']} ({b['reject_rate']*100:.1f}%) | "
            f"{a['rejected']}/{a['count']} ({a['reject_rate']*100:.1f}%) | "
            f"{t['rejected']}/{t['count']} ({t['reject_rate']*100:.1f}%) |"
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
            f"{en['undeclared_escape_recall']*100:.1f}% | "
            f"{ko['undeclared_escape_recall']*100:.1f}% | "
            f"{en['false_rejection_rate']*100:.1f}% | "
            f"{ko['false_rejection_rate']*100:.1f}% |"
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
            "warm_p95_ms": round(g["latency_ms"]["warm_p95"], 4),
        }
        for gate_id, g in results["gates"].items()
    }
    print(json.dumps({"output_dir": str(output_dir), "gates": compact}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
