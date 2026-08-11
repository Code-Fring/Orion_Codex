"""Dependency Graph API for plugins."""

from pathlib import Path
from typing import Any

from backend.analysis.dependency_graph import DependencyGraph, dependency_analyzer


class DependencyGraphAPI:
    """API for dependency graph operations."""

    def __init__(self, project_id: str, workspace_path: str) -> None:
        self.project_id = project_id
        self.workspace_path = workspace_path

    def analyze(self) -> DependencyGraph:
        """Analyze workspace and build dependency graph."""
        return dependency_analyzer.analyze_workspace(Path(self.workspace_path))

    def get_graph(self) -> DependencyGraph | None:
        """Get current dependency graph."""
        return dependency_analyzer.get_graph()

    def find_impact(self, file_path: str) -> dict[str, Any]:
        """Analyze impact of changing a file."""
        graph = self.get_graph()
        if not graph:
            graph = self.analyze()
        return graph.find_impact(file_path)

    def get_dependencies(self, file_path: str) -> list[str]:
        """Get dependencies of a file."""
        graph = self.get_graph()
        if not graph:
            graph = self.analyze()
        node = graph.get_node(file_path)
        if node:
            return [e.target for e in graph.get_edges_from(file_path)]
        return []

    def get_dependents(self, file_path: str) -> list[str]:
        """Get files that depend on this file."""
        graph = self.get_graph()
        if not graph:
            graph = self.analyze()
        node = graph.get_node(file_path)
        if node:
            return [e.source for e in graph.get_edges_to(file_path)]
        return []

    def save_graph(self, output_path: Path) -> bool:
        """Save graph to file."""
        graph = self.get_graph()
        if graph:
            dependency_analyzer.save_graph(output_path)
            return True
        return False

    def get_summary(self) -> dict[str, Any]:
        """Get graph summary."""
        graph = self.get_graph()
        if not graph:
            return {"nodes": 0, "edges": 0, "types": {}}

        types = {}
        for node in graph.nodes.values():
            types[node.type] = types.get(node.type, 0) + 1

        return {
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "types": types,
        }
