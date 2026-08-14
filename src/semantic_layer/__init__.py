"""finaudit 语义层（L1）。

口径定义的结构契约与机械校验器。**不含任何 Agent**——D-002 要求语义层在没有
Agent 的情况下独立成立并可展示。
"""

from .definition import MetricDefinition, load_definition, iter_definition_paths
from .dsl import Condition, DslError, MissingOperandError, evaluate, parse_condition
from .validate import Finding, validate_definition, validate_paths
from .vocabulary import Vocabulary, load_vocabulary

__all__ = [
    "MetricDefinition",
    "load_definition",
    "iter_definition_paths",
    "Condition",
    "DslError",
    "MissingOperandError",
    "evaluate",
    "parse_condition",
    "Finding",
    "validate_definition",
    "validate_paths",
    "Vocabulary",
    "load_vocabulary",
]
