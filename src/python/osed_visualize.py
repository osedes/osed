"""
Graph-Easy visualization module for OSED entity relationships.

This module provides functions to generate text-based entity relationship diagrams
in the graph-easy format for terminal visualization.
"""

import argparse
import sys
import yaml

try:
    import graphviz

    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


def load_osed_yaml(path):
    """
    Load and parse an OSED YAML document from the given file path.
    Returns the parsed Python dict.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_graph_easy(osed_doc):
    """
    Generate a graph-easy formatted string representing the relationships between entities.

    Args:
        osed_doc (dict): Parsed OSED document.

    Returns:
        str: Graph-Easy formatted string.
    """
    entities = set(osed_doc.get('entities', []))
    relationships = []

    # For each entity, check its fields for references to other entities
    for entity in entities:
        fields = osed_doc.get(entity, {})
        if not isinstance(fields, dict):
            continue
        for field, field_type in fields.items():
            # If the field type matches another entity, treat as a relationship
            if field_type in entities:
                relationships.append((entity, field_type, field))

    lines = []
    # Output nodes with labels if possible
    for entity in entities:
        # Use the entity name as the label for demonstration; adjust if you have display names
        lines.append(f"[{entity}] {{label: \"{entity}\"}}")
    # Output edges with labels using the correct syntax
    for src, dst, label in relationships:
        lines.append(f"[{src}] -- \"{label}\" --> [{dst}]")
    return "\n".join(lines)


def generate_dot(osed_doc):
    """
    Generate a DOT/Graphviz formatted string representing the relationships between entities.

    Args:
        osed_doc (dict): Parsed OSED document.

    Returns:
        str: DOT/Graphviz formatted string.
    """
    entities = set(osed_doc.get('entities', []))
    relationships = []

    # For each entity, check its fields for references to other entities
    for entity in entities:
        fields = osed_doc.get(entity, {})
        if not isinstance(fields, dict):
            continue
        for field, field_type in fields.items():
            # If the field type matches another entity, treat as a relationship
            if field_type in entities:
                relationships.append((entity, field_type, field))

    lines = [
        "digraph OSED_Entities {",
        "    // Graph settings",
        "    rankdir=LR;",
        "    node [shape=box, style=filled, fillcolor=lightblue, fontname=\"Arial\"];",
        "    edge [fontname=\"Arial\", fontsize=10];",
        "",
        "    // Entity nodes",
    ]

    # Add entity nodes
    for entity in entities:
        lines.append(f'    "{entity}" [label="{entity}"];')

    lines.append("")
    lines.append("    // Relationships")

    # Add relationship edges
    for src, dst, label in relationships:
        lines.append(f'    "{src}" -> "{dst}" [label="{label}"];')

    lines.append("}")

    return "\n".join(lines)


def build_svg_graph(osed_doc):
    """
    Build and return a graphviz.Digraph object for SVG output.
    """
    if not GRAPHVIZ_AVAILABLE:
        raise ImportError(
            "graphviz package is required for SVG generation. Install with: pip install graphviz"
        )
    entities = set(osed_doc.get('entities', []))
    relationships = []
    for entity in entities:
        fields = osed_doc.get(entity, {})
        if not isinstance(fields, dict):
            continue
        for field, field_type in fields.items():
            if field_type in entities:
                relationships.append((entity, field_type, field))
    dot = graphviz.Digraph(comment='OSED Entity Relationships')
    dot.attr(rankdir='LR')
    dot.attr(
        'node',
        shape='box',
        style='filled',
        fillcolor='lightblue',
        fontname='Arial',
    )
    dot.attr('edge', fontname='Arial', fontsize='10')
    for entity in entities:
        dot.node(entity, entity)
    for src, dst, label in relationships:
        dot.edge(src, dst, label)
    return dot


def generate_svg_file(osed_doc, output_path):
    """
    Generate an SVG file representing the relationships between entities.
    """
    base_path = output_path.replace('.svg', '')
    build_svg_graph(osed_doc).render(base_path, format='svg', cleanup=True)


def build_png_graph(osed_doc):
    """
    Build and return a graphviz.Digraph object for PNG output.
    """
    if not GRAPHVIZ_AVAILABLE:
        raise ImportError(
            "graphviz package is required for PNG generation. Install with: pip install graphviz"
        )
    entities = set(osed_doc.get('entities', []))
    relationships = []
    for entity in entities:
        fields = osed_doc.get(entity, {})
        if not isinstance(fields, dict):
            continue
        for field, field_type in fields.items():
            if field_type in entities:
                relationships.append((entity, field_type, field))
    dot = graphviz.Digraph(comment='OSED Entity Relationships')
    dot.attr(rankdir='LR')
    dot.attr(
        'node',
        shape='box',
        style='filled',
        fillcolor='lightblue',
        fontname='Arial',
    )
    dot.attr('edge', fontname='Arial', fontsize='10')
    for entity in entities:
        dot.node(entity, entity)
    for src, dst, label in relationships:
        dot.edge(src, dst, label)
    return dot


def generate_png_file(osed_doc, output_path):
    """
    Generate a PNG file representing the relationships between entities.
    """
    base_path = output_path.replace('.png', '')
    build_png_graph(osed_doc).render(base_path, format='png', cleanup=True)


def generate_mermaid(osed_doc, show_types=True):
    """
    Generate a Mermaid ER diagram string from the OSED document.
    Args:
        osed_doc (dict): Parsed OSED document.
        show_types (bool): Whether to include field/type info in the diagram.
    Returns:
        str: Mermaid ER diagram.
    """
    entities = set(osed_doc.get('entities', []))
    relationships = []
    entity_fields = {}
    for entity in entities:
        fields = osed_doc.get(entity, {})
        if not isinstance(fields, dict):
            continue
        entity_fields[entity] = fields
        for field, field_type in fields.items():
            if field_type in entities:
                relationships.append((entity, field_type, field))
    lines = ["erDiagram"]
    # Add relationships
    for src, dst, label in relationships:
        # Use o|--|| for reference (one-to-one), o|--o{ for one-to-many (default here)
        lines.append(f"  {src} ||--o{{ {dst} : {label}")
    # Add entities and fields
    for entity in entities:
        lines.append(f"  {entity} {{")
        if show_types:
            for field, field_type in entity_fields.get(entity, {}).items():
                if field_type in entities:
                    continue  # skip relationship fields
                lines.append(f"    {field_type} {field}")
        else:
            for field, field_type in entity_fields.get(entity, {}).items():
                if field_type in entities:
                    continue
                lines.append(f"    {field}")
        lines.append("  }")
    return "\n".join(lines)


def generate_plantuml(osed_doc, show_types=True):
    """
    Generate a PlantUML class diagram string from the OSED document.
    Args:
        osed_doc (dict): Parsed OSED document.
        show_types (bool): Whether to include field/type info in the diagram.
    Returns:
        str: PlantUML class diagram.
    """
    entities = set(osed_doc.get('entities', []))
    relationships = []
    entity_fields = {}
    for entity in entities:
        fields = osed_doc.get(entity, {})
        if not isinstance(fields, dict):
            continue
        entity_fields[entity] = fields
        for field, field_type in fields.items():
            if field_type in entities:
                relationships.append((entity, field_type, field))
    lines = ["@startuml"]
    # Add entities and fields
    for entity in entities:
        lines.append(f"class {entity} {{")
        for field, field_type in entity_fields.get(entity, {}).items():
            if field_type in entities:
                continue  # skip relationship fields
            if show_types:
                lines.append(f"  +{field}: {field_type}")
            else:
                lines.append(f"  +{field}")
        lines.append("}")
    # Add relationships (assume 1-to-many for now)
    for src, dst, label in relationships:
        lines.append(f"{src} " + '"1"' + " -- " + '"*"' + f" {dst} : {label}")
    lines.append("@enduml")
    return "\n".join(lines)


def main():
    """Main entry point for OSED entity relationship visualization CLI."""
    parser = argparse.ArgumentParser(
        description="""
