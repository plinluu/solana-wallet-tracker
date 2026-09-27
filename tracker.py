#!/usr/bin/env python3
"""Solana wallet tracker - check any wallet's SOL balance and recent transactions.

Stdlib only: no pip installs, no API keys. Uses the public Solana RPC.
For heavy use, swap RPC_URL for your own endpoint (e.g. Helius, Alchemy).
"""

import argparse
import datetime
import json
import sys
import time
import urllib.request

RPC_URL = "https://api.mainnet-beta.solana.com"
LAMPORTS_PER_SOL = 1_000_000_000


def rpc_call(method, params):
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
    req = urllib.request.Request(
        RPC_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except Exception as exc:
        raise RuntimeError(f"RPC request failed ({method}): {exc}")
    if data.get("error"):
        raise RuntimeError(f"RPC error ({method}): {data['error']}")
    return data["result"]


def get_balance(address):
    """Return SOL balance for an address."""
    lamports = rpc_call("getBalance", [address])["value"]
    return lamports / LAMPORTS_PER_SOL


def get_sol_usd():
    """Return current SOL price in USD (CoinGecko, free tier)."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.load(resp)["solana"]["usd"]


def get_recent_txs(address, limit):
    """Return recent transactions with this wallet's net SOL change each."""
    sigs = rpc_call("getSignaturesForAddress", [address, {"limit": limit}])
    txs = []
    for entry in sigs:
        sig = entry["signature"]
        tx = rpc_call(
            "getTransaction", [sig, {"encoding": "json", "maxSupportedTransactionVersion": 1}]
        )
        if tx is None:  # not yet finalized/indexed, skip
            continue
        meta = tx.get("meta") or {}
        keys = tx["transaction"]["message"].get("accountKeys", [])
        # accountKeys may be strings or {"pubkey": ...} objects
        normalized = [k if isinstance(k, str) else k.get("pubkey") for k in keys]
        # v0/v1 transactions can pull extra addresses from lookup tables;
        # pre/post balances cover static keys first, then loaded ones
        loaded = meta.get("loadedAddresses") or {}
        full_keys = normalized + loaded.get("writable", []) + loaded.get("readonly", [])
        try:
            idx = full_keys.index(address)
        except ValueError:
            continue  # wallet not involved in this tx
        pre = meta.get("preBalances", [])
        post = meta.get("postBalances", [])
        change = (
            (post[idx] - pre[idx]) / LAMPORTS_PER_SOL
            if idx < len(pre) and idx < len(post)
            else 0.0
        )
        block_time = tx.get("blockTime")
        when = (
            datetime.datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S")
            if block_time
            else "unknown"
        )
        txs.append(
            {
                "signature": sig,
                "time": when,
                "change_sol": change,
                "status": "FAILED" if meta.get("err") else "ok",
            }
        )
    return txs


def show(address, limit, with_usd):
    balance = get_balance(address)
    print(f"Wallet:  {address}")
    print(f"Balance: {balance:.9f} SOL", end="")
    if with_usd:
        try:
            price = get_sol_usd()
            print(f"  (~${balance * price:,.2f} @ ${price:,.2f}/SOL)")
        except Exception as exc:
            print(f"  (USD price unavailable: {exc})")
    else:
        print()
    print(f"\nLast {limit} transactions:")
    print(f"{'TIME':<19} {'CHANGE (SOL)':>12}  STATUS  SIGNATURE")
    print("-" * 90)
    for t in get_recent_txs(address, limit):
        sign = "+" if t["change_sol"] >= 0 else ""
        print(
            f"{t['time']:<19} {sign}{t['change_sol']:>11.9f}  {t['status']:<6}  "
            f"{t['signature'][:16]}..."
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Track a Solana wallet's balance and recent transactions."
    )
    parser.add_argument("address", help="Solana wallet address to track")
    parser.add_argument(
        "-n", "--num-txs", type=int, default=5, help="recent transactions to show (default: 5)"
    )
    parser.add_argument(
        "--usd", action="store_true", help="also show balance in USD via CoinGecko"
    )
    parser.add_argument(
        "--watch",
        type=int,
        metavar="SECONDS",
        default=0,
        help="refresh every SECONDS (default: run once)",
    )
    args = parser.parse_args(argv)

    try:
        if args.watch > 0:
            while True:
                print(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===")
                show(args.address, args.num_txs, args.usd)
                time.sleep(args.watch)
        else:
            show(args.address, args.num_txs, args.usd)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
