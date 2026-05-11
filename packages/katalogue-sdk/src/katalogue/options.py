from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from katalogue.filters import Filter

StandardFormat = Literal["json", "compact", "table"]


class OutputOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: str | None = None
    template: str | None = None
    output_file: str | None = None
    output_dir: str | None = None
    split_by: str | None = None
    filename_template: str | None = None
    overwrite: bool = False
    dry_run: bool = False


class GetOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: int | str | None = None
    parent_id: int | str | None = None
    filters: str | list[str] | list[Filter] | None = None
    properties: list[str] | None = None
    sort: list[dict[str, str]] | None = None
    include_children: bool = False
    format_descriptions_as_text: bool = False
    output: OutputOptions = Field(default_factory=OutputOptions)

    @model_validator(mode="after")
    def _validate_combinations(self) -> "GetOptions":
        out = self.output
        if out.split_by and not self.include_children:
            raise ValueError("split_by requires include_children=True")
        if out.split_by and out.output_file:
            raise ValueError(
                "split_by cannot be combined with output_file; use output_dir"
            )
        if out.split_by and not out.output_dir:
            raise ValueError("split_by requires output_dir")
        if out.output_file and out.output_dir:
            raise ValueError("output_file and output_dir are mutually exclusive")
        return self


class UpdateOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: int | str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)
    records: list[dict[str, Any]] = Field(default_factory=list)
    continue_on_error: bool = False

    @model_validator(mode="after")
    def _validate_mode(self) -> "UpdateOptions":
        has_single = self.resource_id is not None
        has_batch = bool(self.records)
        if has_single and has_batch:
            raise ValueError("resource_id/changes and records are mutually exclusive")
        if not has_single and not has_batch:
            raise ValueError("Either resource_id or records must be provided")
        return self
