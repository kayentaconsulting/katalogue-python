"""Default table properties and parent grouping per resource — single source of truth.

Table output uses DEFAULT_PROPERTIES when no --properties flag is given. JSON and compact
always return all properties. Use --wide to bypass defaults in table mode.
PARENT_GROUP defines which (id, name) field pair to group by in table list output.
"""

from __future__ import annotations

DEFAULT_PROPERTIES: dict[str, list[str]] = {
    "system": ["system_id", "system_name", "system_type", "system_description"],
    "datasource": [
        "datasource_id",
        "datasource_name",
        "datasource_type_name",
        "datasource_description",
    ],
    "dataset": [
        "dataset_id",
        "dataset_name",
        "dataset_type_name",
        "dataset_description",
    ],
    "dataset_group": [
        "dataset_group_id",
        "dataset_group_name",
        "dataset_group_description",
    ],
    "field": [
        "field_id",
        "field_name",
        "field_description_name",
        "field_source_description",
    ],
    "glossary": ["glossary_id", "glossary_name", "glossary_description"],
    "business_term": [
        "business_term_id",
        "business_term_name",
        "glossary_name",
        "business_term_description",
    ],
    "field_description": [
        "field_description_name",
        "field_role_name",
        "is_pii",
        "field_sensitivity_name",
        "field_description_description",
    ],
}

# Immediate parent (id_field, name_field) to group list table output by.
# Resources without a parent (system, glossary) are omitted.
PARENT_GROUP: dict[str, list[tuple[str, str]]] = {
    "datasource": [("system_id", "system_name")],
    "dataset_group": [
        ("system_id", "system_name"),
        ("datasource_id", "datasource_name"),
    ],
    "dataset": [
        ("system_id", "system_name"),
        ("datasource_id", "datasource_name"),
        ("dataset_group_id", "dataset_group_name"),
    ],
    "field": [
        ("system_id", "system_name"),
        ("datasource_id", "datasource_name"),
        ("dataset_group_id", "dataset_group_name"),
        ("dataset_id", "dataset_name"),
    ],
    "business_term": [("glossary_id", "glossary_name")],
    "field_description": [("field_id", "field_name")],
}
