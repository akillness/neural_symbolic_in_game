class_name Interactable3D
extends Area3D

## Proximity interaction marker. Purely presentational: it proposes intents to the
## root controller and never mutates canonical state itself (GDI-01).

signal focus_changed(interactable: Interactable3D, focused: bool)

@export var interaction_id: String = ""
@export var display_name: String = ""
@export var prompt_text: String = ""
var enabled: bool = true


static func create(id: String, name_text: String, prompt: String, radius: float = 2.2) -> Interactable3D:
	var area := Interactable3D.new()
	area.interaction_id = id
	area.display_name = name_text
	area.prompt_text = prompt
	area.name = "Interact_%s" % id
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = radius
	shape.shape = sphere
	area.add_child(shape)
	area.collision_layer = 4
	area.collision_mask = 0
	return area
