# Reviews

`pending/` contains unfinished proposals; `applied/` contains completed apply payloads once. `archive/` stores original historical review files losslessly. Only `data/registry.json` represents current state.

A proposal using a `changes` array is not an apply payload. Review ownership and construct supported table rows before `registry apply`. After successful apply, move the payload from pending to applied; do not leave a copied pending version. See `../docs/review.md`.
