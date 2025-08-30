# tester_phase3_market.py
# End-to-end tests for Phase-3 marketplace endpoints in app.py
#
# What it verifies:
# 1) Offer creation rejects bad input (amount=0)
# 2) Offer creation succeeds for a valid producer credit
# 3) Buying more than available fails
# 4) Partial buy succeeds (offer remains open)
# 5) Final buy closes offer
# 6) Buying a closed offer fails
# 7) Retirements reporting endpoint responds (doesn't assert content)
#
# Prereqs:
# - Your Flask server running with the marketplace endpoints:
#     POST   /api/v1/market/offers
#     GET    /api/v1/market/offers
#     GET    /api/v1/market/offers/<offer_id>
#     POST   /api/v1/market/buy
#     GET    /api/v1/reports/retirements
# - A producer account, a buyer account, and a sellable credit owned by the producer.
# - You can use SMT endpoints to inspect balances (optional).
#
# Usage example:
#   python tester_phase3_market.py \
#       --base http://127.0.0.1:5000 \
#       --producer 68b327fc742e3da17f4013a5 \
#       --buyer    68b327fd742e3da17f4013a7 \
#       --credit   68b327ff742e3da17f4013af \
#       --offer-amount 5000 \
#       --buy1 2000 \
#       --buy2 3000
#
# Exit codes:
#   0 = all tests passed
#   1 = HTTP error / unexpected status
#   2 = Assertion failed (logic did not behave as expected)

import argparse
import json
import sys
from datetime import datetime
import requests

def pretty(x): return json.dumps(x, indent=2)

def must_ok(resp, expected_status=200):
    if resp.status_code != expected_status:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        raise SystemExit(f"[HTTP {resp.request.method} {resp.request.url}] "
                         f"Expected {expected_status}, got {resp.status_code}:\n{pretty(body)}")

def assert_true(cond, msg):
    if not cond:
        print("ASSERT FAILED:", msg)
        sys.exit(2)

def get_state_balance(base, account_id):
    """Optional helper via Phase-2 endpoint; if not available, skip."""
    try:
        r = requests.get(f"{base}/api/v2/state/proof/{account_id}", timeout=30)
        if r.status_code == 200:
            bal = r.json().get("balance_g")
            return int(bal) if bal is not None else None
    except Exception:
        pass
    return None

