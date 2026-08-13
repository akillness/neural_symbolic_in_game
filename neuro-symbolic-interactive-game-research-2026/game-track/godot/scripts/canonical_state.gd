class_name ExperimentalCanonicalState
extends RefCounted

## Canonical JSON used only for deterministic state and artifact-integrity hashes.
## This is an unkeyed SHA-256 checksum, not authentication or writer identity.

static func canonicalize(value: Variant) -> Variant:
	if value is Dictionary:
		var ordered := {}
		var keys: Array = value.keys()
		keys.sort()
		for key in keys:
			ordered[str(key)] = canonicalize(value[key])
		return ordered
	if value is Array:
		var items: Array = []
		for item in value:
			items.append(canonicalize(item))
		return items
	return value


static func canonical_json(value: Variant) -> String:
	return JSON.stringify(canonicalize(value), "", false)


static func sha256(value: Variant) -> String:
	var bytes := canonical_json(value).to_utf8_buffer()
	var context := HashingContext.new()
	var start_error := context.start(HashingContext.HASH_SHA256)
	if start_error != OK:
		push_error("cannot initialize SHA-256 context")
		return ""
	var update_error := context.update(bytes)
	if update_error != OK:
		push_error("cannot update SHA-256 context")
		return ""
	return context.finish().hex_encode()


static func sorted_unique(values: Array) -> Array:
	var index := {}
	for value in values:
		index[str(value)] = true
	var result: Array = index.keys()
	result.sort()
	return result
