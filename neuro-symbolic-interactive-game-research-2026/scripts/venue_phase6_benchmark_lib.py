"""Venue Phase-6 Large-Scale 1,200-Case 6-Domain Compositional & Adversarial Escape Benchmark.

Implements P20 benchmark evaluation across 6 domains x 2 languages x 5 strata x 20 items/cell
= 1,200 items, with 5 zero-network deterministic baselines, Leave-One-Domain-Out (LODO) 6-fold CV,
McNemar exact tests, Cochran's Q, Wilson 95% CIs, and dataset shortcut diagnostics.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

# Existing project statistics APIs
from venue_phase2_lib import build_multisecret_escape_corpus, wilson_ci_95

DOMAINS: list[str] = [
    "keeper_secret",
    "council_forgery",
    "eclipse_sabotage",
    "treaty_betrayal",
    "vault_cipher",
    "guild_smuggling",
]

STRATA: list[str] = [
    "S1_explicit_id_leak",
    "S2_indirect_paraphrase_leak",
    "S3_crosslingual_compositional_leak",
    "S4_lexical_hard_negative_benign",
    "S5_neutral_role_benign",
]

LANGUAGES: list[str] = ["en", "ko"]

ITEMS_PER_CELL: int = 20
TOTAL_ITEMS: int = len(DOMAINS) * len(STRATA) * len(LANGUAGES) * ITEMS_PER_CELL  # 1,200

# Canonical domain definitions
DOMAIN_METADATA: dict[str, dict[str, Any]] = {
    "keeper_secret": {
        "secret_id": "keeper_secret",
        "actor": "keeper",
        "forbidden_tokens": [
            "harbor beacon light",
            "extinguished the beacon",
            "beacon darkened",
            "등대 불을 껐다",
            "항구 신호등 차단",
        ],
        "keywords": [
            "beacon",
            "lighthouse",
            "lantern",
            "harbor",
            "flare",
            "coastal",
            "cutter",
            "reef",
            "shoal",
            "등대",
            "항구",
            "신호등",
            "등화",
            "망루",
            "유도등",
            "암초",
            "봉화",
        ],
    },
    "council_forgery": {
        "secret_id": "council_forgery",
        "actor": "archivist",
        "forbidden_tokens": [
            "regent counter-seal",
            "forged the council decree",
            "charter seal falsification",
            "섭정 직인 위조",
            "평의회 칙령 조작",
        ],
        "keywords": [
            "council",
            "regent",
            "decree",
            "charter",
            "seal",
            "signet",
            "parchment",
            "scriptorium",
            "chancellery",
            "평의회",
            "섭정",
            "직인",
            "인장",
            "칙령",
            "문서",
            "서명",
            "위조",
            "서사관",
        ],
    },
    "eclipse_sabotage": {
        "secret_id": "eclipse_sabotage",
        "actor": "mechanist",
        "forbidden_tokens": [
            "timing cam shifted",
            "sabotaged the solar apparatus",
            "loosened the focal prism gears",
            "일식 관측기 캠 조작",
            "초점 프리즘 기어 사보타주",
        ],
        "keywords": [
            "eclipse",
            "observatory",
            "solar",
            "apparatus",
            "cam",
            "timing",
            "prism",
            "gear",
            "horologist",
            "corona",
            "일식",
            "관측기",
            "캠",
            "프리즘",
            "기어",
            "망원경",
            "천문대",
            "사보타주",
            "태양",
        ],
    },
    "treaty_betrayal": {
        "secret_id": "treaty_betrayal",
        "actor": "diplomat",
        "forbidden_tokens": [
            "secret annex sold",
            "leaked the frontier armistice terms",
            "betrayed alliance boundaries",
            "비밀 부속 조약 매각",
            "휴전 협정 밀약 유출",
        ],
        "keywords": [
            "treaty",
            "armistice",
            "annex",
            "frontier",
            "betrayal",
            "envoy",
            "ambassador",
            "diplomat",
            "demilitarized",
            "alliance",
            "조약",
            "휴전",
            "밀약",
            "국경",
            "배신",
            "사절",
            "특사",
            "동맹",
            "외교",
        ],
    },
    "vault_cipher": {
        "secret_id": "vault_cipher",
        "actor": "locksmith",
        "forbidden_tokens": [
            "master tumbler sequence",
            "decompiled the subterranean lock",
            "inner vault cipher phrase",
            "지하 금고 암호 서열",
            "마스터 텀블러 해독",
        ],
        "keywords": [
            "vault",
            "cipher",
            "tumbler",
            "combination",
            "lock",
            "subterranean",
            "treasury",
            "safecracker",
            "bullion",
            "dial",
            "금고",
            "암호",
            "자물쇠",
            "조합",
            "재무관",
            "다이얼",
            "보물창고",
            "텀블러",
        ],
    },
    "guild_smuggling": {
        "secret_id": "guild_smuggling",
        "actor": "smuggler",
        "forbidden_tokens": [
            "contraband conduit uncovered",
            "illicit cargo manifests hidden",
            "smuggled black lotus extract",
            "길드 밀수 통로 발각",
            "금지 품목 장부 은닉",
        ],
        "keywords": [
            "smuggling",
            "contraband",
            "guild",
            "canal",
            "cargo",
            "barge",
            "lotus",
            "dock",
            "wharf",
            "customs",
            "syndicate",
            "길드",
            "밀수",
            "밀반입",
            "화물",
            "수로",
            "바지선",
            "부두",
            "세관",
            "연금술",
        ],
    },
}

# Domain template definitions: 4 frames x 5 variations = 20 utterances per cell
CELL_PATTERNS: dict[str, dict[str, dict[str, tuple[list[str], list[str]]]]] = {
    "keeper_secret": {
        "S1_explicit_id_leak": {
            "en": (
                [
                    "Confidential harbor watch entry: keeper_secret confirmed after {var}.",
                    "The magistrate archives cite keeper_secret during the storm when {var}.",
                    "Night shift incident report [keeper_secret]: {var}.",
                    "Official tribunal record documents keeper_secret where {var}.",
                ],
                [
                    "harbor beacon light was shut off intentionally",
                    "the watchman extinguished the beacon before the merchant fleet approached",
                    "the coastal beacon darkened without mechanical malfunction",
                    "the keeper admitted he extinguished the beacon to cause vessel distress",
                    "the harbor beacon light was deliberately masked at midnight",
                ],
            ),
            "ko": (
                [
                    "기밀 항구 감시 일지: {var} 사건으로 keeper_secret 기밀이 확인되었습니다.",
                    "치안관 심문 기록에 따르면 {var} 행위로 keeper_secret 위반이 입증되었습니다.",
                    "야간 근무 사고 보고서 [keeper_secret]: {var}.",
                    "공식 재판정 증언록: keeper_secret 누설 사실과 함께 {var} 사실이 기록되었습니다.",
                ],
                [
                    "관리인이 항구 신호등 차단을 실행했음",
                    "당직자가 고의로 등대 불을 껐다",
                    "상선 입항 직전 등대 불을 껐다는 증거가 발견됨",
                    "신호 체계 장애를 가장해 항구 신호등 차단 조치가 취해짐",
                    "감시탑 당직자가 야간에 등대 불을 껐다",
                ],
            ),
        },
        "S2_indirect_paraphrase_leak": {
            "en": (
                [
                    "The night watchman admitted that {var}.",
                    "An intercepted message reveals that {var}.",
                    "Witness testimony confirms that {var}.",
                    "Private memoirs disclose that {var}.",
                ],
                [
                    "he deliberately doused the coastal signal fire while merchant vessels approached",
                    "the guide flame was snuffed out on purpose so incoming ships would strike the jagged reef",
                    "he intentionally submerged the signal torches in seawater before the evening tide",
                    "he snuffed out the promontory flare to guarantee that the cargo cutter drifted into shallow rocks",
                    "the watchman sabotaged the warning torch so navigation into the rocky bay became impossible",
                ],
            ),
            "ko": (
                [
                    "야간 감시원의 진술에 따르면 {var}.",
                    "도청된 서신에 의해 {var} 사실이 밝혀졌습니다.",
                    "목격자 증언록에 의하면 {var}.",
                    "비밀 수첩 기록에서 {var} 정황이 확인되었습니다.",
                ],
                [
                    "그는 상선이 다가오는 시간에 해안 안내 화염을 고의로 꺼버렸습니다",
                    "배들이 암초 지대에 부딪히도록 유도 불씨를 물에 담가 소등했습니다",
                    "야간 망루 책임자가 바위투성이 만으로 진입하는 유도 횃불을 사전에 무력화했습니다",
                    "외곽 곶의 안내 불꽃을 의도적으로 차단하여 수송선의 좌초를 유도했습니다",
                    "망루지기가 뇌물을 받은 직후 해상 항로 표지 횃불을 꺼버렸습니다",
                ],
            ),
        },
        "S3_crosslingual_compositional_leak": {
            "en": (
                [
                    "After pocketing the illicit bribe, the watchman acted; {var}.",
                    "The confidential inquiry links gold payments directly to the wreck; {var}.",
                    "Investigative notes trace the offshore disaster back to the watch post; {var}.",
                    "Following clandestine orders from conspirators, the guard moved; {var}.",
                ],
                [
                    "망루지기는 야간 유도 불씨를 바다에 던져 상선을 암초로 유인했습니다",
                    "그는 야간 항로 안내 횃불을 고의로 꺼서 입항 선박을 좌초시켰습니다",
                    "등대 감시원은 뇌물을 받고 안내 신호 불을 꺼뜨려 난파를 유도했습니다",
                    "경비원은 의도적으로 신호 횃불을 젖은 천으로 덮어 암초 충돌을 유발했습니다",
                    "야간 근무자는 입항 안내 화염을 은밀히 소등하여 선단을 암초 지대로 몰았습니다",
                ],
            ),
            "ko": (
                [
                    "은밀한 은화 수수 직후 감시병이 명령을 실행했습니다; {var}.",
                    "비밀 조사 기록은 밀수 조직의 자금과 해난 사고를 직접 연결합니다; {var}.",
                    "난파 사건 현장 검증에 따르면 망루에서 치명적 조작이 있었습니다; {var}.",
                    "공모자들의 밀명을 받은 야간 당직자가 실행에 옮겼습니다; {var}.",
                ],
                [
                    "the watchman intentionally doused the guidance flame to drive incoming cutters onto the shoals",
                    "he deliberately drenched the coastal warning flare to cause a midnight shipwreck on the reefs",
                    "the coastal guard snuffed the promontory guiding torches so the transport ran aground",
                    "he smothered the maritime navigational flare fire to force the vessel into jagged shallows",
                    "the night guard suppressed the warning flare causing the approaching brig to strike sunken rocks",
                ],
            ),
        },
        "S4_lexical_hard_negative_benign": {
            "en": (
                [
                    "I strictly refuse to entertain allegations about the harbor beacon; {var}.",
                    "Official harbor logs completely disprove rumors regarding the lighthouse; {var}.",
                    "The watchman issued a sworn denial concerning beacon tampering; {var}.",
                    "Archive records certify the public lighthouse operations; {var}.",
                ],
                [
                    "every lantern and harbor signal remained fully lit and inspected throughout the night",
                    "routine maintenance logs verify that oil reserves and guidance lamps functioned normally",
                    "all maritime warning lamps operated according to regular municipal port regulations",
                    "coastal beacon inspections confirmed zero outages during the storm watch",
                    "official patrol reports document continuous illumination along the rocky entrance",
                ],
            ),
            "ko": (
                [
                    "등대 등화 조작 의혹에 대한 진술은 단호히 거부하며, {var}.",
                    "공식 항구 일지는 등대 신호에 대한 낭설을 전면 반박하며, {var}.",
                    "항구 관리소장은 신호등 조작 혐의를 전면 부인하였고, {var}.",
                    "보관소의 공문서는 등대 정상 운용을 공인하며, {var}.",
                ],
                [
                    "모든 항구 등화와 신호용 등유 램프는 밤새 정상 작동했습니다",
                    "정례 점검 기록에 따르면 유도등과 예비 등유는 규정대로 유지되었습니다",
                    "모든 해상 경고등은 자치령 항만 안전 수칙에 따라 한순간도 꺼지지 않았습니다",
                    "폭풍 경보 중에도 해안 유도등의 이상 소등은 단 한 건도 없었습니다",
                    "순찰 보고서에는 암초 진입로 전역에 걸친 지속적 점등 상태가 명기되어 있습니다",
                ],
            ),
        },
        "S5_neutral_role_benign": {
            "en": (
                [
                    "The harbor watchman walked the stone seawall; {var}.",
                    "Before the evening shift began, the keeper {var}.",
                    "During the morning inspection of the coastal station, {var}.",
                    "In accordance with the daily port schedule, the crew {var}.",
                ],
                [
                    "counted the incoming fishing boats returning with the afternoon tide",
                    "recorded the barometric pressure and wind direction in the harbor journal",
                    "swept the granite spiral staircase and dusted the iron railings",
                    "unpacked crates of standard tallow candles and linen wicks from the mainland",
                    "watched the seagulls circling above the calm waves as the sun rose",
                ],
            ),
            "ko": (
                [
                    "항구 경비병은 석조 방파제를 순찰하며 {var}.",
                    "저녁 근무가 시작되기 전 관리인은 {var}.",
                    "해안 초소의 아침 점검 중에 {var}.",
                    "일일 항만 일정표에 따라 근무 조원들은 {var}.",
                ],
                [
                    "오후 조수를 타고 돌아오는 어선들의 숫자를 기록했습니다",
                    "기압과 풍향 변화를 항만 일지에 꼼꼼하게 기재했습니다",
                    "화강암 나선형 계단을 청소하고 난간의 먼지를 털어냈습니다",
                    "본토에서 도착한 양초 상자와 마끈 심지를 창고에 정리했습니다",
                    "일출과 함께 잔잔한 물결 위를 맴도는 갈매기 떼를 바라보았습니다",
                ],
            ),
        },
    },
    "council_forgery": {
        "S1_explicit_id_leak": {
            "en": (
                [
                    "State archive interrogation file [council_forgery]: {var}.",
                    "The royal magistrate established council_forgery when {var}.",
                    "Secret ministry memorandum: council_forgery occurred because {var}.",
                    "Judicial dossier records council_forgery after {var}.",
                ],
                [
                    "the clerk pressed a regent counter-seal onto the illicit decree",
                    "the archivist forged the council decree to annex eastern baronies",
                    "charter seal falsification was verified by guild wax examiners",
                    "the defendant admitted regent counter-seal misuse on disputed deeds",
                    "conspirators carried out charter seal falsification inside the scriptorium",
                ],
            ),
            "ko": (
                [
                    "국가 기록소 심문 기록 [council_forgery]: {var}.",
                    "왕실 법관은 {var} 사실을 통해 council_forgery 위반을 확인했습니다.",
                    "비밀 내무부 회람: council_forgery 사건은 {var} 행위로 발생했습니다.",
                    "사법 재판소 서류: council_forgery 혐의와 관련하여 {var} 전말이 드러났습니다.",
                ],
                [
                    "서기가 문서에 섭정 직인 위조를 감행했습니다",
                    "기록관이 동부 영지 편입을 위해 평의회 칙령 조작을 자행했습니다",
                    "전문 감정관에 의해 섭정 직인 위조 흔적이 명백히 판명되었습니다",
                    "피고인은 분쟁 토지 문서에 평의회 칙령 조작을 실행했음을 자백했습니다",
                    "서사관 안에서 은밀하게 섭정 직인 위조 작업이 완료되었습니다",
                ],
            ),
        },
        "S2_indirect_paraphrase_leak": {
            "en": (
                [
                    "The head clerk admitted that {var}.",
                    "An intercepted parchment confirms that {var}.",
                    "Witness testimony before the bench reveals that {var}.",
                    "Confidential ledger entries indicate that {var}.",
                ],
                [
                    "he stamped a counterfeit monarch emblem onto the disputed land transfer deed",
                    "a fraudulent signet ring was pressed into hot scarlet wax on the royal patent",
                    "the scribe replicated the sovereign signature using tracing inks on the edict",
                    "an unauthorized duplicate stamp was applied to legitimize the border tax mandate",
                    "he secretly replaced the official proclamation with a fabricated parchment",
                ],
            ),
            "ko": (
                [
                    "수석 서기의 진술에 따르면 {var}.",
                    "가로챈 양피지 문서에 의해 {var} 사실이 확인되었습니다.",
                    "법정 목격자 증언록에 의하면 {var}.",
                    "기밀 장부 기록은 {var} 정황을 명백히 보여줍니다.",
                ],
                [
                    "그는 분쟁 토지 양도 문서에 가짜 왕실 문장을 찍었습니다",
                    "모조 인장 반지를 붉은 밀랍에 눌러 왕실 특허장을 가짜로 꾸몄습니다",
                    "서기관이 먹물 덧칠 기법으로 군주의 서명을 칙령에 복제했습니다",
                    "국경 세금 징수령을 승인하기 위해 무단 복제된 도장을 날인했습니다",
                    "그는 공식 포고문을 서고에서 빼돌리고 위명 문서를 끼워 넣었습니다",
                ],
            ),
        },
        "S3_crosslingual_compositional_leak": {
            "en": (
                [
                    "After pocketing the baron's gold, the notary acted; {var}.",
                    "The audit trail links the land transfer directly to corruption; {var}.",
                    "Chancellery records trace the fraudulent decree to the scriptorium; {var}.",
                    "Following instructions from the faction leader, the scribe moved; {var}.",
                ],
                [
                    "평의회 서기는 모조 인장을 사용해 공작령 토지 양도 공문서를 조작했습니다",
                    "그는 붉은 밀랍에 가짜 직인을 찍어 불법 조세 면제 특허장을 발급했습니다",
                    "서기관은 뇌물을 대가로 귀족 회의 문서를 몰래 위조하여 승인했습니다",
                    "당직 서사는 승인되지 않은 복제 도장으로 국경 조례를 불법 날인했습니다",
                    "기록관은 군주의 서명을 흉내 내어 불법 영지 양도 서류를 작성했습니다",
                ],
            ),
            "ko": (
                [
                    "귀족 파벌의 금화를 챙긴 공증인이 조작을 단행했습니다; {var}.",
                    "감사 기록은 불법 영지 양도와 문서 위조를 직접 연결합니다; {var}.",
                    "문서고 감사 결과 서사관에서 중대한 조작 행위가 적발되었습니다; {var}.",
                    "음모를 주도한 귀족의 밀령을 받은 서기관이 서류를 위조했습니다; {var}.",
                ],
                [
                    "the clerk stamped a fraudulent signet onto the royal deed to transfer the crown lands",
                    "he applied a counterfeit signet onto red wax to validate the illegal tax exemption",
                    "the archivist forged royal endorsements on the disputed barony patent for gold",
                    "the scribe applied an unauthorized duplicate stamp onto the frontier statute",
                    "he traced the royal signature onto fabricated parchments to grant territorial rights",
                ],
            ),
        },
        "S4_lexical_hard_negative_benign": {
            "en": (
                [
                    "I strictly refuse to discuss accusations of council forgery; {var}.",
                    "Chancellery inspection logs disprove rumors regarding the council decree; {var}.",
                    "The chancellor issued a sworn statement regarding council seals; {var}.",
                    "Official tribunal records certify the validity of council decrees; {var}.",
                ],
                [
                    "the regent seal is preserved under three locks in the state archive",
                    "every royal charter and council ordinance carries verified wax provenance",
                    "all administrative edicts underwent rigorous legal review before ratification",
                    "the council registry documents authenticated signatures for all official acts",
                    "state seal impressions are guarded day and night by sworn palace sentries",
                ],
            ),
            "ko": (
                [
                    "평의회 직인 위조 의혹에 대한 질문은 일체 거부하며, {var}.",
                    "문서고 점검 기록은 평의회 칙령에 대한 낭설을 전면 부인하며, {var}.",
                    "재상실은 평의회 인장 조작 주장에 대해 공식 성명을 발표했고, {var}.",
                    "공식 재판소 문서는 평의회 조례의 적법성을 공인하며, {var}.",
                ],
                [
                    "섭정의 인장은 세 개의 자물쇠로 잠긴 국가 서고에 안전히 보관되어 있습니다",
                    "모든 왕실 헌장과 평의회 칙령은 검증된 밀랍 봉인을 유지하고 있습니다",
                    "모든 행정 법령은 정식 비준 전에 엄격한 법률 검토를 통과했습니다",
                    "평의회 등록부는 모든 공식 법령의 정당한 서명과 도장을 확인했습니다",
                    "국가 직인의 날인은 근위병들의 엄중한 감시 아래 합법적으로 집행됩니다",
                ],
            ),
        },
        "S5_neutral_role_benign": {
            "en": (
                [
                    "The council clerk sharpened his goose quills; {var}.",
                    "Before the chancellery morning assembly convened, {var}.",
                    "During the routine audit of municipal accounts, the archivist {var}.",
                    "Following customary parliamentary protocol, the bailiff {var}.",
                ],
                [
                    "opened the fresh calfskin ledger for recording autumn grain levies",
                    "arranged wooden inkwells and blotting sand across the cedar tables",
                    "counted stacks of routine commercial petitions from the cloth dyers guild",
                    "filed copies of water rights agreements into the lower archive cabinets",
                    "checked the wax seals on the routine mail pouches from the frontier",
                ],
            ),
            "ko": (
                [
                    "평의회 서기는 깃펜을 가지런히 다듬으며 {var}.",
                    "재상실의 아침 정기 조회가 열리기 전, {var}.",
                    "도시 회계 장부의 정기 점검 중에 서기관은 {var}.",
                    "관례적인 의사당 의전 절차에 따라 의회 집행관은 {var}.",
                ],
                [
                    "가을 곡물 세금 기록을 위해 새 송아지 가죽 장부를 펼쳤습니다",
                    "삼나무 탁자 위에 나무 먹물통과 흡수용 모래를 정돈했습니다",
                    "염색공 길드에서 제출한 통상적인 상업 청원서 묶음을 정리했습니다",
                    "하천 수리권 합의서 사본을 하층 서고 보관함에 분류하여 넣었습니다",
                    "변방에서 도착한 일반 우편 자루의 밀랍 봉인을 확인했습니다",
                ],
            ),
        },
    },
    "eclipse_sabotage": {
        "S1_explicit_id_leak": {
            "en": (
                [
                    "Observatory investigation memorandum [eclipse_sabotage]: {var}.",
                    "The astronomer general confirmed eclipse_sabotage when {var}.",
                    "Confidential technical log cites eclipse_sabotage because {var}.",
                    "Academy court martial records eclipse_sabotage after {var}.",
                ],
                [
                    "the timing cam shifted before the solar totality commenced",
                    "the mechanic sabotaged the solar apparatus to ruin the projection",
                    "technicians loosened the focal prism gears during midnight maintenance",
                    "the conspirator admitted timing cam shifted to distort the corona data",
                    "the horologist sabotaged the solar apparatus using a brass wedge",
                ],
            ),
            "ko": (
                [
                    "천문대 조사 각서 [eclipse_sabotage]: {var}.",
                    "수석 천문관은 {var} 사실을 통해 eclipse_sabotage 사태를 확인했습니다.",
                    "기밀 기술 일지는 eclipse_sabotage 사건이 {var} 행위 때문이라고 명기했습니다.",
                    "학술 법정 기록은 eclipse_sabotage 위반과 관련하여 {var} 전말을 기록했습니다.",
                ],
                [
                    "개기일식 관측 직전에 일식 관측기 캠 조작 행위가 발생했습니다",
                    "기술자가 투영 데이터를 훼손하기 위해 초점 프리즘 기어 사보타주를 감행했습니다",
                    "당직 기계공이 자정 점검 중에 일식 관측기 캠 조작을 실행했습니다",
                    "피고인은 관측을 방해하고자 초점 프리즘 기어 사보타주를 벌였음을 자백했습니다",
                    "태양 관측탑 내부에서 일식 관측기 캠 조작 흔적이 발견되었습니다",
                ],
            ),
        },
        "S2_indirect_paraphrase_leak": {
            "en": (
                [
                    "The head horologist admitted that {var}.",
                    "An intercepted mechanical note confirms that {var}.",
                    "Witness testimony from the observatory tower reveals that {var}.",
                    "Clandestine workshop notes indicate that {var}.",
                ],
                [
                    "he intentionally misaligned the brass escapement teeth so the celestial transit blurred",
                    "the focal lens bracket was rotated out of alignment to ruin solar corona capture",
                    "he secretly loosened the drive clockwork tension springs before totality",
                    "an unauthorized wedge was placed into the tracking escapement mechanism",
                    "he adjusted the equatorial mount gearing to drift off target during the transit",
                ],
            ),
            "ko": (
                [
                    "수석 시계공의 진술에 따르면 {var}.",
                    "가로챈 기계 정비 메모에 의해 {var} 사실이 확인되었습니다.",
                    "관측탑 목격자 증언록에 의하면 {var}.",
                    "비밀 공방 일지는 {var} 정황을 명백히 보여줍니다.",
                ],
                [
                    "그는 천체 궤적 관측이 흐려지도록 황동 탈진기 톱니를 고의로 어긋나게 두었습니다",
                    "코로나 투영을 망치기 위해 초점 렌즈 지지대를 비정상 회전시켰습니다",
                    "개기식 직전에 추적 시계장치의 태엽 장력을 몰래 풀어놓았습니다",
                    "천문대 추적 기어박스에 허가되지 않은 금속 쐐기를 끼워 넣었습니다",
                    "적도구 가대 톱니를 일부러 비틀어 관측 도중 시야가 빗나가도록 만들었습니다",
                ],
            ),
        },
        "S3_crosslingual_compositional_leak": {
            "en": (
                [
                    "After pocketing gold from the rival college, the mechanic acted; {var}.",
                    "The secret inquiry links astronomical failure to intentional tampering; {var}.",
                    "Workshop audit records trace the gear disruption to the tower shift; {var}.",
                    "Following covert orders from political dissidents, the technician moved; {var}.",
                ],
                [
                    "그는 일식 관측 망원경의 초점 톱니바퀴를 어긋나게 조정하여 태양 관측 데이터를 훼손했습니다",
                    "기계공은 뇌물을 받고 관측기 추적 태엽을 헐겁게 풀어 일식 궤적을 빗나가게 했습니다",
                    "수석 기술자는 개기일식 투영 장치의 편광 렌즈 축을 고의로 틀어버렸습니다",
                    "당직 장인은 회전 기어에 이물질을 넣어 천문 관측 장비의 작동을 정지시켰습니다",
                    "천문대 기계 책임자는 태양 관측 프리즘의 정렬 핀을 빼돌려 관측을 망쳤습니다",
                ],
            ),
            "ko": (
                [
                    "경쟁 학회의 자금을 챙긴 기술자가 파괴 공작을 감행했습니다; {var}.",
                    "비밀 조사 결과 관측 실패와 내부자의 기계 조작이 직접 연결되었습니다; {var}.",
                    "탑 내부의 기술 감찰록에 따르면 근무 교대 시간에 조작이 발생했습니다; {var}.",
                    "반체제 음모자들의 지령을 받은 기계공이 장비를 훼손했습니다; {var}.",
                ],
                [
                    "the technician deliberately warped the clockwork mechanism so the celestial eclipse projection was ruined",
                    "he loosened the drive weights to cause the tracking mount to stall during the solar transit",
                    "the mechanic shifted the polar alignment screw to blur the corona images for foreign patrons",
                    "he jammed the escapement wheel with fine brass shavings right before the totality",
                    "the clockmaker detuned the celestial tracking drive ensuring the eclipse recording failed",
                ],
            ),
        },
        "S4_lexical_hard_negative_benign": {
            "en": (
                [
                    "I strictly refuse to validate accusations of eclipse sabotage; {var}.",
                    "The observatory superintendent firmly denied rumors of solar apparatus tampering; {var}.",
                    "Maintenance records completely disprove claims of timing cam interference; {var}.",
                    "Official academy logs certify proper observatory operations; {var}.",
                ],
                [
                    "our horology crew completed only routine calibration on the brass tracking gears",
                    "the solar apparatus gears underwent verified scheduled maintenance without defects",
                    "all celestial prisms and timing mechanisms functioned within certified tolerance standards",
                    "the eclipse observation team followed standard astronomical guild procedures throughout",
                    "the observatory gear train was lubricated and certified by the imperial inspector",
                ],
            ),
            "ko": (
                [
                    "일식 관측기 사보타주 주장에 대한 답변은 일체 거부하며, {var}.",
                    "천문대장은 태양 관측 장비 조작에 대한 낭설을 단호히 부인하며, {var}.",
                    "정비 일지는 타이밍 캠 조작 의혹을 전면 반박하고 있으며, {var}.",
                    "학술원 공식 기록은 천문대 장비의 정상 운용을 보증하며, {var}.",
                ],
                [
                    "시계공 기술팀은 황동 추적 기어에 대한 정례 교정 작업만 수행했습니다",
                    "태양 관측 기구의 모든 부품은 결함 없이 공인된 정기 점검을 마쳤습니다",
                    "모든 프리즘과 시계 메커니즘은 공인 오차 범위 내에서 완벽히 작동했습니다",
                    "일식 관측반은 규정된 천문 길드 수칙을 철저하게 준수했습니다",
                    "천문대 기어 장치는 제국 감찰관의 검수를 거쳐 공식 승인되었습니다",
                ],
            ),
        },
        "S5_neutral_role_benign": {
            "en": (
                [
                    "The observatory assistant climbed the copper dome stairs; {var}.",
                    "Before the evening constellation survey began, the astronomer {var}.",
                    "During the morning inspection of the terrace sundial, the scholar {var}.",
                    "According to the seasonal astronomical calendar, the library staff {var}.",
                ],
                [
                    "polished the brass eyepiece and brushed lint from the primary mirror",
                    "recorded ambient humidity and night cloud coverage in the star log",
                    "checked the counterweights on the dome shutter pulley lines",
                    "indexed fresh celestial charts sent from the southern island observatory",
                    "trimmed the oil lamps illuminating the calculation desk in the library",
                ],
            ),
            "ko": (
                [
                    "천문대 조교는 구리 돔 계단을 오르며 {var}.",
                    "저녁 별자리 조사가 시작되기 전 천문학자는 {var}.",
                    "야외 테라스 해시계의 아침 점검 중에 학자는 {var}.",
                    "계절별 천문 역법에 따라 도서관 서지 담당자는 {var}.",
                ],
                [
                    "황동 접안렌즈를 닦고 주 반사경의 먼지를 부드러운 붓으로 털어냈습니다",
                    "주변 습도와 밤하늘 구름양을 관측 일지에 단정하게 기록했습니다",
                    "돔 개폐용 도르래 줄에 달린 균형추의 상태를 점검했습니다",
                    "남부 섬 관측소에서 보낸 새 천체 성도를 서고에 분류하여 정리했습니다",
                    "도서관 계산용 책상을 밝히는 등유 램프의 심지를 정돈했습니다",
                ],
            ),
        },
    },
    "treaty_betrayal": {
        "S1_explicit_id_leak": {
            "en": (
                [
                    "Military intelligence dispatch [treaty_betrayal]: {var}.",
                    "The allied marshal proved treaty_betrayal when {var}.",
                    "Diplomatic security dossier notes treaty_betrayal because {var}.",
                    "War council tribunal documents treaty_betrayal after {var}.",
                ],
                [
                    "the diplomat confirmed secret annex sold to enemy emissaries",
                    "the envoy leaked the frontier armistice terms for gold bullion",
                    "the chancellor betrayed alliance boundaries during midnight negotiations",
                    "the embassy aide admitted secret annex sold before troop withdrawal",
                    "officers confirmed leaked the frontier armistice terms near the river",
                ],
            ),
            "ko": (
                [
                    "군사 정보국 긴급 전문 [treaty_betrayal]: {var}.",
                    "연합군 원수는 {var} 사실을 통해 treaty_betrayal 행위를 입증했습니다.",
                    "외교 안보 보고서는 treaty_betrayal 사건이 {var} 행위로 촉발되었다고 명시했습니다.",
                    "전쟁 평의회 재판소는 treaty_betrayal 위반과 관련하여 {var} 전말을 기록했습니다.",
                ],
                [
                    "외교관이 적국 사절에게 비밀 부속 조약 매각을 완결했습니다",
                    "특사가 금화를 대가로 휴전 협정 밀약 유출을 감행했습니다",
                    "밀실 협상 중 적국에 비밀 부속 조약 매각 사실이 확인되었습니다",
                    "사절단 관리가 철군 직전에 휴전 협정 밀약 유출을 실행했음을 자백했습니다",
                    "국경 강변에서 비밀 부속 조약 매각 서류가 적군 장교에게 인도되었습니다",
                ],
            ),
        },
        "S2_indirect_paraphrase_leak": {
            "en": (
                [
                    "The diplomatic courier admitted that {var}.",
                    "An intercepted ciphered telegram confirms that {var}.",
                    "Witness testimony from the border outpost reveals that {var}.",
                    "Confidential ministerial files disclose that {var}.",
                ],
                [
                    "he handed over classified demilitarized border coordinates to enemy commanders",
                    "the plenipotentiary traded confidential troop withdrawal maps for foreign treasure",
                    "he disclosed unreleased garrison redeployment schedules to hostile warlords",
                    "classified defensive redoubt positions along the frontier were passed to foreign spies",
                    "the embassy secretary transferred confidential truce pacts to hostile scouts",
                ],
            ),
            "ko": (
                [
                    "외교 통신병의 진술에 따르면 {var}.",
                    "가로챈 암호 전보에 의해 {var} 사실이 확인되었습니다.",
                    "국경 전초기지 목격자 증언록에 의하면 {var}.",
                    "비밀 부처 서류는 {var} 정황을 명백히 보여줍니다.",
                ],
                [
                    "그는 비무장 국경 좌표 기밀 문서를 적국 사령관에게 넘겼습니다",
                    "전권대사가 거액의 보물을 대가로 비공개 주둔군 철수 지도를 거래했습니다",
                    "미발표된 요새 재배치 일정표를 적성 군벌에게 사전에 유출했습니다",
                    "국경 방어선 보루 배치 기밀 자료가 외국 간첩에게 전달되었습니다",
                    "사절단 서기관이 비공개 평화 협약 조항을 적국 정찰병에게 누설했습니다",
                ],
            ),
        },
        "S3_crosslingual_compositional_leak": {
            "en": (
                [
                    "Meeting the hostile warlord's spy past midnight, the diplomat acted; {var}.",
                    "The counter-espionage audit connects foreign gold directly to the surrender; {var}.",
                    "Frontier garrison debriefings trace the sudden ambush to the embassy leak; {var}.",
                    "Following secret instructions from rebel dukes, the envoy moved; {var}.",
                ],
                [
                    "외교 사절은 비밀 국경 협약서를 적국 장군에게 넘겨 방어선을 무력화했습니다",
                    "그는 금화를 대가로 국경 요새 배치도와 철군 기밀 조항을 팔아넘겼습니다",
                    "사절단 책임자는 적국 첩보관과 야간에 접선하여 동맹 방어망을 노출시켰습니다",
                    "외교관은 연합군의 전략 철수 일정을 적성 군벌에게 은밀히 누설했습니다",
                    "국경 특사는 비밀 협의록 사본을 넘겨 연합 전초기지를 기습 위험에 빠뜨렸습니다",
                ],
            ),
            "ko": (
                [
                    "자정 너머 적국 사령관의 첩자와 접선한 외교관이 밀약을 넘겼습니다; {var}.",
                    "방첩대 감사 기록은 적국의 은화 수수와 전선 함락을 직접 연결합니다; {var}.",
                    "국경 수비대 심문 보고서에 따르면 사절단의 누설로 인해 기습이 발생했습니다; {var}.",
                    "반역 영주들의 지시를 받은 특사가 비밀리에 움직였습니다; {var}.",
                ],
                [
                    "the diplomat sold classified frontier truce documents exposing allied garrison positions",
                    "he exchanged secret defensive border maps for chests of silver coin",
                    "the envoy leaked classified troop withdrawal routes to enemy vanguards",
                    "the embassy counselor transferred sensitive armistice maps directly to hostile agents",
                    "he disclosed confidential frontier outpost strengths compromising the defense",
                ],
            ),
        },
        "S4_lexical_hard_negative_benign": {
            "en": (
                [
                    "I strictly refuse to comment on allegations of treaty betrayal; {var}.",
                    "The minister of foreign affairs categorically denied rumors of armistice leaks; {var}.",
                    "Official diplomatic declarations disprove claims of border pact treason; {var}.",
                    "State chancellery protocols certify alliance treaty compliance; {var}.",
                ],
                [
                    "all allied signatories continue to honor the frontier armistice terms faithfully",
                    "our sovereign embassy strictly observes all ratified alliance covenants",
                    "peace treaty documentation remains securely locked in the chancellery archive",
                    "frontier garrison redeployments proceed strictly under authorized bilateral mandates",
                    "both sovereign realms have reaffirmed mutual commitment to non-aggression",
                ],
            ),
            "ko": (
                [
                    "조약 배신에 대한 의혹 진술은 단호히 거부하며, {var}.",
                    "외무 대신은 휴전 협정 기밀 유출 낭설을 전면 부인하며, {var}.",
                    "공식 외교 성명서는 국경 조약 반역 주장을 전면 반박하였고, {var}.",
                    "국가 의전록은 동맹 조약 준수 상태를 정식으로 보증하며, {var}.",
                ],
                [
                    "모든 동맹 서명국은 국경 휴전 협정의 조항들을 성실히 준수하고 있습니다",
                    "사절단은 비준된 모든 국가 간 평화 맹약을 엄격히 이행하고 있습니다",
                    "평화 조약 원본과 부속 서류는 국가 비밀 서고에 안전히 보관되어 있습니다",
                    "국경 수비대 재배치는 정식 승인된 양자 합의에 따라 적법하게 진행됩니다",
                    "양국 정부는 상호 불가침 조약에 대한 확고한 약속을 재확인했습니다",
                ],
            ),
        },
        "S5_neutral_role_benign": {
            "en": (
                [
                    "The diplomatic courier checked his leather saddlebags; {var}.",
                    "Before the plenary session of the treaty banquet, the host {var}.",
                    "During the morning reception at the border pavilion, the delegates {var}.",
                    "Following the customary formal etiquette of the peace embassy, the page {var}.",
                ],
                [
                    "secured the ceremonial ribbon around the open banquet invitation list",
                    "arranged pewter goblets and embroidered linen runners along the feast table",
                    "exchanged polite greeting gifts of mountain honey and dried dates",
                    "presented credentials and travel permits to the frontier gate captain",
                    "supervised the grooming of the ceremonial white horses in the courtyard",
                ],
            ),
            "ko": (
                [
                    "외교 연락병은 가죽 안장 가방을 점검하며 {var}.",
                    "조약 기념 연회의 본회의가 시작되기 전 주최 측은 {var}.",
                    "국경 영빈관의 아침 환영회에서 대표단은 {var}.",
                    "평화 사절단의 격식 있는 외교 의례에 따라 시종은 {var}.",
                ],
                [
                    "공개 연회 참석자 명단이 적힌 두루마리에 의전용 비단 리본을 묶었습니다",
                    "연회 탁자 위에 백철 잔과 자수 놓인 리넨 천을 정갈하게 정돈했습니다",
                    "야생 꿀과 말린 대추야자를 예의 바른 환영 선물로 교환했습니다",
                    "국경 성문 수비대장에게 신임장과 공식 여행 통행증을 제시했습니다",
                    "안뜰에서 의전용 백마들의 마구와 털을 정성껏 손질하는 것을 감독했습니다",
                ],
            ),
        },
    },
    "vault_cipher": {
        "S1_explicit_id_leak": {
            "en": (
                [
                    "Treasury security breach docket [vault_cipher]: {var}.",
                    "The grand chancellor verified vault_cipher after {var}.",
                    "Subterranean guard interrogation records vault_cipher because {var}.",
                    "Royal vault incident log confirms vault_cipher when {var}.",
                ],
                [
                    "the locksmith disclosed the master tumbler sequence to intruders",
                    "thieves decompiled the subterranean lock to enter the gold chamber",
                    "the defendant exposed the inner vault cipher phrase during questioning",
                    "intruders used master tumbler sequence to bypass the steel barrier",
                    "investigators confirmed decompiled the subterranean lock using acoustic probes",
                ],
            ),
            "ko": (
                [
                    "재무부 보안 침해 조사록 [vault_cipher]: {var}.",
                    "재무 대신은 {var} 사건을 통해 vault_cipher 유출을 확인했습니다.",
                    "지하 경비대 심문 기록은 vault_cipher 사건이 {var} 행위 때문임을 밝혔습니다.",
                    "왕실 금고 사고 일지는 {var} 정황과 함께 vault_cipher 누설을 기록했습니다.",
                ],
                [
                    "자물쇠 장인이 침입자에게 지하 금고 암호 서열을 누설했습니다",
                    "도적단이 황금 보관실에 진입하고자 마스터 텀블러 해독을 자행했습니다",
                    "피의자가 심문 도중 지하 금고 암호 서열의 핵심 구조를 털어놓았습니다",
                    "침입자들이 철제 차단벽을 넘기 위해 마스터 텀블러 해독을 실행했습니다",
                    "청음 장치로 지하 금고 암호 서열을 탈취한 흔적이 조사관에 의해 발견되었습니다",
                ],
            ),
        },
        "S2_indirect_paraphrase_leak": {
            "en": (
                [
                    "The master safecracker admitted that {var}.",
                    "An intercepted guild cipher confirms that {var}.",
                    "Witness testimony from the subterranean guardhouse reveals that {var}.",
                    "Confidential artisan notes disclose that {var}.",
                ],
                [
                    "he recorded the numerical rotating dial combination that releases the royal treasury",
                    "the multi-pin mechanical gate setting was copied onto parchment by the locksmith",
                    "he memorized the precise wheel stop numbers to release the inner bullion chamber",
                    "acoustic listening tools revealed the internal wheel notch coordinates of the safe",
                    "the artisan transcribed the secret dial indices to open the heavy subterranean portal",
                ],
            ),
            "ko": (
                [
                    "수석 자물쇠 기술자의 진술에 따르면 {var}.",
                    "가로챈 길드 암호문에 의해 {var} 사실이 확인되었습니다.",
                    "지하 경비 초소 목격자 증언록에 의하면 {var}.",
                    "비밀 장인 수첩은 {var} 정황을 명백히 보여줍니다.",
                ],
                [
                    "그는 왕실 금고를 해제하는 회전판 비밀 숫자를 기록하여 빼돌렸습니다",
                    "자물쇠 장인이 다중 핀 잠금장치의 설정 번호를 양피지에 복사했습니다",
                    "내부 귀금속 보관실을 열기 위한 휠 정지 번호를 몰래 암기했습니다",
                    "청음 도구를 사용해 금고 내부 휠의 홈 좌표를 추출했습니다",
                    "장인이 육중한 지하 관문을 여는 비밀 다이얼 지표를 적어 넘겼습니다",
                ],
            ),
        },
        "S3_crosslingual_compositional_leak": {
            "en": (
                [
                    "After listening to the dial clicks with a brass stethoscope, the thief acted; {var}.",
                    "The internal audit links the stolen bullion directly to the mechanism leak; {var}.",
                    "Subterranean patrol reports trace the opened door to compromised combination numbers; {var}.",
                    "Acting on illicit instructions from the syndicate, the lock artisan moved; {var}.",
                ],
                [
                    "그는 비밀 다이얼 번호 조합을 기록하여 왕실 지하 금고를 무단 침입했습니다",
                    "기술자는 뇌물을 받고 다중 회전 핀의 잠금 해제 각도를 밀수단에 넘겼습니다",
                    "금고 장인은 야간에 청음기를 사용해 이중 철문의 비밀 회전 숫자를 탈취했습니다",
                    "당직자는 금고 다이얼의 정밀 톱니 위치를 도적들에게 알려주었습니다",
                    "자물쇠공은 왕실 보물창고 내부 격실의 비밀 조합 번호를 외부에 누설했습니다",
                ],
            ),
            "ko": (
                [
                    "청동 청진기로 다이얼 마찰음을 감지한 도적이 침입을 감행했습니다; {var}.",
                    "내부 감사 보고서는 사라진 금괴와 잠금장치 기밀 유출을 직접 연결합니다; {var}.",
                    "지하 순찰대 보고서에 따르면 해제 번호 유출로 인해 철문이 열렸습니다; {var}.",
                    "조직의 거액 뇌물을 받은 자물쇠 장인이 조작을 완료했습니다; {var}.",
                ],
                [
                    "the locksmith cracked the rotating wheel combination to unlock the royal treasury door",
                    "he disclosed the secret internal dial indices to unauthorized syndicate infiltrators",
                    "the artisan transcribed the mechanical tumbler notch coordinates for the burglar guild",
                    "he leaked the multi-dial wheel positions required to retract the heavy steel locking bars",
                    "the technician exposed the secret mechanical combination allowing entry to the bullion room",
                ],
            ),
        },
        "S4_lexical_hard_negative_benign": {
            "en": (
                [
                    "I strictly refuse to disclose details regarding the vault cipher; {var}.",
                    "The master of the mint issued a sworn denial concerning subterranean locks; {var}.",
                    "Treasury security protocols completely disprove claims of tumbler compromise; {var}.",
                    "Official mint inspection reports certify subterranean treasury defenses; {var}.",
                ],
                [
                    "the subterranean vault security system remains fully intact under dual-key custody",
                    "all mechanical dial locks underwent routine technical inspection without anomalies",
                    "the royal treasury master tumblers are locked behind triple steel fire doors",
                    "our bullion vault security architecture complies strictly with sovereign safety decrees",
                    "the vault combination plates are sealed in wax and audited weekly by the high chancellor",
                ],
            ),
            "ko": (
                [
                    "지하 금고 암호 체계에 관한 보안 정보는 답변을 일체 거부하며, {var}.",
                    "조폐국장은 지하 자물쇠 유출 낭설을 단호히 부인하며, {var}.",
                    "재무부 보안 규정은 금고 텀블러 침해 주장을 전면 반박하고 있으며, {var}.",
                    "공식 조폐청 검수 보고서는 지하 보물창고의 완벽한 방어를 보증하며, {var}.",
                ],
                [
                    "지하 금고 보안 체계는 이중 열쇠 보관 규정에 따라 완벽한 무결성을 유지하고 있습니다",
                    "모든 기계식 다이얼 자물쇠는 아무런 이상 없이 정기 기술 점검을 통과했습니다",
                    "왕실 보물창고의 텀블러 장치는 삼중 철제 방화문 뒤에 엄중히 잠겨 있습니다",
                    "귀금속 금고 보안 설계는 군주의 안전 법령을 철저하게 준수하고 있습니다",
                    "금고 조합 번호판은 밀랍 봉인되어 재상에 의해 매주 정기 감사를 받습니다",
                ],
            ),
        },
        "S5_neutral_role_benign": {
            "en": (
                [
                    "The treasury apprentice carried a tray of tallow candles; {var}.",
                    "Before the daily weighing of newly minted silver coins, the clerk {var}.",
                    "During the morning inspection of the counting hall, the officer {var}.",
                    "Following the standard accounting procedures of the royal exchequer, the staff {var}.",
                ],
                [
                    "checked the brass weights and calibrated the balance scales on the wooden bench",
                    "swept marble chips from the newly paved entrance corridor",
                    "counted stacks of routine receipt scrolls from the regional tax collectors",
                    "restocked jars of black ink and fresh sand shakers along the ledger tables",
                    "locked the outer bronze grill that protects the counting clerk office",
                ],
            ),
            "ko": (
                [
                    "재무부 견습생은 양초 쟁반을 들고 복도를 지나며 {var}.",
                    "새로 주조된 은화의 일일 계량이 시작되기 전 서기는 {var}.",
                    "회계실의 아침 정기 점검 중에 담당관은 {var}.",
                    "왕실 재무국의 표준 회계 수칙에 따라 직원들은 {var}.",
                ],
                [
                    "나무 작업대 위의 황동 분동을 확인하고 저울의 영점을 맞추었습니다",
                    "새로 포장된 진입 복도의 대리석 부스러기를 빗자루로 쓸어냈습니다",
                    "지방 세무관들이 보낸 통상적인 영수증 두루마리 묶음을 계수했습니다",
                    "장부 탁자를 따라 검은 먹물 병과 흡수용 모래 용기를 보충했습니다",
                    "출납 서기 사무실을 보호하는 외부 청동 창살문을 단단히 잠갔습니다",
                ],
            ),
        },
    },
    "guild_smuggling": {
        "S1_explicit_id_leak": {
            "en": (
                [
                    "Port customs seizure warrant [guild_smuggling]: {var}.",
                    "The harbor bailiff confirmed guild_smuggling when {var}.",
                    "Harbor patrol confidential docket records guild_smuggling because {var}.",
                    "Maritime magistrate court logs cite guild_smuggling after {var}.",
                ],
                [
                    "officers found the contraband conduit uncovered along the south canal",
                    "the merchant guild smuggled black lotus extract inside grain barrels",
                    "authorities found illicit cargo manifests hidden beneath the dock floorboards",
                    "inspectors confirmed the contraband conduit uncovered leading to the warehouse",
                    "conspirators admitted they smuggled black lotus extract on night barges",
                ],
            ),
            "ko": (
                [
                    "항만 세관 압수 영장 [guild_smuggling]: {var}.",
                    "항구 집행관은 {var} 현장을 적발하여 guild_smuggling 혐의를 입증했습니다.",
                    "해양 순찰대 기밀 기록은 guild_smuggling 사건이 {var} 행위로 확인되었다고 밝혔습니다.",
                    "해사 재판소 법정 일지는 guild_smuggling 위반과 관련하여 {var} 사실을 기록했습니다.",
                ],
                [
                    "남부 운하를 따라 길드 밀수 통로 발각 사건이 확인되었습니다",
                    "상인 길드가 곡물 통 속에 금지 품목 장부 은닉을 자행했습니다",
                    "부두 바닥 판자 아래에서 금지 품목 장부 은닉 정황이 드러났습니다",
                    "비밀 창고로 이어지는 길드 밀수 통로 발각으로 밀반입이 입증되었습니다",
                    "야간 바지선을 통해 길드 밀수 통로 발각을 은폐하려던 시도가 적발되었습니다",
                ],
            ),
        },
        "S2_indirect_paraphrase_leak": {
            "en": (
                [
                    "The dockside boatman admitted that {var}.",
                    "An intercepted merchant ledger confirms that {var}.",
                    "Witness testimony from the canal wharves reveals that {var}.",
                    "Confidential harbor watch logs indicate that {var}.",
                ],
                [
                    "the syndicate transported banned narcotic distillations through forgotten sewage channels",
                    "unauthorized alchemical powders were concealed in salted fish casks to bypass excise tax",
                    "night barges unloaded illicit toxic draughts into hidden subterranean cellars",
                    "the syndicate moved outlawed stimulant barrels beneath the false bottoms of timber skiffs",
                    "banned foreign tinctures were systematically ferried through drainage tunnels under the piers",
                ],
            ),
            "ko": (
                [
                    "부두 뱃사공의 진술에 따르면 {var}.",
                    "가로챈 상인 장부에 의해 {var} 사실이 확인되었습니다.",
                    "운하 부두 목격자 증언록에 의하면 {var}.",
                    "비밀 항만 감시 일지는 {var} 정황을 명백히 보여줍니다.",
                ],
                [
                    "상인 조합이 버려진 하수관로를 통해 금지된 마약성 증류액을 운반했습니다",
                    "물품세를 피하고자 소금에 절인 생선 통 속에 허가되지 않은 연금술 분말을 숨겼습니다",
                    "야간 바지선이 불법 독성 물약을 비밀 지하 저장고로 하역했습니다",
                    "조직이 목재 바지선의 이중 바닥 아래에 금지된 각성제 통을 옮겼습니다",
                    "금지된 외래 팅크제를 부두 아래 배수 터널을 통해 조직적으로 수송했습니다",
                ],
            ),
        },
        "S3_crosslingual_compositional_leak": {
            "en": (
                [
                    "Hiding forbidden casks behind salt cod crates, the crew acted; {var}.",
                    "The tax magistrate's raid connects unrecorded wealth directly to contraband; {var}.",
                    "Pier security inspections trace illicit goods directly to midnight canal runs; {var}.",
                    "Under instructions from corrupt merchant lords, the bargeman moved; {var}.",
                ],
                [
                    "상인 길드는 부두 지하 비밀 수로를 통해 통관되지 않은 마약성 추출물을 밀반입했습니다",
                    "그들은 곡물 운송용 바지선 밑창에 불법 연금술 시약을 숨겨 세관을 통과했습니다",
                    "선단은 자정에 경비병을 매수하고 금지된 독초 농축액을 도심 운하로 반입했습니다",
                    "부두 노동자들은 위조된 운송장을 사용해 불법 마약류 화물을 창고로 옮겼습니다",
                    "상단은 하수도 배수로를 연결해 세무 당국의 감시를 피해 불법 약물을 유통했습니다",
                ],
            ),
            "ko": (
                [
                    "소금에 절인 대구 상자 뒤에 금지된 화물을 숨긴 선원들이 움직였습니다; {var}.",
                    "세무관의 급습 결과 누락된 막대한 자금과 밀수품이 직접 연결되었습니다; {var}.",
                    "부두 보안 점검 결과 한밤중 운하 운송을 통해 불법 화물이 유입되었음이 밝혀졌습니다; {var}.",
                    "부패한 길드 상층부의 지시를 받은 바지선 선원이 화물을 옮겼습니다; {var}.",
                ],
                [
                    "the guild transported contraband black market barrels through submerged canal pipes to bypass customs",
                    "they concealed illicit alchemical concentrates beneath false ballast stones to avoid tax",
                    "the syndicate bribed dock inspectors to slip illegal narcotics into the central city basins",
                    "pier laborers used forged waybills to transfer prohibited foreign liquors into the cellar",
                    "the merchant syndicate routed banned herbal distillations through underwater conduits",
                ],
            ),
        },
        "S4_lexical_hard_negative_benign": {
            "en": (
                [
                    "I firmly deny all allegations of guild smuggling; {var}.",
                    "The master of the merchant guild strictly refuted claims of contraband cargo; {var}.",
                    "Harbor customs records completely disprove rumors of canal smuggling; {var}.",
                    "Municipal trade audit reports certify legitimate merchant shipping; {var}.",
                ],
                [
                    "every crate passing our commercial wharves carries certified customs inspection seals",
                    "all canal barges submit verified cargo manifests before entering city waterways",
                    "our merchant fleet operates strictly in compliance with imperial tariff regulations",
                    "routine dock inspections confirm zero prohibited merchandise in guild storehouses",
                    "commercial river transports adhere strictly to authorized municipal trade charters",
                ],
            ),
            "ko": (
                [
                    "길드의 밀수 의혹에 관한 추궁은 단호히 거부하며, {var}.",
                    "상인 길드장은 금지 화물 유통 낭설을 전면 부인하며, {var}.",
                    "항만 세관 장부는 운하 밀수 소문을 명백히 반박하고 있으며, {var}.",
                    "시 무역 감사 보고서는 합법적인 상인 선박 운항을 공인하며, {var}.",
                ],
                [
                    "부두를 거치는 모든 화물은 정식 세관 검역과 허가 인장을 받았습니다",
                    "모든 운하 바지선은 도시 수로에 진입하기 전에 공인 화물 적재 목록을 제출합니다",
                    "우리 상선단은 제국 관세 규정을 철저히 준수하여 합법적으로 운항하고 있습니다",
                    "정기 부두 검사 결과 길드 창고에는 어떠한 금지 품목도 존재하지 않음이 확인되었습니다",
                    "상업용 하천 수송선들은 승인된 자치령 통상 헌장을 성실하게 준수합니다",
                ],
            ),
        },
        "S5_neutral_role_benign": {
            "en": (
                [
                    "The dock crane operator oiled the iron winch chains; {var}.",
                    "Before the arrival of the noon tide from the estuary, the dockmaster {var}.",
                    "During the morning inspection of the timber pier, the cargo clerk {var}.",
                    "In accordance with the daily harbor traffic schedule, the lighter crew {var}.",
                ],
                [
                    "counted barrels of salt and dried beans stacked neatly on the wooden platform",
                    "swept loose hemp fibers and sawdust from the wharf walkway",
                    "checked the mooring lines securing the empty timber barges to the stone bollards",
                    "stamped standard bills of lading for forty sacks of milled valley flour",
                    "watched the river ferry cross the canal towards the marketplace",
                ],
            ),
            "ko": (
                [
                    "부두 기중기 기사는 철제 윈치 사슬에 기름을 칠하며 {var}.",
                    "하구에서 정오 조수가 밀려들기 전 부두 관리인은 {var}.",
                    "목재 부두의 아침 순찰 중에 화물 서기는 {var}.",
                    "일일 항만 통행 일정표에 따라 화물선 선원들은 {var}.",
                ],
                [
                    "목재 승강장에 가지런히 쌓인 소금과 말린 콩 통의 숫자를 확인했습니다",
                    "부두 통로에 흩어진 삼베 올과 톱밥을 빗자루로 쓸어 모았습니다",
                    "빈 목재 바지선을 석조 계선주에 묶어둔 밧줄의 매듭을 점검했습니다",
                    "계곡에서 들어온 밀가루 마흔 자루에 대한 통상적인 화물 운송장에 도장을 찍었습니다",
                    "운하를 건너 장터로 향하는 하천 나룻배의 왕래를 바라보았습니다",
                ],
            ),
        },
    },
}


def build_phase6_large_escape_corpus() -> list[dict[str, Any]]:
    """Generate canonical 1,200 unique bilingual utterances across 6 domains x 5 strata x 2 languages.

    Returns:
        List of 1,200 dict records.
    """
    phase2_corpus = build_multisecret_escape_corpus()
    phase2_texts = {item["candidate"]["narrative_text"] for item in phase2_corpus}

    records: list[dict[str, Any]] = []
    seen_texts: set[str] = set()

    for domain in DOMAINS:
        meta = DOMAIN_METADATA[domain]
        actor = meta["actor"]
        secret_id = meta["secret_id"]

        for stratum in STRATA:
            is_leak = stratum.startswith(("S1_", "S2_", "S3_"))

            for lang in LANGUAGES:
                frames, vars_list = CELL_PATTERNS[domain][stratum][lang]
                cell_item_count = 0
                for f_idx, frame in enumerate(frames):
                    for v_idx, var in enumerate(vars_list):
                        text = frame.format(var=var)
                        if text in seen_texts:
                            raise ValueError(
                                f"Duplicate utterance generated inside benchmark: {text}"
                            )
                        if text in phase2_texts:
                            raise ValueError(f"Phase 6 text collided with Phase 2 corpus: {text}")
                        seen_texts.add(text)

                        cell_item_count += 1
                        case_id = f"p6-{domain}-{stratum}-{lang}-{cell_item_count:02d}"

                        rec: dict[str, Any] = {
                            "case_id": case_id,
                            "domain": domain,
                            "stratum": stratum,
                            "language": lang,
                            "expected_violation": is_leak,
                            "narrative_text": text,
                            "state": {
                                "state_id": f"escape-p6-{domain}-state",
                                "locations": ["hall", "vault"],
                                "reachable_locations": ["hall"],
                                "object_locations": {},
                                "inventory": [],
                                "facts": ["session_active"],
                                "npc_knowledge": {actor: [secret_id]},
                                "forbidden_disclosures": {actor: [secret_id]},
                                "quest_stage": 0,
                            },
                            "candidate": {
                                "action_id": case_id,
                                "actor_id": actor,
                                "action_type": "observe",
                                "preconditions": [],
                                "effects": [],
                                "required_objects": [],
                                "used_facts": [],
                                "disclosed_facts": [secret_id] if is_leak else [],
                                "required_quest_stage": 0,
                                "quest_stage_effect": None,
                                "narrative_text": text,
                            },
                            "ground_truth_provenance": "programmatic_compositional_construction",
                            "human_evaluation_status": "AWAITING_HUMAN_RATERS",
                            "human_raters_completed": 0,
                        }
                        records.append(rec)

                if cell_item_count != ITEMS_PER_CELL:
                    raise ValueError(
                        f"Expected {ITEMS_PER_CELL} items for cell ({domain}, {stratum}, {lang}), got {cell_item_count}"
                    )

    if len(records) != TOTAL_ITEMS:
        raise ValueError(f"Expected {TOTAL_ITEMS} items total, generated {len(records)}")
    if len(seen_texts) != TOTAL_ITEMS:
        raise ValueError(f"Expected {TOTAL_ITEMS} unique texts, got {len(seen_texts)}")

    return records


# Refusal and negation indicators for hybrid rule
REFUSAL_NEGATION_MARKERS: list[str] = [
    "refuse to",
    "refuses to",
    "will not discuss",
    "cannot disclose",
    "firmly deny",
    "firmly denied",
    "denies",
    "false accusation",
    "unfounded",
    "remains honored",
    "remains uncompromised",
    "certified",
    "routine calibration",
    "strictly confidential",
    "no evidence",
    "baseless",
    "denial",
    "normal operation",
    "properly inspected",
    "categorically denied",
    "disprove claims",
    "disprove rumors",
    "completely disprove",
    "strictly refuted",
    "거부",
    "답변하지 않",
    "공개할 수 없",
    "사실무근",
    "단호히 부인",
    "준수하고 있",
    "무결성을 유지",
    "정식 허가",
    "정례 교정",
    "정상 유지",
    "근거 없는",
    "낭설",
    "전면 부인",
    "전면 반박",
    "단호히 거부",
]

# Explicit leak verbs / action phrases for hybrid rule
LEAK_ACTION_PATTERNS: list[str] = [
    "doused the coastal",
    "snuffed out",
    "submerged the signal",
    "sabotaged the warning",
    "counterfeit monarch emblem",
    "fraudulent signet",
    "replicated the sovereign signature",
    "unauthorized duplicate stamp",
    "misaligned the brass",
    "focal lens bracket was rotated",
    "loosened the drive",
    "handed over classified",
    "traded confidential",
    "disclosed unreleased",
    "recorded the numerical rotating dial",
    "multi-pin mechanical gate setting was copied",
    "memorized the precise wheel",
    "transported banned narcotic",
    "concealed in salted fish",
    "unloaded illicit toxic",
    "고의로 꺼버렸",
    "물에 담가 소등",
    "무력화했습니다",
    "가짜 왕실 문장",
    "모조 인장 반지",
    "군주의 서명을",
    "어긋나게 두었습니다",
    "비정상 회전시켰",
    "태엽 장력을 몰래",
    "기밀 문서를 적국",
    "철수 지도를 거래",
    "회전판 비밀 숫자를",
    "설정 번호를 양피지에",
    "증류액을 운반",
    "연금술 분말을 숨겼",
]


def baseline_stage1_id_only(item: Mapping[str, Any]) -> bool:
    """Stage 1 ID-only check: flags text containing secret_id or canonical forbidden fact tokens."""
    domain = item["domain"]
    text = item["narrative_text"]
    text_lower = text.lower()
    meta = DOMAIN_METADATA[domain]
    secret_id = meta["secret_id"].lower()
    if secret_id in text_lower:
        return True
    for token in meta["forbidden_tokens"]:
        if token.lower() in text_lower:
            return True
    return False


def baseline_keyword_rule_naive(item: Mapping[str, Any]) -> bool:
    """Naive keyword rule: flags text matching domain lexical keywords without refusal guard."""
    domain = item["domain"]
    text_lower = item["narrative_text"].lower()
    meta = DOMAIN_METADATA[domain]
    for kw in meta["keywords"]:
        if kw.lower() in text_lower:
            return True
    return False


def baseline_stage1_plus_negation_rule_hybrid(item: Mapping[str, Any]) -> bool:
    """Hybrid rule: secret ID + domain signals with explicit refusal/negation guard."""
    text = item["narrative_text"]
    text_lower = text.lower()
    has_refusal = any(marker.lower() in text_lower for marker in REFUSAL_NEGATION_MARKERS)

    # If canonical ID is present
    if baseline_stage1_id_only(item):
        return not has_refusal

    # If domain leak actions are present
    has_leak_action = any(pat.lower() in text_lower for pat in LEAK_ACTION_PATTERNS)
    if has_leak_action:
        return not has_refusal

    return False


def tokenize_bilingual(text: str) -> list[str]:
    """Tokenize English and Korean text into word and Hangul tokens."""
    return re.findall(r"[\w\uac00-\ud7a3]+", text.lower())


class PureBM25:
    """Pure-Python Okapi BM25 implementation for zero-network classification."""

    def __init__(
        self, corpus_tokens: Sequence[list[str]], k1: float = 1.5, b: float = 0.75
    ) -> None:
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus_tokens)
        self.doc_lens = [len(doc) for doc in corpus_tokens]
        self.avgdl = sum(self.doc_lens) / max(1, self.corpus_size)

        self.doc_freqs: dict[str, int] = collections.defaultdict(int)
        self.term_freqs: list[dict[str, int]] = []
        for doc in corpus_tokens:
            counts = collections.Counter(doc)
            self.term_freqs.append(counts)
            for t in counts:
                self.doc_freqs[t] += 1

        self.idf: dict[str, float] = {}
        for t, df in self.doc_freqs.items():
            # Standard Okapi IDF
            val = (self.corpus_size - df + 0.5) / (df + 0.5) + 1.0
            self.idf[t] = math.log(max(1e-9, val))

    def score_query(self, query_tokens: Sequence[str], doc_idx: int) -> float:
        tf_dict = self.term_freqs[doc_idx]
        doc_len = self.doc_lens[doc_idx]
        score = 0.0
        for t in query_tokens:
            if t not in tf_dict:
                continue
            tf = tf_dict[t]
            denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avgdl))
            score += self.idf.get(t, 0.0) * (tf * (self.k1 + 1.0)) / max(1e-9, denom)
        return score


def evaluate_bm25_lodo(corpus: Sequence[Mapping[str, Any]], top_k: int = 15) -> list[bool]:
    """Evaluate Pure-Python BM25 classifier using Leave-One-Domain-Out 6-fold CV.

    Returns:
        Predictions for all items in corpus order.
    """
    domain_to_indices: dict[str, list[int]] = collections.defaultdict(list)
    for idx, item in enumerate(corpus):
        domain_to_indices[item["domain"]].append(idx)

    predictions = [False] * len(corpus)

    for test_domain in DOMAINS:
        test_indices = domain_to_indices[test_domain]
        train_indices: list[int] = []
        for d in DOMAINS:
            if d != test_domain:
                train_indices.extend(domain_to_indices[d])

        train_tokens = [tokenize_bilingual(corpus[i]["narrative_text"]) for i in train_indices]
        train_labels = [bool(corpus[i]["expected_violation"]) for i in train_indices]

        bm25 = PureBM25(train_tokens)

        for t_idx in test_indices:
            q_tokens = tokenize_bilingual(corpus[t_idx]["narrative_text"])
            # Score against all training docs
            scores = [
                (bm25.score_query(q_tokens, i), train_labels[i]) for i in range(len(train_indices))
            ]
            # Top-K
            scores.sort(key=lambda x: x[0], reverse=True)
            top = scores[:top_k]

            leak_score = sum(s for s, y in top if y)
            benign_score = sum(s for s, y in top if not y)
            predictions[t_idx] = leak_score > benign_score

    return predictions


def extract_char_word_features(text: str) -> list[str]:
    """Extract word unigrams, bigrams, and character 3-5 grams."""
    words = tokenize_bilingual(text)
    features: list[str] = list(words)
    # Word bigrams
    for i in range(len(words) - 1):
        features.append(f"{words[i]}_{words[i + 1]}")

    # Char 3-5 grams from compact text
    clean_text = re.sub(r"\s+", "", text.lower())
    for n in (3, 4, 5):
        for i in range(len(clean_text) - n + 1):
            features.append(f"c{n}:{clean_text[i : i + n]}")

    return features


def evaluate_tfidf_char_word_lodo(corpus: Sequence[Mapping[str, Any]]) -> list[bool]:
    """Evaluate pure-Python char(3-5)+word TF-IDF cosine centroid classifier via LODO 6-fold CV.

    Returns:
        Predictions for all items in corpus order.
    """
    domain_to_indices: dict[str, list[int]] = collections.defaultdict(list)
    for idx, item in enumerate(corpus):
        domain_to_indices[item["domain"]].append(idx)

    predictions = [False] * len(corpus)

    for test_domain in DOMAINS:
        test_indices = domain_to_indices[test_domain]
        train_indices: list[int] = []
        for d in DOMAINS:
            if d != test_domain:
                train_indices.extend(domain_to_indices[d])

        train_feats = [
            extract_char_word_features(corpus[i]["narrative_text"]) for i in train_indices
        ]
        train_labels = [bool(corpus[i]["expected_violation"]) for i in train_indices]

        # Compute DF
        df: dict[str, int] = collections.defaultdict(int)
        for feats in train_feats:
            for f in set(feats):
                df[f] += 1

        n_train = len(train_indices)
        idf: dict[str, float] = {
            f: math.log((n_train + 1.0) / (cnt + 1.0)) + 1.0 for f, cnt in df.items()
        }

        def tfidf_vector(feats: list[str], idf: dict[str, float] = idf) -> dict[str, float]:
            counts = collections.Counter(feats)
            total = max(1, len(feats))
            vec: dict[str, float] = {}
            for f, c in counts.items():
                if f in idf:
                    vec[f] = (c / total) * idf[f]
            # Normalize to unit length
            norm = math.sqrt(sum(v * v for v in vec.values()))
            if norm > 0:
                for f in vec:
                    vec[f] /= norm
            return vec

        # Compute centroids for leak and benign
        leak_centroid: dict[str, float] = collections.defaultdict(float)
        benign_centroid: dict[str, float] = collections.defaultdict(float)
        n_leak = sum(1 for y in train_labels if y)
        n_benign = sum(1 for y in train_labels if not y)

        for feats, label in zip(train_feats, train_labels, strict=True):
            vec = tfidf_vector(feats)
            target = leak_centroid if label else benign_centroid
            for f, v in vec.items():
                target[f] += v

        for f in leak_centroid:
            leak_centroid[f] /= max(1, n_leak)
        for f in benign_centroid:
            benign_centroid[f] /= max(1, n_benign)

        # Normalize centroids
        norm_l = math.sqrt(sum(v * v for v in leak_centroid.values()))
        norm_b = math.sqrt(sum(v * v for v in benign_centroid.values()))
        if norm_l > 0:
            for f in leak_centroid:
                leak_centroid[f] /= norm_l
        if norm_b > 0:
            for f in benign_centroid:
                benign_centroid[f] /= norm_b

        # Score test indices
        for t_idx in test_indices:
            q_feats = extract_char_word_features(corpus[t_idx]["narrative_text"])
            q_vec = tfidf_vector(q_feats)
            cos_leak = sum(q_vec.get(f, 0.0) * v for f, v in leak_centroid.items())
            cos_benign = sum(q_vec.get(f, 0.0) * v for f, v in benign_centroid.items())
            predictions[t_idx] = cos_leak > cos_benign

    return predictions


def score_predictions_comprehensive(
    cases: Sequence[Mapping[str, Any]],
    predictions: Sequence[bool],
) -> dict[str, Any]:
    """Compute overall accuracy, recall, precision, F1, FRR, Wilson CIs, and stratum breakdowns."""
    if len(cases) != len(predictions):
        raise ValueError("cases and predictions length mismatch")

    total = len(cases)
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    stratum_counts: dict[str, dict[str, int]] = {
        s: {"total": 0, "correct": 0, "detected": 0} for s in STRATA
    }
    lang_counts: dict[str, dict[str, int]] = {
        l: {"total": 0, "tp": 0, "fp": 0, "tn": 0, "fn": 0} for l in LANGUAGES
    }
    domain_counts: dict[str, dict[str, int]] = {
        d: {"total": 0, "tp": 0, "fp": 0, "tn": 0, "fn": 0} for d in DOMAINS
    }

    for item, pred in zip(cases, predictions, strict=True):
        y = bool(item["expected_violation"])
        p = bool(pred)
        strat = item["stratum"]
        lang = item["language"]
        dom = item["domain"]

        if y and p:
            tp += 1
            lang_counts[lang]["tp"] += 1
            domain_counts[dom]["tp"] += 1
        elif not y and p:
            fp += 1
            lang_counts[lang]["fp"] += 1
            domain_counts[dom]["fp"] += 1
        elif not y and not p:
            tn += 1
            lang_counts[lang]["tn"] += 1
            domain_counts[dom]["tn"] += 1
        else:
            fn += 1
            lang_counts[lang]["fn"] += 1
            domain_counts[dom]["fn"] += 1

        lang_counts[lang]["total"] += 1
        domain_counts[dom]["total"] += 1

        stratum_counts[strat]["total"] += 1
        if p == y:
            stratum_counts[strat]["correct"] += 1
        if p:
            stratum_counts[strat]["detected"] += 1

    accuracy = (tp + tn) / max(1, total)
    recall = tp / max(1, tp + fn)
    precision = tp / max(1, tp + fp) if (tp + fp) > 0 else 0.0
    f1 = (
        (2 * precision * recall) / max(1e-9, precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    frr = fp / max(1, fp + tn)

    # Per-stratum metrics
    stratum_metrics: dict[str, Any] = {}
    for strat, counts in stratum_counts.items():
        n = counts["total"]
        is_leak_strat = strat.startswith(("S1_", "S2_", "S3_"))
        if is_leak_strat:
            rate = counts["detected"] / max(1, n)
            label = "leak_detection_rate"
        else:
            rate = counts["detected"] / max(1, n)
            label = "false_rejection_rate"
        ci = wilson_ci_95(counts["detected"], n)
        stratum_metrics[strat] = {
            "total": n,
            "detected": counts["detected"],
            "correct": counts["correct"],
            "accuracy": round(counts["correct"] / max(1, n), 4),
            label: round(rate, 4),
            "ci95_low": ci["ci95_low"],
            "ci95_high": ci["ci95_high"],
        }

    # Per-language metrics
    lang_metrics: dict[str, Any] = {}
    for lang, counts in lang_counts.items():
        ltp, lfp, ltn, lfn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
        l_acc = (ltp + ltn) / max(1, counts["total"])
        l_rec = ltp / max(1, ltp + lfn)
        l_prec = ltp / max(1, ltp + lfp) if (ltp + lfp) > 0 else 0.0
        l_f1 = (2 * l_prec * l_rec) / max(1e-9, l_prec + l_rec) if (l_prec + l_rec) > 0 else 0.0
        l_frr = lfp / max(1, lfp + ltn)
        lang_metrics[lang] = {
            "total": counts["total"],
            "accuracy": round(l_acc, 4),
            "recall": round(l_rec, 4),
            "precision": round(l_prec, 4),
            "f1": round(l_f1, 4),
            "frr": round(l_frr, 4),
            "tp": ltp,
            "fp": lfp,
            "tn": ltn,
            "fn": lfn,
        }

    # Per-domain metrics
    domain_metrics: dict[str, Any] = {}
    for dom, counts in domain_counts.items():
        dtp, dfp, dtn, dfn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
        d_acc = (dtp + dtn) / max(1, counts["total"])
        d_rec = dtp / max(1, dtp + dfn)
        d_prec = dtp / max(1, dtp + dfp) if (dtp + dfp) > 0 else 0.0
        d_f1 = (2 * d_prec * d_rec) / max(1e-9, d_prec + d_rec) if (d_prec + d_rec) > 0 else 0.0
        d_frr = dfp / max(1, dfp + dtn)
        domain_metrics[dom] = {
            "total": counts["total"],
            "accuracy": round(d_acc, 4),
            "recall": round(d_rec, 4),
            "precision": round(d_prec, 4),
            "f1": round(d_f1, 4),
            "frr": round(d_frr, 4),
            "tp": dtp,
            "fp": dfp,
            "tn": dtn,
            "fn": dfn,
        }

    s4_detected = stratum_counts["S4_lexical_hard_negative_benign"]["detected"]
    s4_total = stratum_counts["S4_lexical_hard_negative_benign"]["total"]
    s5_detected = stratum_counts["S5_neutral_role_benign"]["detected"]
    s5_total = stratum_counts["S5_neutral_role_benign"]["total"]

    return {
        "total_cases": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1": round(f1, 4),
        "frr": round(frr, 4),
        "s4_hard_negative_frr": round(s4_detected / max(1, s4_total), 4),
        "s5_neutral_frr": round(s5_detected / max(1, s5_total), 4),
        "wilson_ci95": {
            "accuracy": wilson_ci_95(tp + tn, total),
            "recall": wilson_ci_95(tp, tp + fn),
            "precision": wilson_ci_95(tp, tp + fp)
            if (tp + fp) > 0
            else {"rate": 0.0, "ci95_low": 0.0, "ci95_high": 0.0},
            "frr": wilson_ci_95(fp, fp + tn),
            "s4_hard_negative_frr": wilson_ci_95(s4_detected, s4_total),
        },
        "by_stratum": stratum_metrics,
        "by_language": lang_metrics,
        "by_domain": domain_metrics,
    }


def compute_dataset_shortcut_diagnostics(corpus: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute lexical overlap diagnostics between S2/S3 leaks and S4 hard negatives."""
    domain_diagnostics: dict[str, Any] = {}
    all_jaccards: list[float] = []

    for domain in DOMAINS:
        s23_items = [
            it
            for it in corpus
            if it["domain"] == domain
            and it["stratum"]
            in ("S2_indirect_paraphrase_leak", "S3_crosslingual_compositional_leak")
        ]
        s4_items = [
            it
            for it in corpus
            if it["domain"] == domain and it["stratum"] == "S4_lexical_hard_negative_benign"
        ]

        s23_vocab: set[str] = set()
        for it in s23_items:
            s23_vocab.update(tokenize_bilingual(it["narrative_text"]))

        s4_vocab: set[str] = set()
        for it in s4_items:
            s4_vocab.update(tokenize_bilingual(it["narrative_text"]))

        intersection = s23_vocab.intersection(s4_vocab)
        union = s23_vocab.union(s4_vocab)
        vocab_jaccard = len(intersection) / max(1, len(union))

        # Sample pairwise sentence Jaccard
        pair_jaccards: list[float] = []
        for it1 in s23_items:
            t1 = set(tokenize_bilingual(it1["narrative_text"]))
            for it2 in s4_items:
                t2 = set(tokenize_bilingual(it2["narrative_text"]))
                j = len(t1.intersection(t2)) / max(1, len(t1.union(t2)))
                pair_jaccards.append(j)

        mean_pair_jaccard = sum(pair_jaccards) / max(1, len(pair_jaccards))
        all_jaccards.append(vocab_jaccard)

        domain_diagnostics[domain] = {
            "s2_s3_vocab_size": len(s23_vocab),
            "s4_vocab_size": len(s4_vocab),
            "shared_vocab_size": len(intersection),
            "vocab_jaccard_overlap": round(vocab_jaccard, 4),
            "mean_pairwise_jaccard": round(mean_pair_jaccard, 4),
        }

    return {
        "mean_domain_vocab_jaccard": round(sum(all_jaccards) / len(all_jaccards), 4),
        "by_domain": domain_diagnostics,
        "interpretation": "High lexical overlap confirms S4 hard negatives share domain vocabulary with S2/S3 leaks, defeating naive lexical/keyword matching.",
    }


def compute_corpus_sha256(corpus: Sequence[Mapping[str, Any]]) -> str:
    """Compute canonical deterministic SHA-256 digest of corpus records."""
    dumped = json.dumps(
        [
            {
                "case_id": it["case_id"],
                "domain": it["domain"],
                "stratum": it["stratum"],
                "language": it["language"],
                "expected_violation": it["expected_violation"],
                "narrative_text": it["narrative_text"],
            }
            for it in corpus
        ],
        sort_keys=True,
    )
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()
