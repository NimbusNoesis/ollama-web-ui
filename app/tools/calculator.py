"""Simple calculator tool for testing."""

import ast
import operator
import math
from typing import Any, Dict


def calculator(expression: str) -> Dict[str, Any]:
    """
    Perform mathematical calculations

    Args:
        expression: The mathematical expression to evaluate

    Returns:
        Result of the tool execution
    """
    try:
        if expression is None:
            raise ValueError("expression is required")

        # Define safe operations
        safe_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.BitXor: operator.xor,
            ast.USub: operator.neg,
            ast.Mod: operator.mod,  # Support for modulo operation
        }

        # Define allowed constants
        math_constants = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "inf": math.inf,
            "nan": math.nan,
        }

        def safe_eval(expr):
            return eval_(ast.parse(expr, mode="eval").body)

        def eval_(node):
            if isinstance(node, ast.Num):
                # For Python < 3.8
                return node.n
            elif isinstance(node, ast.Constant):
                # For Python >= 3.8
                return node.value
            elif isinstance(node, ast.Name):
                # Handle constants like pi, e
                if node.id in math_constants:
                    return math_constants[node.id]
                raise ValueError(f"Unknown variable: {node.id}")
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type not in safe_operators:
                    raise ValueError(
                        f"Unsupported operation: {node.op.__class__.__name__}"
                    )
                return safe_operators[op_type](eval_(node.left), eval_(node.right))
            elif isinstance(node, ast.UnaryOp):
                op_type = type(node.op)
                if op_type not in safe_operators:
                    raise ValueError(
                        f"Unsupported operation: {node.op.__class__.__name__}"
                    )
                return safe_operators[op_type](eval_(node.operand))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                # Support for basic math functions
                func_name = node.func.id
                if not hasattr(math, func_name):
                    raise ValueError(f"Unknown math function: {func_name}")

                args = [eval_(arg) for arg in node.args]
                return getattr(math, func_name)(*args)
            else:
                raise ValueError(f"Unsupported expression type: {type(node).__name__}")

        result = safe_eval(expression)
        return {"result": result}
    except Exception as e:
        # Handle exceptions appropriately
        return {"error": str(e)}


# Example usage:
# result = calculator(expression="2 + 3 * 4")
# result = calculator(expression="sin(pi/2)")
# result = calculator(expression="sqrt(16) + log(10)")
