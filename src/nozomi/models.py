from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PipelineState(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class DataType(StrEnum):
    ACCE = "acce"
    GYRO = "gyro"
    BLE = "ble"
    POSE = "pose"
    PARTICLE = "particle"


class AssetContract(StrictModel):
    kind: Literal["asset"] = "asset"
    data_type: DataType
    schema_version: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    format: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")


class InternalValueContract(StrictModel):
    kind: Literal["internal_value"] = "internal_value"
    value_type: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")


Contract = Annotated[AssetContract | InternalValueContract, Field(discriminator="kind")]


class Slot(StrictModel):
    slot_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    accepted_contracts: tuple[Contract, ...] = Field(min_length=1)
    required: bool = True
    max_assets: int = Field(default=1, ge=1, le=1)


def _json_object_schema(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("type") != "object":
        raise ValueError("parameters_schema must have type=object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("parameters_schema must be finite JSON") from exc
    return value


class ComponentContract(StrictModel):
    component_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    instance_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    input_slots: tuple[Slot, ...] = ()
    output_slots: tuple[Slot, ...] = ()
    parameters_schema: dict[str, Any]
    _schema = field_validator("parameters_schema")(_json_object_schema)

    @model_validator(mode="after")
    def validate_slot_ids(self) -> ComponentContract:
        for slots, label in (
            (self.input_slots, "input"),
            (self.output_slots, "output"),
        ):
            ids = [slot.slot_id for slot in slots]
            if len(ids) != len(set(ids)):
                raise ValueError(f"component {label} slot ids must be unique")
        return self


class SlotBinding(StrictModel):
    target_component_instance: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    target_slot_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    source_component_instance: str | None = None
    source_slot_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")


class PipelineOutput(StrictModel):
    output_slot_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    source_component_instance: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    source_slot_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")


class PipelineDefinition(StrictModel):
    pipeline_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    display_name: str = Field(min_length=1)
    definition_version: str = Field(pattern=r"^v?[0-9]+\.[0-9]+\.[0-9]+$")
    components: tuple[ComponentContract, ...] = Field(min_length=1)
    input_slots: tuple[Slot, ...] = ()
    outputs: tuple[PipelineOutput, ...] = Field(min_length=1)
    bindings: tuple[SlotBinding, ...] = ()
    state: PipelineState = PipelineState.ACTIVE
    parameters_schema: dict[str, Any]
    _schema = field_validator("parameters_schema")(_json_object_schema)

    @model_validator(mode="after")
    def validate_ids(self) -> PipelineDefinition:
        ids = [slot.slot_id for slot in self.input_slots]
        if len(ids) != len(set(ids)):
            raise ValueError("pipeline input slot ids must be unique")
        ids = [component.instance_id for component in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("component instance ids must be unique")
        return self


class AvailabilityReason(StrictModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    target: str


class PipelineAvailability(StrictModel):
    available: bool
    reason: AvailabilityReason | None = None


class PipelineCatalogEntry(StrictModel):
    definition: PipelineDefinition
    availability: PipelineAvailability
    digest: str


class PipelineSnapshot(PipelineCatalogEntry):
    pass


class ErrorResponse(StrictModel):
    code: str
    message: str
    availability_reason: AvailabilityReason | None = None


class ErrorEnvelope(StrictModel):
    detail: ErrorResponse
