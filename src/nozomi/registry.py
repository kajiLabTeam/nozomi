from __future__ import annotations

import hashlib
import json

from .adapter import ComponentAdapter
from .models import (
    AvailabilityReason,
    ComponentContract,
    PipelineAvailability,
    PipelineCatalogEntry,
    PipelineDefinition,
    PipelineSnapshot,
    Slot,
)


def canonical_digest(definition: PipelineDefinition) -> str:
    payload = definition.model_dump(mode="json", exclude_none=True)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(text.encode()).hexdigest()


def _validate(definition: PipelineDefinition) -> None:
    components = {
        component.instance_id: component for component in definition.components
    }
    bindings = {
        (binding.target_component_instance, binding.target_slot_id): binding
        for binding in definition.bindings
    }
    pipeline_inputs = {slot.slot_id: slot for slot in definition.input_slots}
    if len(bindings) != len(definition.bindings):
        raise ValueError("input bindings must be unique")
    positions = {
        component.instance_id: index
        for index, component in enumerate(definition.components)
    }
    valid_targets = {
        (component.instance_id, slot.slot_id)
        for component in definition.components
        for slot in component.input_slots
    }
    if set(bindings) != valid_targets:
        raise ValueError("bindings must match component inputs exactly")
    for index, component in enumerate(definition.components):
        for slot in component.input_slots:
            binding = bindings.get((component.instance_id, slot.slot_id))
            if binding is None:
                raise ValueError(
                    f"missing binding for {component.instance_id}.{slot.slot_id}"
                )
            source: Slot | None
            if binding.source_component_instance is None:
                source = pipeline_inputs.get(binding.source_slot_id)
            else:
                if binding.source_component_instance not in positions:
                    raise ValueError("binding source component does not exist")
                if positions[binding.source_component_instance] >= index:
                    raise ValueError("binding source must precede target")
                source_component = components.get(binding.source_component_instance)
                source = (
                    next(
                        (
                            s
                            for s in source_component.output_slots
                            if s.slot_id == binding.source_slot_id
                        ),
                        None,
                    )
                    if source_component
                    else None
                )
            if source is None or source.accepted_contracts != slot.accepted_contracts:
                raise ValueError(f"binding type mismatch for {slot.slot_id}")
    output_ids = [output.output_slot_id for output in definition.outputs]
    if len(output_ids) != len(set(output_ids)):
        raise ValueError("pipeline output slot ids must be unique")
    for output in definition.outputs:
        output_component = components.get(output.source_component_instance)
        if output_component is None or not any(
            s.slot_id == output.source_slot_id for s in output_component.output_slots
        ):
            raise ValueError("pipeline output source does not exist")


def _matching(required: ComponentContract, candidate: ComponentContract) -> bool:
    return (
        required.component_id == candidate.component_id
        and required.input_slots == candidate.input_slots
        and required.output_slots == candidate.output_slots
        and required.parameters_schema == candidate.parameters_schema
    )


class PipelineRegistry:
    def __init__(
        self, definitions: tuple[PipelineDefinition, ...], adapter: ComponentAdapter
    ) -> None:
        keys = [(d.pipeline_id, d.definition_version) for d in definitions]
        if len(keys) != len(set(keys)):
            raise ValueError("pipeline_id and definition_version must be unique")
        active = [d.pipeline_id for d in definitions if d.state.value == "active"]
        if len(active) != len(set(active)):
            raise ValueError("each pipeline_id may have one active version")
        for definition in definitions:
            _validate(definition)
        self._payloads = tuple(
            json.dumps(
                d.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for d in definitions
        )
        self._adapter = adapter

    def _definitions(self) -> tuple[PipelineDefinition, ...]:
        return tuple(PipelineDefinition.model_validate_json(p) for p in self._payloads)

    def _availability(self, definition: PipelineDefinition) -> PipelineAvailability:
        for component in definition.components:
            if not any(
                _matching(component, candidate)
                for candidate in self._adapter.capabilities()
            ):
                return PipelineAvailability(
                    available=False,
                    reason=AvailabilityReason(
                        code="unsupported_component", target=component.component_id
                    ),
                )
        return PipelineAvailability(available=True)

    def catalog(self) -> tuple[PipelineCatalogEntry, ...]:
        return tuple(
            PipelineCatalogEntry(
                definition=d,
                availability=self._availability(d),
                digest=canonical_digest(d),
            )
            for d in self._definitions()
        )

    def resolve(self, pipeline_id: str) -> PipelineSnapshot | None:
        definition = next(
            (
                d
                for d in self._definitions()
                if d.pipeline_id == pipeline_id and d.state.value == "active"
            ),
            None,
        )
        if definition is None:
            return None
        return PipelineSnapshot(
            definition=definition,
            availability=self._availability(definition),
            digest=canonical_digest(definition),
        )
