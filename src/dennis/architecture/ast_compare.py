import ast
import copy
from pathlib import Path
import hashlib


def collect_project_functions(root):

    functions = []

    root = Path(root)

    for py_file in root.rglob("*.py"):

        try:

            functions.extend(
                collect_functions(py_file)
            )

        except Exception:

            pass

    return functions

def normalize_function(node):

    node = copy.deepcopy(node)

    node.name = "__NORMALIZED__"

    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(
            node.body[0].value,
            ast.Constant
        )
        and isinstance(
            node.body[0].value.value,
            str
        )
    ):
        node.body.pop(0)

    return node

def canonical_ast(node):

    return ast.dump(
        node,
        annotate_fields=False,
        include_attributes=False
    )

def extract_source_excerpt(
    source_lines,
    node
):

    return source_lines[
        node.lineno - 1:
        node.end_lineno
    ]

def collect_functions(path):

    source = open(
        path,
        encoding="utf-8"
    ).read()

    source_lines = source.splitlines()

    tree = ast.parse(source)

    functions = []

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):

            functions.append(
                {
                    "name": node.name,
                    "file": str(path),

                    "start_line": node.lineno,
                    "end_line": node.end_lineno,

                    "line_count":
                        node.end_lineno - node.lineno + 1,

                    "source_excerpt":
                        extract_source_excerpt(
                            source_lines,
                            node
                        ),

                    "signature":
                        canonical_ast(
                            normalize_function(node)
                        )
                }
            )

    return functions

from collections import defaultdict

def detect_duplicate_ast_candidates(root):

    groups = defaultdict(list)

    for func in collect_project_functions(root):

        groups[
            func["signature"]
        ].append(func)

    findings = []

    for funcs in groups.values():

        if len(funcs) < 2:
            continue

        group_hash = hashlib.sha256(
            funcs[0]["signature"].encode("utf-8")
        ).hexdigest()

        findings.append(
            {
                "type":
                    "ARCHITECTURE.DUPLICATE_AST_CANDIDATE",

                "evidence": {
                    "normalized_hash":
                        group_hash,
                
                    "count":
                        len(funcs),

                    "count":
                        len(funcs),

                    "total_lines":
                        sum(
                            f["line_count"]
                            for f in funcs
                        ),

                    "functions":
                        [
                            {
                                k: v
                                for k, v in func.items()
                                if k != "signature"
                            }
                            for func in funcs
                        ],
                
            },
            "confidence": 1.0,
            }
        )

    return findings