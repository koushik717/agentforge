"""Calculator tool for mathematical expressions."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

import structlog

from tools import BaseTool

logger = structlog.get_logger(__name__)

# Safe operators for expression evaluation
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "pi": math.pi,
    "e": math.e,
    "ceil": math.ceil,
    "floor": math.floor,
}


class Calculator(BaseTool):
    """Safely evaluate mathematical expressions."""

    name = "calculator"
    description = (
        "Evaluate mathematical expressions safely. Supports basic arithmetic "
        "(+, -, *, /, **, %), and functions (sqrt, abs, sin, cos, tan, log, round, ceil, floor). "
        "Constants: pi, e."
    )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate, e.g. '(2 + 3) * sqrt(16)'",
                },
            },
            "required": ["expression"],
        }

    async def execute(self, *, expression: str) -> str:
        """Safely evaluate a math expression."""
        logger.info("tool.calculator", expression=expression)
        try:
            result = self._safe_eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Error evaluating '{expression}': {str(e)}"

    def _safe_eval(self, expression: str) -> float | int:
        """Parse and evaluate expression using AST — no exec/eval."""
        tree = ast.parse(expression, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> float | int:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {node.value}")

        elif isinstance(node, ast.Name):
            if node.id in _SAFE_FUNCTIONS:
                val = _SAFE_FUNCTIONS[node.id]
                if isinstance(val, (int, float)):
                    return val
            raise ValueError(f"Unknown variable: {node.id}")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return _SAFE_OPERATORS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return _SAFE_OPERATORS[op_type](operand)

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCTIONS:
                func = _SAFE_FUNCTIONS[node.func.id]
                if callable(func):
                    args = [self._eval_node(arg) for arg in node.args]
                    return func(*args)
            raise ValueError(f"Unsupported function: {ast.dump(node.func)}")

        raise ValueError(f"Unsupported expression: {ast.dump(node)}")
