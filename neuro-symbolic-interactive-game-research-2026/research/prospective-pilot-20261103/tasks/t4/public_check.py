import hashlib
import json

def check(api):
    c, runtime = api["contracts"], api["runtime"]
    state = c.WorldState("public-replay", frozenset({"dock"}), frozenset({"dock"}), {},
                         frozenset(), frozenset(), action_policies={"MOVE": c.ActionPolicy(frozenset(), frozenset({"open"}))})
    candidate = c.CandidateAction("public", "captain", "MOVE", frozenset(), frozenset({"open"}))
    record = runtime.to_jsonable(runtime.execute_with_repair(state, candidate))
    assert runtime.to_jsonable(runtime.replay_trace_record(record))["facts"] == ["open"]
    record["state"]["facts"] = ["impossible"]
    payload = {key: value for key, value in record.items() if key != "trace_hash"}
    record["trace_hash"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    try:
        runtime.replay_trace_record(record)
    except ValueError:
        return
    raise AssertionError("rehashed impossible facts accepted")
