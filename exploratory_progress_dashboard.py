#!/usr/bin/env python3
"""Loopback-only, read-only view of exploratory experiment progress."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATE = Path(__file__).resolve().parent / "exploratory_signal_progress.json"
PILOT_STATE = Path(__file__).resolve().parent / "neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/codex-feedback-pilot-20261110/status.json"
PILOT_RESULTS = PILOT_STATE.with_name("results.json")
PAGE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>시그널 비교 실험 진행</title><style>
body{font:16px/1.6 system-ui,sans-serif;background:#f5f6f8;color:#18212e;margin:0}main{max-width:820px;margin:auto;padding:32px 20px}h1{font-size:1.7rem}article{background:white;border:1px solid #dce1e8;border-radius:10px;padding:16px;margin:12px 0}strong{display:block;font-size:1.1rem}.status{font-weight:700}.detail{white-space:pre-wrap}small{color:#475569}#error{color:#9b1c1c}
</style></head><body><main><h1>연구 진행 상황</h1><p>개발용 파일럿, 미완료 연구 및 과거 탐색을 구분합니다. 상태 파일을 2초마다 읽습니다.</p><section id="pilot" aria-label="개발용 파일럿" aria-live="polite"></section><h2>기존 연구 및 과거 탐색</h2><p id="summary" aria-live="polite">상태 확인 중</p><div id="error" role="alert"></div><section id="tasks" aria-label="할 일"></section><p id="receipt"></p><small>모델 신원과 비용은 관측된 경우에만 확인됩니다.</small></main><script>
const labels={pending:'대기',running:'진행 중',completed:'완료',blocked:'중단 / 차단',failed:'실패'};
function text(tag, value, cls){const el=document.createElement(tag);el.textContent=value;if(cls)el.className=cls;return el}
const cohortsSection=document.createElement('section');cohortsSection.setAttribute('aria-label','신규 개발용 코호트');document.querySelector('#pilot').before(cohortsSection);
function runState(run){return run.status==='COMPLETED'&&run.failed>0?'종료 (실패 포함)':({AWAITING_REVIEW:'검토 대기',RUNNING:'기록상 진행 중 (프로세스 생존 미확인)',COMPLETED:'완료',COMPLETED_WITH_FAILURES:'종료 (실패 포함)',STOPPED:'중단',FAILED:'실패',PENDING:'대기'}[run.status] || '미확인')}
function counts(card, conditions){if(!conditions){card.append(text('p','조건별 집계: 미확인'));return}for(const [key,label] of [['detailed','상세'],['generic','일반']]){const c=conditions[key];card.append(text('p',label+' · 할당 '+c.assigned+' · 완료 '+c.completed+' · 실패 '+c.failed+' · 대기 '+c.pending+' · 진행 중 '+c.running+' · 기타 '+c.unknown))}}
async function refreshCohorts(){try{const response=await fetch('/status',{cache:'no-store'});if(!response.ok)throw new Error();const data=await response.json();cohortsSection.replaceChildren(text('h2','개발용 코호트'));cohortsSection.append(text('p','진단 코호트와 이전 evidence 실행, 준비 코호트 및 과거 실패 기록은 별개입니다. 확증 holdout 또는 인간 평가가 아닙니다. 기록된 실행 상태는 프로세스 생존을 보증하지 않습니다.'));for(const item of data.cohorts || []){const card=document.createElement('article');card.append(text('strong',item.model));card.append(text('p',item.kind==='diagnostic'?'신규 v2 진단 코호트':item.kind==='v2'?'이전 v2 evidence 실행':item.kind==='superseded'?'이전 v2 코호트 · 소스 변경으로 대체됨':item.kind==='native'?'이전 native 0.167.0 준비 코호트':'이전 0.147.0 준비 코호트'));if(item.run){const r=item.run;card.append(text('p','기록된 상태: '+runState(r)+' · 갱신: '+(r.updated_at || '미확인')));card.append(text('p','계획 '+(r.planned ?? '미확인')+' · 완료 '+(r.completed ?? '미확인')+' · 실패 '+(r.failed ?? '미확인')+' · 미종결 '+(r.pending ?? '미확인')));card.append(text('p','실제 응답 모델: '+(r.actual_model_identity ?? '미확인')+' · 비용 USD: '+(r.cost_usd ?? '미확인')))}else card.append(text('p','실행 상태: 미확인'));counts(card,item.conditions);cohortsSection.append(card)}}catch(e){cohortsSection.replaceChildren(text('p','개발용 코호트 상태 미확인'))}}refreshCohorts();setInterval(refreshCohorts,2000);
function renderPilot(pilot){const section=document.querySelector('#pilot');section.replaceChildren();const card=document.createElement('article');card.append(text('strong','과거 개발용 파일럿 (신규 코호트와 별개)'));card.append(text('p',pilot?.scope_note || '개발용 파일럿; 확증 결과가 아닙니다.'));const run=pilot?.run;if(!run){card.append(text('p','실행 상태: 미확인'));section.append(card);return}card.append(text('p','요청 모델 선택자: '+(run.model_selector ?? '미확인')+' · 실제 응답 모델: '+(run.actual_model_identity ?? '미확인')));card.append(text('p','기록된 실행 상태: '+runState(run)+' · 갱신: '+(run.updated_at || '미확인')));card.append(text('p','계획 '+(run.planned ?? '미확인')+' · 완료 '+(run.completed ?? '미확인')+' · 실패 '+(run.failed ?? '미확인')+' · 미종결 '+(run.pending ?? '미확인')));counts(card,pilot.conditions);section.append(card)}
async function refresh(){try{const res=await fetch('/status',{cache:'no-store'});if(!res.ok)throw new Error('상태 파일을 읽을 수 없습니다 (HTTP '+res.status+').');const data=await res.json();if(!Array.isArray(data.tasks))throw new Error('상태 파일의 작업 목록이 유효하지 않습니다.');renderPilot(data.pilot);document.querySelector('#error').textContent='';document.querySelector('#summary').textContent='작업 보고 스냅샷: '+(labels[data.status] || '미확인')+' · 보고 시각: '+(data.updated_at || '미확인');const target=document.querySelector('#tasks');target.replaceChildren();for(const task of data.tasks){const card=document.createElement('article');card.append(text('strong',task.label || task.id || '이름 미확인'));card.append(text('span','상태: '+(labels[task.status] || '미확인'),'status'));if(task.detail)card.append(text('p',task.detail,'detail'));target.append(card)}}catch(e){document.querySelector('#summary').textContent='전체 상태 미확인';document.querySelector('#error').textContent=e.message;document.querySelector('#pilot').replaceChildren();document.querySelector('#tasks').replaceChildren(text('article','상태 파일이 없어 작업 목록을 확인할 수 없습니다.'))}}refresh();setInterval(refresh,2000);
</script></body></html>'''

def load_run(path):
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(run, dict):
            return None
        result = {key: run.get(key) for key in ("status", "updated_at", "planned", "completed", "failed", "pending")}
        result["model_selector"] = run.get("model_selector") if run.get("model_selector") in ("gpt-6-luna", "gpt-5.6-luna", "gpt-5.6-terra") else None
        result["actual_model_identity"] = run.get("actual_model_identity") if run.get("actual_model_identity") in ("gpt-5.6-luna", "gpt-5.6-terra") else None
        cost = run.get("cost_usd")
        result["cost_usd"] = cost if type(cost) in (int, float) else None
        return result
    except (OSError, ValueError):
        return None


def condition_counts(path):
    try:
        records = json.loads(path.read_text(encoding="utf-8"))["cases"]
        if not isinstance(records, list):
            return None
        counts = {condition: dict.fromkeys(("assigned", "completed", "failed", "pending", "running", "unknown"), 0) for condition in ("detailed", "generic")}
        for record in records:
            condition = record["condition"]
            if condition not in counts:
                return None
            group = counts[condition]
            group["assigned"] += 1
            state = {"COMPLETED": "completed", "FAILED": "failed", "PENDING": "pending", "IN_PROGRESS": "running"}.get(record.get("status"), "unknown")
            group[state] += 1
        return counts
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get_all("Host") != [f"127.0.0.1:{self.server.server_port}"]:
            self.send_error(403, "Invalid Host")
            return
        if self.path == "/":
            body, status, content_type = PAGE.encode(), 200, "text/html; charset=utf-8"
        elif self.path == "/status":
            try:
                data = json.loads(STATE.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
                    raise ValueError("invalid status structure")
                if isinstance(data.get("pilot"), dict):
                    pilot = data["pilot"]
                    data["pilot"] = {"scope_note": pilot.get("scope_note"), "run": load_run(PILOT_STATE), "conditions": condition_counts(PILOT_RESULTS)}
                data.pop("receipt_path", None)
                data["cohorts"] = []
                for directory_name, model, kind in (
                    ("codex-feedback-pilot-v2-diagnostic-20261110-luna", "gpt-5.6-luna", "diagnostic"),
                    ("codex-feedback-pilot-v2-diagnostic-20261110-terra", "gpt-5.6-terra", "diagnostic"),
                    ("codex-feedback-pilot-v2-evidence-20261110-luna", "gpt-5.6-luna", "v2"),
                    ("codex-feedback-pilot-v2-evidence-20261110-terra", "gpt-5.6-terra", "v2"),
                    ("codex-feedback-pilot-v2-20261110-luna", "gpt-5.6-luna", "superseded"),
                    ("codex-feedback-pilot-v2-20261110-terra", "gpt-5.6-terra", "superseded"),
                    ("gpt-5.6-luna-native-0.167.0", "gpt-5.6-luna", "native"),
                    ("gpt-5.6-terra-native-0.167.0", "gpt-5.6-terra", "native"),
                    ("gpt-5.6-luna", "gpt-5.6-luna", "old"),
                    ("gpt-5.6-terra", "gpt-5.6-terra", "old"),
                ):
                    directory = PILOT_STATE.parent.parent / directory_name
                    cohort = {"model": model, "kind": kind, "run": load_run(directory / "status.json"), "conditions": condition_counts(directory / "results.json")}
                    data["cohorts"].append(cohort)
                body, status = json.dumps(data, ensure_ascii=False).encode(), 200
            except (OSError, ValueError):
                body, status = b'{"error":"status unavailable"}', 503
            content_type = "application/json; charset=utf-8"
        else:
            body, status, content_type = b"Not found", 404, "text/plain; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
