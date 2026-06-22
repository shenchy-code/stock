# Fund Strategy Board Design

## Goal

Add an independent "基金策略" tab that uses the existing saved fund list and latest fund data to produce portfolio-level trading guidance, per-fund actions, position rebalancing amounts, and scenario-based profit expectations.

## Scope

- Add a new strategy calculation module with no dependency on Flask or browser code.
- Store user-entered position inputs per fund: buy price and invested amount.
- Read existing fund quote/detail data through the current backend functions.
- Add dedicated strategy APIs without changing the existing holdings and money-flow behavior.
- Add a third frontend tab using a dashboard-first layout.

## Assumptions

- First version requires only buy price and invested amount.
- Available extra cash is not tracked; rebalancing is calculated against current invested portfolio value.
- Subscription/redemption fees, taxes, and settlement timing are not included.
- Profit expectations are scenario estimates, not guarantees.

## API Shape

- `GET /api/strategy` returns saved position inputs, latest fund data, per-fund strategy items, and portfolio overview.
- `POST /api/strategy/positions` saves position inputs for the current fund pool.

## Strategy Output

Each fund receives:

- score from 0 to 100
- action: buy, hold, reduce, sell, or input
- target weight
- current value and estimated profit based on buy price
- rebalance amount
- short explanation

The overview shows total invested amount, estimated current value, estimated profit, risk level, recommended action summary, and conservative/base/optimistic one-month scenario estimates.

## Isolation

The new feature writes only new strategy data under `funds_data.json.positions`. Existing `funds`, `stocks`, and money-flow behavior stay unchanged.
