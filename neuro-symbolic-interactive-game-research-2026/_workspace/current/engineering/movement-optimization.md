# Movement optimization / 이동 최적화

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Status: `N/A — documented scope boundary`

The approved slice is turn-based and headless; it has no real-time locomotion, pathfinding, camera,
or combat. Reachability is an encoded set membership check (`lamp_store` is reachable from the
initial harbor state). Adding movement would introduce an unapproved confound into the primary
structured-state experiment. A later desktop debug surface may visualize the same state without
changing the commit protocol.