OSED Entity Relationship Visualization

Recommended: Use --format=svg for best quality diagrams (scalable, browser-friendly).
Other formats: 'graph-easy' (ASCII), 'dot' (Graphviz), 'png' (bitmap image).
"""
    )
    parser.add_argument(
        "input_file",
        metavar="INPUT",
        type=str,
        help="Path to the OSED YAML document to visualize.",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="graph-easy",
        choices=["graph-easy", "dot", "png", "svg", "mermaid", "plantuml"],
        help="Output format: 'graph-easy' (ASCII), 'dot' (Graphviz), 'png' (bitmap), 'svg' (recommended: scalable, browser-friendly), 'mermaid' (Markdown ER diagram), 'plantuml' (UML class diagram; render with PlantUML JAR, server, or online editors such as plantuml.com/plantuml)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (if omitted, prints to terminal; required for 'png' and 'svg').",
    )
    parser.add_argument(
        "--show-types",
        action="store_true",
        default=False,
        help="Show field types in Mermaid ER diagram (default: false)",
    )
    args = parser.parse_args()

    osed_doc = load_osed_yaml(args.input_file)

    if args.format == "graph-easy":
        output = generate_graph_easy(osed_doc)
    elif args.format == "dot":
        output = generate_dot(osed_doc)
    elif args.format == "png":
        if not args.output:
            print(
                "Error: Output file path is required for 'png' format.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            generate_png_file(osed_doc, args.output)
            print(f"Generated PNG file: {args.output}")
            return
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.format == "svg":
        if not args.output:
            print(
                "Error: Output file path is required for 'svg' format.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            generate_svg_file(osed_doc, args.output)
            print(f"Generated SVG file: {args.output}")
            return
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.format == "mermaid":
        output = generate_mermaid(osed_doc, show_types=args.show_types)
    elif args.format == "plantuml":
        output = generate_plantuml(osed_doc, show_types=args.show_types)
    else:
        print(f"Error: Unsupported format '{args.format}'.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
