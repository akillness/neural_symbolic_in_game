"""Modular multi-hop ontology closure and external shielding baselines for TRACE-RPG."""

from .validator import (
    DatalogClosureResult,
    MultihopOntologySpec,
    compute_datalog_closure,
    evaluate_action_mask_shield,
    evaluate_dialog_rail_filter,
    execute_with_multihop_repair,
    validate_candidate_multihop,
)

__all__ = [
    "DatalogClosureResult",
    "MultihopOntologySpec",
    "compute_datalog_closure",
    "evaluate_action_mask_shield",
    "evaluate_dialog_rail_filter",
    "execute_with_multihop_repair",
    "validate_candidate_multihop",
]
