from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WrittenFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    split_key: str | None = None
    split_value: str | int | None = None
    resource_type: str | None = None


class CatalogResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    data: Any
    raw: Any | None = None
    output: str | None = None
    output_file: str | None = None
    output_files: list[WrittenFile] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
