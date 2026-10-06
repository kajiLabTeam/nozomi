import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from nozomi.adapter import RikkaAdapter
from nozomi.catalog import (
    ACCE,
    BEACON_LAYOUT,
    FLOOR_MAP_PNG,
    FLOOR_MAP_SVG,
    GYRO,
    initial_catalog,
)
from nozomi.models import (
    AssetContract,
    ComponentContract,
    DataType,
    PipelineOutput,
    PipelineState,
    Slot,
    SlotBinding,
)
from nozomi.registry import PipelineRegistry, canonical_digest


def test_catalog_has_four_linear_definitions_and_specific_pdr_slots() -> None:
    catalog = initial_catalog()
    assert len(catalog) == 4
    assert [s.slot_id for s in catalog[0].input_slots] == ["acce", "gyro"]
    assert catalog[0].input_slots[0].accepted_contracts == (ACCE,)
    assert catalog[0].input_slots[1].accepted_contracts == (GYRO,)
    assert any(c.component_id == "ble-fusion" for c in catalog[2].components)


def test_each_pipeline_external_slots_and_accepted_contracts_are_fixed() -> None:
    catalog = initial_catalog()
    assert [s.slot_id for s in catalog[0].input_slots] == ["acce", "gyro"]
    assert [s.slot_id for s in catalog[1].input_slots] == ["acce", "gyro", "floor_map"]
    assert [s.slot_id for s in catalog[2].input_slots] == [
        "acce",
        "gyro",
        "ble",
        "floor_map",
        "beacon_layout",
    ]
    assert [s.slot_id for s in catalog[3].input_slots] == [
        "acce",
        "gyro",
        "ble",
        "floor_map",
        "beacon_layout",
    ]
    assert catalog[1].input_slots[2].accepted_contracts == (
        FLOOR_MAP_PNG,
        FLOOR_MAP_SVG,
    )
    assert catalog[2].input_slots[-1].accepted_contracts == (BEACON_LAYOUT,)
    assert catalog[3].input_slots[2].accepted_contracts == (
        catalog[2].input_slots[2].accepted_contracts[0],
    )


@pytest.mark.parametrize(
    ("name", "expected_hash", "contract"),
    [
        (
            "acce",
            "c96e29f8a62eaf8d5b63564edcdd04b3b57ffdbc343c8e671312ba65f68de8e3",
            ACCE,
        ),
        (
            "gyro",
            "193d8ecaf97eabb0923744d5e01942998a721c94f096288cc0b16aca61f1136a",
            GYRO,
        ),
    ],
)
def test_vendored_contract_hash_and_catalog_triad(
    name: str, expected_hash: str, contract: AssetContract
) -> None:
    path = Path(__file__).parents[1] / "contracts" / "data-types" / f"{name}.v1.json"
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_hash
    document = json.loads(raw)
    assert (contract.data_type.value, contract.schema_version, contract.format) == (
        document["data_type"],
        document["schema_version"],
        document["format"],
    )


def test_strict_asset_slot_and_parameters_schema() -> None:
    with pytest.raises(ValidationError):
        Slot(slot_id="x", accepted_contracts=(ACCE,), max_assets=2)
    with pytest.raises(ValidationError):
        ComponentContract(
            component_id="x", instance_id="x-1", parameters_schema={"type": "string"}
        )
    with pytest.raises(ValidationError):
        AssetContract(
            data_type=DataType.ACCE, schema_version="bad version", format="json"
        )


def test_component_rejects_duplicate_input_and_output_slot_ids() -> None:
    slot = Slot(slot_id="input", accepted_contracts=(ACCE,))
    with pytest.raises(ValidationError, match="input slot ids must be unique"):
        ComponentContract(
            component_id="component",
            instance_id="component-1",
            input_slots=(slot, slot),
            parameters_schema={"type": "object"},
        )
    with pytest.raises(ValidationError, match="output slot ids must be unique"):
        ComponentContract(
            component_id="component",
            instance_id="component-1",
            output_slots=(slot, slot),
            parameters_schema={"type": "object"},
        )


def test_digest_fixed_and_order_independent() -> None:
    definition = initial_catalog()[0]
    reordered = definition.model_copy(
        update={"parameters_schema": {"properties": {}, "type": "object"}}
    )
    equivalent = definition.model_copy(
        update={"parameters_schema": {"type": "object", "properties": {}}}
    )
    same = definition.model_copy(deep=True)
    assert canonical_digest(definition) == canonical_digest(same)
    assert canonical_digest(reordered) == canonical_digest(equivalent)
    assert (
        canonical_digest(definition)
        == "4ef35b55455927e335bd4277c9bca5c6df9151cedbe97fb41fbe7673b7353bb5"
    )


