# nozomi

## Pipeline Registry

`GET /pipelines` returns the immutable catalog of the four initial pipeline
definitions. Each entry includes typed slots, a definition version, state,
canonical JSON SHA-256 digest, and an `availability` result. The internal
resolution endpoint is `GET /internal/pipelines/{pipeline_id}`; it returns the
same immutable snapshot for one active id, including `available=false` and its
structured reason, and responds with 404 only for an unknown id or an id with
no active version. Execution-start and unavailable (409) handling belong to a
future execution API, not this resolve contract.

Availability is evaluated through Nozomi's `ComponentAdapter` capability
boundary. The current `RikkaAdapter` deliberately wraps the available Rikka
surface without changing Rikka or copying its execution algorithms. Therefore
an unsupported composition remains in the catalog but is not advertised as
available, and includes a capability-mismatch reason.

Asset slots are explicit contracts: the initial PDR definition uses Okarin's
`acce.v1` and `gyro.v1` assets (data types `acce` and `gyro`, schema version
`1`, CSV format). BLE follows the DesignDoc contract (`ble`, schema version
`1`, CSV), but is not yet implemented in the Okarin catalog. Pipeline
components have instance IDs and explicit linear bindings; resource slots
`resource.floor_map` (PNG/SVG) and `resource.beacon_layout` (JSON) are future
contracts only. They are not vendor files and keep these pipelines unavailable
until Okarin publishes the corresponding catalog contracts.

This boundary enables staged adoption without changing Rikka: capabilities can
be added to the adapter as Rikka evolves, while future pipeline definitions can
be cataloged before their components are executable. The initial specification
allows at most one asset per slot; arbitrary DAGs, multiple assets per slot,
and job delivery are intentionally out of scope. Internal/public API
separation is represented by the `/internal` route for now; no bespoke
authentication layer is introduced. A reverse proxy or service identity is
required before exposing that route outside a trusted service boundary.

Canonical digests use UTF-8 JSON with sorted keys, compact separators, omitted
nulls, and SHA-256. Parameter schemas are limited to finite JSON objects with
`type: object`; no external schema dependency is used. External asset contracts
and internal values are separate: `pose` and `particle` are internal values;
Nozomi #7 will define the formal output asset contract later.

# 開発コマンド

python versionは`3.14`
パッケージ管理は`uv`

## 実行コマンド
```sh
$ uv run main.py
```

python fastapiの実行
```sh
$ uv run fastapi dev main.py
```

### uvのセットアップ

`uv venv`
`. .venv/bin/activate`
`uv sync`
`uv run main.py`

### uvでパッケージの追加

`uv add hoge`

# コミット前に以下のコマンドをする
## フォーマッター

```sh
$ uv run ruff format .
```

## リンター

```sh
uv run ruff check .
```

## 型チェック

```sh
uv run mypy src main.py tests
uv run pytest
```
