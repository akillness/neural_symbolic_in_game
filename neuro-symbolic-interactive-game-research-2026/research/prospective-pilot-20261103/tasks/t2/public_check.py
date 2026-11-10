def check(api):
    c, validator = api["contracts"], api["validator"]
    state = c.WorldState("public-stage", frozenset({"dock"}), frozenset({"dock"}), {},
                         frozenset(), frozenset(), quest_stage=2,
                         action_policies={"MOVE": c.ActionPolicy(frozenset(), frozenset(),
                             allowed_quest_stage_effects=frozenset({1, 2}))})
    for stage, expected in ((1, {"QUEST_STAGE_REGRESSION"}), (2, set())):
        candidate = c.CandidateAction("public", "captain", "MOVE", frozenset(), frozenset(),
                                      quest_stage_effect=stage)
        result = validator.validate_candidate(state, candidate)
        assert {error.code for error in result.errors} == expected
        assert result.valid is (not expected)
