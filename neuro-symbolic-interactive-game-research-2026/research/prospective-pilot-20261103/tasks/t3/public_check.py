def check(api):
    c, repair = api["contracts"], api["repair"]
    candidate = c.CandidateAction("public", "captain", "MOVE", frozenset(), frozenset({"keep"}))
    errors = c.ValidationResult(False, (c.ValidationError("POLICY_EFFECT_OMISSION", "needed", "public", "public"),), ())
    result = repair.counterexample_guided_repair(None, candidate, errors, 1)
    assert result.effects == frozenset({"keep", "needed"})
    assert repair.counterexample_guided_repair(None, result, errors, 2) == result
