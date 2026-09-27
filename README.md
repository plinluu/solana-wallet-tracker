# Solana Wallet Tracker

Check any Solana wallet's SOL balance and recent transactions from your terminal.
No installs, no API keys — Python 3.8+ stdlib only.

## Run it

```bash
python3 tracker.py <WALLET_ADDRESS>
python3 tracker.py <WALLET_ADDRESS> --usd        # include USD value
python3 tracker.py <WALLET_ADDRESS> -n 10        # show 10 recent transactions
python3 tracker.py <WALLET_ADDRESS> --watch 60   # refresh every 60 seconds
```

## Example

```bash
$ python3 tracker.py 11111111111111111111111111111111 -n 3
Wallet:  11111111111111111111111111111111
Balance: 0.000000001 SOL

Last 3 transactions:
TIME                CHANGE (SOL)  STATUS  SIGNATURE
------------------------------------------------------------------------------------------
2026-09-27 00:00:00  +0.000000000  ok      4vJ9JU7d1aKx...
...
```

## How it works

- Balance via the `getBalance` Solana JSON-RPC method
- History via `getSignaturesForAddress` + `getTransaction`
- Net SOL change per transaction from pre/post balances
- Optional USD price from CoinGecko's free API

Uses the public `api.mainnet-beta.solana.com` endpoint (rate-limited).
For heavy or watch-mode use, point `RPC_URL` at your own Helius/Alchemy endpoint.

## Ideas to extend

- Alert when balance changes past a threshold
- Track SPL token balances with `getTokenAccountsByOwner`
- Export history to CSV
