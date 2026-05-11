from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    message: str
    data: list[dict[str, Any]] = Field(default_factory=list)
    raw: Any | None = None
    record_id: int | str | None = None
    partial_results: list["WriteResult"] | None = None


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
