"""Live Ollama verification (Phase 5).

Run this on a machine with a real local Ollama server + qwen2.5:3b
pulled -- it cannot be run from the sandboxed environment Phase 5 was
built in, since that environment has no network access to ollama.com to
install Ollama, and no route to your machine's localhost either.

What it does, using EXISTING local data only (no destructive changes):
  1. Confirms Ollama is reachable (GET /api/tags).
  2. Picks 1-3 existing RecoveryCase rows from the local Postgres database
     (does not create any).
  3. Calls the real /api/recovery/opportunities/{id}/ai-recommend endpoint
     against your running FastAPI backend for each one.
  4. Prints the full result: AI status, parsed recommendation, the
     deterministic comparison, safety validation outcome, and whether a
     fallback was used.

It does NOT plan/validate/execute any recovery action, and it does NOT
process the full 1,412-case dataset -- by design, per Phase 5's
performance constraints (no GPU, ~8GB RAM).

Usage (from backend/, with the venv active and the FastAPI server
already running on http://localhost:8000):

    python scripts/verify_live_ollama.py
    python scripts/verify_live_ollama.py --count 3
    python scripts/verify_live_ollama.py --api-base-url http://localhost:8000
"""

import argparse
import json
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=2, help="How many cases to test (1-3 recommended). Default: 2.")
    parser.add_argument(
        "--api-base-url",
        default="http://localhost:8000",
        help="Base URL of the running RecoverAI backend. Default: http://localhost:8000",
    )
    parser.add_argument(
        "--ollama-base-url",
        default="http://localhost:11434",
        help="Base URL of the local Ollama server, for the initial reachability check.",
    )
    args = parser.parse_args()

    if args.count > 3:
        print("Refusing to run more than 3 cases through the live model -- pass --count 1, 2, or 3.")
        sys.exit(1)

    print(f"1. Checking Ollama is reachable at {args.ollama_base_url} ...")
    try:
        tags_response = httpx.get(f"{args.ollama_base_url}/api/tags", timeout=5.0)
        tags_response.raise_for_status()
        models = [m.get("name") for m in tags_response.json().get("models", [])]
        print(f"   OK -- Ollama is up. Locally available models: {models}")
    except httpx.HTTPError as exc:
        print(f"   FAILED -- could not reach Ollama: {exc}")
        print("   Make sure `ollama serve` is running and qwen2.5:3b has been pulled.")
        sys.exit(1)

    print(f"\n2. Fetching {args.count} existing recovery opportunity IDs from {args.api_base_url} ...")
    try:
        list_response = httpx.get(
            f"{args.api_base_url}/api/recovery/opportunities",
            params={"limit": args.count},
            timeout=10.0,
        )
        list_response.raise_for_status()
        opportunities = list_response.json()["opportunities"]
    except httpx.HTTPError as exc:
        print(f"   FAILED -- could not reach the RecoverAI backend: {exc}")
        print("   Make sure `uvicorn app.main:app` is running.")
        sys.exit(1)

    if not opportunities:
        print("   No recovery opportunities found. Run `python -m app.data_generation.seed` and")
        print("   `curl -X POST .../api/recovery/detect` first.")
        sys.exit(1)

    case_ids = [o["recovery_case_id"] for o in opportunities][: args.count]
    print(f"   Using case IDs: {case_ids}")

    print("\n3. Calling POST /ai-recommend for each case (this invokes the real local model) ...")
    for case_id in case_ids:
        print(f"\n--- {case_id} ---")
        try:
            response = httpx.post(
                f"{args.api_base_url}/api/recovery/opportunities/{case_id}/ai-recommend",
                timeout=120.0,  # a 3B model on CPU can be slow for the first call
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"   Request failed: {exc}")
            continue

        result = response.json()
        print(json.dumps(result, indent=2))

        if result["ai_status"] == "ok":
            print(
                f"   -> AI recommended '{result['ai_recommended_action']}' "
                f"(confidence {result['ai_confidence']}, risk {result['ai_risk_level']})"
            )
            print(f"   -> Deterministic action was '{result['deterministic_action']}'")
            print(f"   -> Agreement: {result['agreement']}")
            print(f"   -> Safety validation: {result['safety_validation_result']}")
            print(f"   -> Fallback used: {result['fallback_used']} | Effective action: {result['effective_action']}")
        else:
            print(f"   -> AI call did not succeed (status: {result['ai_status']}); fell back to the deterministic action.")

    print("\nDone. No recovery action was planned, validated, or executed -- ai-recommend is advisory only.")
    print("Check GET /api/recovery/ai-summary for the aggregate view of everything just recorded.")


if __name__ == "__main__":
    main()
