# Okarin contract mirror

The `acce.v1.json` and `gyro.v1.json` files are vendored from [Okarin PR
#263](https://github.com/kajiLabTeam/okarin/pull/263) at commit
[`e1b65c6`](https://github.com/kajiLabTeam/okarin/commit/e1b65c6). The owning
integration team must refresh this mirror from that upstream source. SHA-256 of
the current files:

- `acce.v1.json`: `c96e29f8a62eaf8d5b63564edcdd04b3b57ffdbc343c8e671312ba65f68de8e3`
- `gyro.v1.json`: `193d8ecaf97eabb0923744d5e01942998a721c94f096288cc0b16aca61f1136a`

BLE is deliberately not vendored: Okarin's catalog does not implement it yet;
the Pipeline definition references the DesignDoc CSV contract only.
