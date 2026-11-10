def check(mapping):
    actor = next(role for role in mapping["roles"] if role["id"] == "actor")
    meanings = mapping["disclosure_rule_meanings"]
    rules = actor["rule_ids"]
    assert len(rules) == 2 and len(set(rules)) == 2
    assert any("eligible actor" in meanings[rule] for rule in rules)
    assert any("denial preserves" in meanings[rule].lower() for rule in rules)
