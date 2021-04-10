import re
import sys
import os
import ast
from collections import defaultdict

from typing import Dict


class PepAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats: Dict[str, Dict[int, list]] = {
            "variables": defaultdict(list),
            "parameters": defaultdict(list),
            "is_constant_default": defaultdict(list),
        }

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.stats["variables"][node.lineno].append(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        for a in node.args.args:
            self.stats["parameters"][node.lineno].append(a.arg)
        for a in node.args.defaults:
            self.stats["is_constant_default"][node.lineno].append(isinstance(a, ast.Constant))
        self.generic_visit(node)

    def get_parameters(self, lineno: int) -> list:
        return self.stats["parameters"][lineno]

    def get_variables(self, lineno: int) -> list:
        return self.stats["variables"][lineno]

    def get_mutable_defaults(self, lineno: int) -> str:
        for param_name, is_default in zip(self.stats["parameters"][lineno], self.stats["is_constant_default"][lineno]):
            if not is_default:
                return param_name
        return ""


path = sys.argv[1]
all_files = []
if os.path.isdir(path):
    for name in sorted(os.listdir(path)):
        if name.endswith(".py"):
            all_files.append(os.path.join(path, name))
else:
    all_files.append(path)
for files in all_files:
    with open(files) as file:
        counter = 0
        tree = ast.parse(file.read())
        pep_analyzer = PepAnalyzer()
        pep_analyzer.visit(tree)
        file.seek(0)
        for n, line in enumerate(file, 1):
            if line == "\n":
                counter += 1
                continue
            if len(line) > 79:
                print(f"{files}: Line {n}: S001 Too long")
            if (len(line) - len(line.lstrip())) % 4 != 0:
                print(f"{files}: Line {n}: S002 Indentation is not a multiple of four")
            if re.search(r"^([^#])*;(?!\S)", line):
                print(f"{files}: Line {n}: S003 Unnecessary semicolon")
            if "#" in line and line.lstrip()[0] != "#" and line.index("#") - len(line[:line.index("#")].rstrip()) < 2:
                print(f"{files}: Line {n}: S004 At least two spaces required before inline comments")
            if re.search(r"(?i)# *todo", line):
                print(f"{files}: Line {n}: S005 TODO found")
            if counter > 2:
                print(f"{files}: Line {n}: S006 More than two blank lines used before this line")
                counter = 0
            if line != "\n":
                counter = 0
            if match := re.match(r"(class|def)(\s){2,}(\w+)", line.lstrip()):
                print(f"{files}: Line {n}: S007 Too many spaces after '{match.group(2)}'")

            if match := re.match(r"class\s+([a-zA-z]+)", line.lstrip()):
                s = match.group(1)
                if not (s != s.lower() and s != s.upper() and "_" not in s):
                    print(f"{files}: Line {n}: S008 Class name '{s}' should use CamelCase")
            if match := re.match(r"def\s+(\w+)", line.lstrip()):
                if not re.match(r"([a-z_]+)_?([a-z_]+)", s := match.group(1)):
                    print(f"{files}: Line {n}: S009 Function name '{s}' should use snake_case")
            for parameter in pep_analyzer.get_parameters(n):
                if not re.match(r"[a-z_]+", parameter):
                    print(f"{files}: Line {n}: S010 Argument name '{parameter}' should be snake_case")
                    break

            for variable in pep_analyzer.get_variables(n):
                if not re.match(r"[a-z_]+", variable):
                    print(f"{files}: Line {n}: S011 Variable '{variable}' in function should be snake_case")
                    break

            if pep_analyzer.get_mutable_defaults(n):
                print(f"{files}: Line {n}: S012 Default argument value is mutable")
