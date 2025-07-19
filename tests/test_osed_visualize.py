"""
Unit tests for OSED graph-easy visualization output.
"""

import os
from src.python import osed_visualize
from src.python.osed_visualize import generate_mermaid


def test_generate_graph_easy_demo():
    """Test graph-easy output for a demo OSED document with relationships."""
    # Load the demo OSED document with relationships
    path = os.path.join(
        os.path.dirname(__file__), 'data/v0.3.0/osed.visualize-demo.v0.3.0.yaml'
    )
    osed_doc = osed_visualize.load_osed_yaml(path)
    output = osed_visualize.generate_graph_easy(osed_doc)
    # Check for expected nodes
    for entity in ['user', 'post', 'comment', 'userProfile']:
        assert f'[{entity}] {{label: "{entity}"}}' in output
    # Check for expected edges (relationships)
    assert '[user] -- "profile" --> [userProfile]' in output
    assert '[post] -- "author" --> [user]' in output
    assert '[comment] -- "post" --> [post]' in output
    assert '[comment] -- "author" --> [user]' in output


def test_generate_dot_demo():
    """Test DOT/Graphviz output for a demo OSED document with relationships."""
    # Load the demo OSED document with relationships
    path = os.path.join(
        os.path.dirname(__file__), 'data/v0.3.0/osed.visualize-demo.v0.3.0.yaml'
    )
    osed_doc = osed_visualize.load_osed_yaml(path)
    output = osed_visualize.generate_dot(osed_doc)

    # Check for DOT file structure
    assert "digraph OSED_Entities {" in output
    assert "rankdir=LR;" in output
    assert (
        "node [shape=box, style=filled, fillcolor=lightblue, fontname=\"Arial\"];"
        in output
    )
    assert "edge [fontname=\"Arial\", fontsize=10];" in output

    # Check for expected entity nodes
    for entity in ['user', 'post', 'comment', 'userProfile']:
        assert f'"{entity}" [label="{entity}"];' in output

    # Check for expected relationship edges
    assert '"user" -> "userProfile" [label="profile"];' in output
    assert '"post" -> "user" [label="author"];' in output
    assert '"comment" -> "post" [label="post"];' in output
    assert '"comment" -> "user" [label="author"];' in output

    # Check for proper closing
    assert output.strip().endswith("}")


def test_generate_mermaid_demo():
    """Test Mermaid ER diagram output for a demo OSED document with relationships and types."""
    path = os.path.join(
        os.path.dirname(__file__), 'data/v0.3.0/osed.visualize-demo.v0.3.0.yaml'
    )
    osed_doc = osed_visualize.load_osed_yaml(path)
    output = generate_mermaid(osed_doc, show_types=True)
    # Check for ER diagram header
    assert output.startswith("erDiagram")
    # Check for expected relationships
    assert "user ||--o{ userProfile : profile" in output
    assert "post ||--o{ user : author" in output
    assert "comment ||--o{ post : post" in output
    assert "comment ||--o{ user : author" in output
    # Check for expected entities and type info
    assert "user {" in output
    assert "systemId id" in output
    assert "string password" in output
    assert "userProfile {" in output
    assert "string displayName" in output
    assert "post {" in output
    assert "string title" in output
    assert "comment {" in output
    assert "string content" in output


def test_generate_plantuml_demo():
    """Test PlantUML class diagram output for a demo OSED document with relationships and types."""
    path = os.path.join(
        os.path.dirname(__file__), 'data/v0.3.0/osed.visualize-demo.v0.3.0.yaml'
    )
    osed_doc = osed_visualize.load_osed_yaml(path)
    output = osed_visualize.generate_plantuml(osed_doc, show_types=True)
    # Check for PlantUML diagram header and footer
    assert output.startswith("@startuml")
    assert output.strip().endswith("@enduml")
    # Check for expected class definitions
    for entity in ['user', 'post', 'comment', 'userProfile']:
        assert f"class {entity} {{" in output
    # Check for expected fields and types
    assert "+id: systemId" in output
    assert "+email: email" in output
    assert "+password: string" in output
    assert "+displayName: string" in output
    assert "+title: string" in output
    assert "+content: string" in output
    # Check for expected relationships
    assert 'user "1" -- "*" userProfile : profile' in output
    assert 'post "1" -- "*" user : author' in output
    assert 'comment "1" -- "*" post : post' in output
    assert 'comment "1" -- "*" user : author' in output


# NOTE: PNG and SVG output are not tested in CI due to non-determinism in Graphviz output.
# Attempts to use hash or text comparison failed because output varies between runs/environments.
# See session state and GitHub issue for future comprehensive visualization testing.