def main():
    ap = argparse.ArgumentParser(description="Phase-3 Marketplace tester")
    ap.add_argument("--base", required=True, help="Server base URL, e.g. http://127.0.0.1:5000")
    ap.add_argument("--producer", required=True, help="Producer account_id (stringified ObjectId)")
    ap.add_argument("--buyer", required=True, help="Buyer account_id (stringified ObjectId)")
    ap.add_argument("--credit", required=True, help="Producer credit_id to sell (stringified ObjectId)")
    ap.add_argument("--offer-amount", type=int, default=5000, help="Amount to list in offer (g)")
    ap.add_argument("--price", type=float, default=0.1, help="Price per g (demo only)")
    ap.add_argument("--buy1", type=int, default=2000, help="First buy amount (g)")
    ap.add_argument("--buy2", type=int, default=3000, help="Second buy amount (g)")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    t0 = datetime.utcnow().isoformat() + "Z"
    print("== Phase-3 Marketplace Tester ==")
    print("Base:", base)
    print("Time:", t0)
    print("Producer:", args.producer)
    print("Buyer   :", args.buyer)
    print("Credit  :", args.credit)

    # Optional: show balances via SMT
    pb = get_state_balance(base, args.producer)
    bb = get_state_balance(base, args.buyer)
    if pb is not None and bb is not None:
        print(f"[Info] Producer balance_g={pb}, Buyer balance_g={bb} (from SMT)")

    # ---------- 1) Offer creation rejects bad input ----------
    print("\n[TEST 1] Offer creation must reject amount_g=0 ...")
    r = requests.post(f"{base}/api/v1/market/offers", json={
        "producer_id": args.producer,
        "credit_id": args.credit,
        "amount_g": 0,
        "price_per_g": args.price
    }, timeout=30)
    # Expect 400
    assert_true(r.status_code == 400, f"Expected 400 for bad offer, got {r.status_code}: {r.text}")
    print("PASS")

    # ---------- 2) Offer creation succeeds ----------
    print("\n[TEST 2] Offer creation succeeds ...")
    r = requests.post(f"{base}/api/v1/market/offers", json={
        "producer_id": args.producer,
        "credit_id": args.credit,
        "amount_g": args.offer_amount,
        "price_per_g": args.price
    }, timeout=30)
    must_ok(r, 201)
    offer = r.json()
    print("Offer:", pretty(offer))
    offer_id = offer.get("id")
    assert_true(offer_id, "offer id missing")
    assert_true(offer.get("status") == "open", "offer not open after creation")

    # ---------- 3) Buy exceeding available fails ----------
    print("\n[TEST 3] Buy exceeding available fails ...")
    r = requests.post(f"{base}/api/v1/market/buy", json={
        "buyer_id": args.buyer,
        "offer_id": offer_id,
        "amount_g": args.offer_amount + 1  # deliberately exceed
    }, timeout=30)
    assert_true(r.status_code == 400, f"Expected 400 for exceeding buy, got {r.status_code}: {r.text}")
    print("PASS")

    # ---------- 4) Partial buy succeeds ----------
    print("\n[TEST 4] Partial buy succeeds; offer remains open ...")
    r = requests.post(f"{base}/api/v1/market/buy", json={
        "buyer_id": args.buyer,
        "offer_id": offer_id,
        "amount_g": args.buy1
    }, timeout=30)
    must_ok(r, 201)
    res1 = r.json()
    print("Buy #1:", pretty(res1))
    assert_true(res1.get("ok") is True, "buy1 not ok")
    left_after_1 = res1.get("offer_left")
    assert_true(left_after_1 == (args.offer_amount - args.buy1), "offer_left wrong after buy1")
    assert_true(res1.get("offer_status") == "open", "offer should still be open after partial buy")

    # ---------- 5) Final buy closes offer ----------
    print("\n[TEST 5] Final buy closes offer ...")
    r = requests.post(f"{base}/api/v1/market/buy", json={
        "buyer_id": args.buyer,
        "offer_id": offer_id,
        "amount_g": args.buy2
    }, timeout=30)
    must_ok(r, 201)
    res2 = r.json()
    print("Buy #2:", pretty(res2))
    assert_true(res2.get("ok") is True, "buy2 not ok")
    left_after_2 = res2.get("offer_left")
    assert_true(left_after_2 == 0, "offer_left should be 0 after final buy")
    assert_true(res2.get("offer_status") == "closed", "offer should be closed after final buy")

    # ---------- 6) Buying a closed offer fails ----------
    print("\n[TEST 6] Buy on a closed offer must fail ...")
    r = requests.post(f"{base}/api/v1/market/buy", json={
        "buyer_id": args.buyer,
        "offer_id": offer_id,
        "amount_g": 1
    }, timeout=30)
    assert_true(r.status_code == 400, f"Expected 400 on closed offer, got {r.status_code}: {r.text}")
    print("PASS")

    # ---------- 7) Retirements report endpoint works ----------
    print("\n[TEST 7] Retirements report responds ...")
    r = requests.get(f"{base}/api/v1/reports/retirements", timeout=30)
    must_ok(r, 200)
    report = r.json()
    # Only assert presence/shape; content depends on whether retire calls occurred in your run.
    assert_true(isinstance(report, dict) and "retirements" in report, "report shape invalid")
    print("Report sample:", pretty(report if len(pretty(report)) < 1500 else {'note':'large payload ok'}))
    print("\n✅ ALL TESTS PASSED")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        print("HTTP error:", e)
        sys.exit(1)
