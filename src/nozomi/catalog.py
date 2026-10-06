from .models import (
    AssetContract,
    ComponentContract,
    DataType,
    InternalValueContract,
    PipelineDefinition,
    PipelineOutput,
    Slot,
    SlotBinding,
)

ACCE = AssetContract(data_type=DataType.ACCE, schema_version="1", format="csv")
GYRO = AssetContract(data_type=DataType.GYRO, schema_version="1", format="csv")
BLE = AssetContract(data_type=DataType.BLE, schema_version="1", format="csv")
POSE = InternalValueContract(value_type="pose")
PARTICLE = InternalValueContract(value_type="particle")


def _slot(slot_id: str, contract: AssetContract | InternalValueContract) -> Slot:
    return Slot(slot_id=slot_id, accepted_contracts=(contract,))


def _component(
    component_id: str, instance_id: str, inputs: tuple[Slot, ...], output: Slot
) -> ComponentContract:
    return ComponentContract(
        component_id=component_id,
        instance_id=instance_id,
        input_slots=inputs,
        output_slots=(output,),
        parameters_schema={"type": "object"},
    )


def initial_catalog() -> tuple[PipelineDefinition, ...]:
    acce, gyro, ble = _slot("acce", ACCE), _slot("gyro", GYRO), _slot("ble", BLE)
    pose, particle = _slot("pose", POSE), _slot("particle", PARTICLE)
    pdr = _component("pdr", "pdr-1", (acce, gyro), pose)
    pdr_bindings = (
        SlotBinding(
            target_component_instance="pdr-1",
            target_slot_id="acce",
            source_slot_id="acce",
        ),
        SlotBinding(
            target_component_instance="pdr-1",
            target_slot_id="gyro",
            source_slot_id="gyro",
        ),
    )
    return (
        PipelineDefinition(
            pipeline_id="pdr",
            display_name="PDR",
            definition_version="1.0.0",
            components=(pdr,),
            input_slots=(acce, gyro),
            bindings=pdr_bindings,
            outputs=(
                PipelineOutput(
                    output_slot_id="pose",
                    source_component_instance="pdr-1",
                    source_slot_id="pose",
                ),
            ),
            parameters_schema={"type": "object"},
        ),
        PipelineDefinition(
            pipeline_id="pdr-particle-filter",
            display_name="PDR + Particle Filter",
            definition_version="1.0.0",
            components=(pdr, _component("particle-filter", "pf-1", (pose,), particle)),
            input_slots=(acce, gyro),
            bindings=pdr_bindings
            + (
                SlotBinding(
                    target_component_instance="pf-1",
                    target_slot_id="pose",
                    source_component_instance="pdr-1",
                    source_slot_id="pose",
                ),
            ),
            outputs=(
                PipelineOutput(
                    output_slot_id="particle",
                    source_component_instance="pf-1",
                    source_slot_id="particle",
                ),
            ),
            parameters_schema={"type": "object"},
        ),
        PipelineDefinition(
            pipeline_id="pdr-ble",
            display_name="PDR + BLE",
            definition_version="1.0.0",
            components=(
                pdr,
                _component("ble-fusion", "ble-fusion-1", (pose, ble), pose),
            ),
            input_slots=(acce, gyro, ble),
            bindings=pdr_bindings
            + (
                SlotBinding(
                    target_component_instance="ble-fusion-1",
                    target_slot_id="pose",
                    source_component_instance="pdr-1",
                    source_slot_id="pose",
                ),
                SlotBinding(
                    target_component_instance="ble-fusion-1",
                    target_slot_id="ble",
                    source_slot_id="ble",
                ),
            ),
            outputs=(
                PipelineOutput(
                    output_slot_id="pose",
                    source_component_instance="ble-fusion-1",
                    source_slot_id="pose",
                ),
            ),
            parameters_schema={"type": "object"},
        ),
        PipelineDefinition(
            pipeline_id="pdr-particle-filter-ble",
            display_name="PDR + Particle Filter + BLE",
            definition_version="1.0.0",
            components=(
                pdr,
                _component("particle-filter", "pf-1", (pose,), particle),
                _component("ble-fusion", "ble-fusion-1", (particle, ble), pose),
            ),
            input_slots=(acce, gyro, ble),
            bindings=pdr_bindings
            + (
                SlotBinding(
                    target_component_instance="pf-1",
                    target_slot_id="pose",
                    source_component_instance="pdr-1",
                    source_slot_id="pose",
                ),
                SlotBinding(
                    target_component_instance="ble-fusion-1",
                    target_slot_id="particle",
                    source_component_instance="pf-1",
                    source_slot_id="particle",
                ),
                SlotBinding(
                    target_component_instance="ble-fusion-1",
                    target_slot_id="ble",
                    source_slot_id="ble",
                ),
            ),
            outputs=(
                PipelineOutput(
                    output_slot_id="pose",
                    source_component_instance="ble-fusion-1",
                    source_slot_id="pose",
                ),
            ),
            parameters_schema={"type": "object"},
        ),
    )