def test_resource_pipeline_digests_are_fixed() -> None:
    assert [canonical_digest(definition) for definition in initial_catalog()] == [
        "4ef35b55455927e335bd4277c9bca5c6df9151cedbe97fb41fbe7673b7353bb5",
        "a99f539ae6fe8ae311fdb4685f4e412aee955f464c5b702bdbab54af1a5dbc22",
        "5914c6f3c48f1217516d53f25011f07b3fd67fa67f64d141ea39d654aa106c1c",
        "2131c884f83f508168b85daab0410712819f247f38eaee468b27edc1b2842e38",
    ]


def test_registry_detects_binding_type_mismatch_and_duplicate_active() -> None:
    definition = initial_catalog()[0]
    bad = definition.model_copy(update={"bindings": ()})
    with pytest.raises(ValueError, match="bindings must match"):
        PipelineRegistry((bad,), RikkaAdapter())
    with pytest.raises(ValueError, match="one active"):
        PipelineRegistry(
            (definition, definition.model_copy(update={"definition_version": "2.0.0"})),
            RikkaAdapter(),
        )


def test_binding_rejects_unknown_target_and_backward_source() -> None:
    definition = initial_catalog()[0]
    unknown = definition.model_copy(
        update={
            "bindings": definition.bindings
            + (
                SlotBinding(
                    target_component_instance="missing",
                    target_slot_id="x",
                    source_slot_id="acce",
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="bindings must match"):
        PipelineRegistry((unknown,), RikkaAdapter())
    definition = initial_catalog()[1]
    backward = definition.model_copy(
        update={
            "bindings": tuple(
                SlotBinding(
                    target_component_instance="pf-1",
                    target_slot_id="pose",
                    source_component_instance="pf-1",
                    source_slot_id="particle",
                )
                if (b.target_component_instance, b.target_slot_id) == ("pf-1", "pose")
                else b
                for b in definition.bindings
            )
        }
    )
    with pytest.raises(ValueError, match="precede"):
        PipelineRegistry((backward,), RikkaAdapter())


def test_binding_rejects_actual_source_target_contract_mismatch() -> None:
    definition = initial_catalog()[1]
    mismatch = definition.model_copy(
        update={
            "bindings": (
                *(
                    b.model_copy(update={"source_slot_id": "gyro"})
                    if (b.target_component_instance, b.target_slot_id)
                    == ("pf-1", "pose")
                    else b
                    for b in definition.bindings
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="binding type mismatch"):
        PipelineRegistry((mismatch,), RikkaAdapter())


def test_output_ids_and_fourth_pipeline_wiring() -> None:
    definition = initial_catalog()[3]
    assert [
        (b.target_component_instance, b.target_slot_id) for b in definition.bindings
    ] == [
        ("pdr-1", "acce"),
        ("pdr-1", "gyro"),
        ("pf-1", "pose"),
        ("pf-1", "floor_map"),
        ("ble-fusion-1", "particle"),
        ("ble-fusion-1", "ble"),
        ("ble-fusion-1", "beacon_layout"),
    ]
    duplicate = definition.model_copy(
        update={
            "outputs": definition.outputs
            + (
                PipelineOutput(
                    output_slot_id="pose",
                    source_component_instance="ble-fusion-1",
                    source_slot_id="pose",
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="output slot"):
        PipelineRegistry((duplicate,), RikkaAdapter())


def test_registry_snapshot_is_immune_to_returned_mutation() -> None:
    registry = PipelineRegistry((initial_catalog()[0],), RikkaAdapter())
    first = registry.resolve("pdr")
    assert first is not None
    first.definition.parameters_schema["changed"] = True
    second = registry.resolve("pdr")
    assert second is not None
    assert "changed" not in second.definition.parameters_schema
    assert first.digest == second.digest


def test_retired_not_resolved_and_rikka_does_not_fake_availability() -> None:
    retired = initial_catalog()[0].model_copy(update={"state": PipelineState.RETIRED})
    assert PipelineRegistry((retired,), RikkaAdapter()).resolve("pdr") is None
    entry = PipelineRegistry((initial_catalog()[0],), RikkaAdapter()).catalog()[0]
    assert not entry.availability.available
    assert entry.availability.reason is not None
    assert entry.availability.reason.code == "unsupported_component"


def test_api_models_and_structured_errors() -> None:
    client = TestClient(app)
    response = client.get("/pipelines")
    assert response.status_code == 200
    assert len(response.json()) == 4
    unavailable = client.get("/internal/pipelines/pdr")
    assert unavailable.status_code == 200
    assert unavailable.json()["availability"]["available"] is False
    assert (
        unavailable.json()["availability"]["reason"]["code"] == "unsupported_component"
    )
    assert unavailable.json()["digest"] == response.json()[0]["digest"]
    schema = app.openapi()
    assert "ErrorEnvelope" in str(schema["components"]["schemas"])
    assert (
        "409"
        not in schema["paths"]["/internal/pipelines/{pipeline_id}"]["get"]["responses"]
    )
    missing = client.get("/internal/pipelines/missing")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "unknown_pipeline"
