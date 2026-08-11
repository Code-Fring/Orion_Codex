"""Dependency graph for code analysis and impact assessment."""

import ast
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeNode:
    """Represents a node in the dependency graph (file, class, function)."""

    id: str
    name: str
    type: str  # file, class, function, module
    file_path: str
    line_start: int
    line_end: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyEdge:
    """Represents a dependency between two nodes."""

    source: str
    target: str
    type: str  # import, inheritance, call, reference
    metadata: dict[str, Any] = field(default_factory=dict)


class DependencyGraph:
    """Graph representing code dependencies."""

    def __init__(self) -> None:
        self.nodes: dict[str, CodeNode] = {}
        self.edges: list[DependencyEdge] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        self._file_nodes: dict[str, list[str]] = defaultdict(list)

    def add_node(self, node: CodeNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        self._file_nodes[node.file_path].append(node.id)

    def add_edge(self, edge: DependencyEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        self._adjacency[edge.source].add(edge.target)
        self._reverse_adjacency[edge.target].add(edge.source)

    def get_dependencies(self, node_id: str) -> list[str]:
        """Get direct dependencies of a node."""
        return list(self._adjacency.get(node_id, set()))

    def get_dependents(self, node_id: str) -> list[str]:
        """Get nodes that depend on this node."""
        return list(self._reverse_adjacency.get(node_id, set()))

    def get_transitive_dependencies(
        self, node_id: str, max_depth: int = 10
    ) -> set[str]:
        """Get all transitive dependencies."""
        visited = set()
        queue = [(node_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth or current in visited:
                continue
            visited.add(current)
            for dep in self._adjacency.get(current, set()):
                if dep not in visited:
                    queue.append((dep, depth + 1))

        visited.discard(node_id)
        return visited

    def get_transitive_dependents(self, node_id: str, max_depth: int = 10) -> set[str]:
        """Get all transitive dependents."""
        visited = set()
        queue = [(node_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth or current in visited:
                continue
            visited.add(current)
            for dep in self._reverse_adjacency.get(current, set()):
                if dep not in visited:
                    queue.append((dep, depth + 1))

        visited.discard(node_id)
        return visited

    def get_file_dependencies(self, file_path: str) -> list[str]:
        """Get all files this file depends on."""
        deps = set()
        for node_id in self._file_nodes.get(file_path, []):
            for dep_id in self.get_dependencies(node_id):
                dep_node = self.nodes.get(dep_id)
                if dep_node:
                    deps.add(dep_node.file_path)
        return list(deps)

    def get_file_dependents(self, file_path: str) -> list[str]:
        """Get all files that depend on this file."""
        deps = set()
        for node_id in self._file_nodes.get(file_path, []):
            for dep_id in self.get_dependents(node_id):
                dep_node = self.nodes.get(dep_id)
                if dep_node:
                    deps.add(dep_node.file_path)
        return list(deps)

    def find_impact(self, file_path: str) -> dict[str, Any]:
        """Find impact of changing a file."""
        affected_files = self.get_file_dependents(file_path)
        all_affected = set(affected_files)

        # Also check transitive dependents
        for node_id in self._file_nodes.get(file_path, []):
            all_affected.update(
                self.nodes[dep_id].file_path
                for dep_id in self.get_transitive_dependents(node_id)
                if dep_id in self.nodes
            )

        # Find affected nodes in the file
        affected_nodes = []
        for node_id in self._file_nodes.get(file_path, []):
            node = self.nodes[node_id]
            dependents = self.get_dependents(node_id)
            if dependents:
                affected_nodes.append(
                    {
                        "node": node.name,
                        "type": node.type,
                        "dependents_count": len(dependents),
                        "dependents": [
                            self.nodes[d].name for d in dependents if d in self.nodes
                        ],
                    }
                )

        return {
            "file": file_path,
            "directly_affected_files": affected_files,
            "all_affected_files": list(all_affected),
            "affected_nodes": affected_nodes,
            "risk_level": self._calculate_risk(affected_files, affected_nodes),
        }

    def _calculate_risk(
        self, affected_files: list[str], affected_nodes: list[dict]
    ) -> str:
        """Calculate risk level of changes."""
        total_dependents = sum(n["dependents_count"] for n in affected_nodes)
        if total_dependents > 50 or len(affected_files) > 20:
            return "critical"
        elif total_dependents > 20 or len(affected_files) > 10:
            return "high"
        elif total_dependents > 5 or len(affected_files) > 5:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "nodes": {k: v.__dict__ for k, v in self.nodes.items()},
            "edges": [e.__dict__ for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DependencyGraph":
        """Deserialize graph from dictionary."""
        graph = cls()
        for node_data in data.get("nodes", {}).values():
            node = CodeNode(**node_data)
            graph.add_node(node)
        for edge_data in data.get("edges", []):
            edge = DependencyEdge(**edge_data)
            graph.add_edge(edge)
        return graph


class DependencyAnalyzer:
    """Analyzes code to build dependency graphs."""

    def __init__(self) -> None:
        self.graph = DependencyGraph()

    def analyze_python_file(self, file_path: Path, content: str) -> None:
        """Analyze Python file for dependencies."""
        try:
            tree = ast.parse(content)
            file_id = str(file_path)

            # Add file node
            file_node = CodeNode(
                id=f"file:{file_id}",
                name=file_path.name,
                type="file",
                file_path=file_id,
                line_start=1,
                line_end=len(content.splitlines()),
            )
            self.graph.add_node(file_node)

            # Track imports
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(
                            f"{module}.{alias.name}" if module else alias.name
                        )

                # Classes
                elif isinstance(node, ast.ClassDef):
                    class_id = f"class:{file_id}:{node.name}"
                    class_node = CodeNode(
                        id=class_id,
                        name=node.name,
                        type="class",
                        file_path=file_id,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        metadata={
                            "bases": [
                                base.id
                                for base in node.bases
                                if isinstance(base, ast.Name)
                            ]
                        },
                    )
                    self.graph.add_node(class_node)
                    self.graph.add_edge(
                        DependencyEdge(
                            source=f"file:{file_id}",
                            target=class_id,
                            type="contains",
                        )
                    )

                    # Inheritance edges
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            self.graph.add_edge(
                                DependencyEdge(
                                    source=class_id,
                                    target=f"class:{base.id}",
                                    type="inheritance",
                                )
                            )

                # Functions
                elif isinstance(node, ast.FunctionDef):
                    func_id = f"function:{file_id}:{node.name}"
                    func_node = CodeNode(
                        id=func_id,
                        name=node.name,
                        type="function",
                        file_path=file_id,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        metadata={"is_async": isinstance(node, ast.AsyncFunctionDef)},
                    )
                    self.graph.add_node(func_node)
                    self.graph.add_edge(
                        DependencyEdge(
                            source=f"file:{file_id}",
                            target=func_id,
                            type="contains",
                        )
                    )

                # Function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        self.graph.add_edge(
                            DependencyEdge(
                                source=f"function:{file_id}:{self._get_current_function(tree, node)}",
                                target=f"function:{node.func.id}",
                                type="call",
                            )
                        )
                    elif isinstance(node.func, ast.Attribute):
                        self.graph.add_edge(
                            DependencyEdge(
                                source=f"function:{file_id}:{self._get_current_function(tree, node)}",
                                target=f"method:{node.func.attr}",
                                type="call",
                            )
                        )

            # Add import edges
            for imp in imports:
                self.graph.add_edge(
                    DependencyEdge(
                        source=f"file:{file_id}",
                        target=f"module:{imp}",
                        type="import",
                    )
                )

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")

    def _get_current_function(self, tree: ast.AST, node: ast.AST) -> str:
        """Get the name of the function containing a node."""
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(parent):
                    if child is node:
                        return parent.name
        return "module"

    def analyze_javascript_file(self, file_path: Path, content: str) -> None:
        """Analyze JavaScript/TypeScript file for dependencies (basic regex-based)."""
        file_id = str(file_path)

        # Add file node
        file_node = CodeNode(
            id=f"file:{file_id}",
            name=file_path.name,
            type="file",
            file_path=file_id,
            line_start=1,
            line_end=len(content.splitlines()),
        )
        self.graph.add_node(file_node)

        # Import patterns
        import_patterns = [
            r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)',
            r'import\([\'"]([^\'"]+)[\'"]\)',
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                dep = match.group(1)
                self.graph.add_edge(
                    DependencyEdge(
                        source=f"file:{file_id}",
                        target=f"module:{dep}",
                        type="import",
                    )
                )

        # Class definitions
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            extends = match.group(2)
            class_id = f"class:{file_id}:{class_name}"

            class_node = CodeNode(
                id=class_id,
                name=class_name,
                type="class",
                file_path=file_id,
                line_start=content[: match.start()].count("\n") + 1,
                line_end=content[: match.end()].count("\n") + 1,
            )
            self.graph.add_node(class_node)
            self.graph.add_edge(
                DependencyEdge(
                    source=f"file:{file_id}",
                    target=class_id,
                    type="contains",
                )
            )

            if extends:
                self.graph.add_edge(
                    DependencyEdge(
                        source=class_id,
                        target=f"class:{extends}",
                        type="inheritance",
                    )
                )

        # Function definitions
        func_pattern = r"(?:async\s+)?function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1) or match.group(2)
            func_id = f"function:{file_id}:{func_name}"

            func_node = CodeNode(
                id=func_id,
                name=func_name,
                type="function",
                file_path=file_id,
                line_start=content[: match.start()].count("\n") + 1,
                line_end=content[: match.end()].count("\n") + 1,
            )
            self.graph.add_node(func_node)
            self.graph.add_edge(
                DependencyEdge(
                    source=f"file:{file_id}",
                    target=func_id,
                    type="contains",
                )
            )

    def analyze_workspace(
        self, workspace_path: Path, extensions: list[str] = None
    ) -> DependencyGraph:
        """Analyze entire workspace."""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]

        for ext in extensions:
            for file_path in workspace_path.rglob(f"*{ext}"):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if ext == ".py":
                            self.analyze_python_file(file_path, content)
                        elif ext in (".js", ".ts", ".jsx", ".tsx"):
                            self.analyze_javascript_file(file_path, content)
                    except Exception as e:
                        logger.warning(f"Failed to analyze {file_path}: {e}")

        return self.graph

    def save_graph(self, output_path: Path) -> None:
        """Save graph to file."""
        output_path.write_text(json.dumps(self.graph.to_dict(), indent=2))

    def load_graph(self, input_path: Path) -> DependencyGraph:
        """Load graph from file."""
        data = json.loads(input_path.read_text())
        self.graph = DependencyGraph.from_dict(data)
        return self.graph


# Global dependency analyzer
dependency_analyzer = DependencyAnalyzer()
