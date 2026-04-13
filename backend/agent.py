#!/usr/bin/env python3
"""
Sploink Agent Simulator CLI
============================
Simulates AI agent behavior across 4 scenarios:

  normal   — logical task progression, high success rate
  loop     — repeated actions with slight variations (not exact duplicates)
  drift    — intent shift mid-session (auth work → pipeline work)
  failure  — cascading failures with retries
  mixed    — multiple interleaved concurrent sessions

Usage:
  python agent.py --scenario normal
  python agent.py --scenario loop --session my-session-42
  python agent.py --scenario mixed --url http://localhost:8000
"""

import argparse
import random
import requests
import time
import uuid
import threading

BASE_URL = "http://localhost:8000"


def send_event(
    session_id: str,
    step: int,
    action: str,
    input_text: str,
    output_text: str,
    status: str = "success",
    file: str = None,
    delay: float = 0.15,
):
    payload = {
        "session_id": session_id,
        "timestamp": time.time(),
        "step": step,
        "action": action,
        "input": input_text,
        "output": output_text,
        "metadata": {"status": status, "file": file},
    }
    try:
        resp = requests.post(f"{BASE_URL}/events", json=payload, timeout=5)
        tag = resp.json().get("status", "?")
        status_icon = "✓" if status == "success" else "✗"
        print(f"  [{step:02d}] {status_icon} {action:<14} | {tag}")
    except Exception as e:
        print(f"  [{step:02d}] ERROR: {e}")
    time.sleep(delay + random.uniform(0, 0.05))


# ---------------------------------------------------------------------------
# Scenario: Normal
# ---------------------------------------------------------------------------

def simulate_normal(session_id: str):
    print(f"\n🟢 NORMAL | {session_id}")
    steps = [
        ("read_file",    "config.yaml",                                  "Loaded: model=gpt-4, temperature=0.7, max_tokens=2048",      "config.yaml",      "success"),
        ("llm_call",     "Analyze config and plan execution steps",       "Plan: 1) validate env 2) install deps 3) run tests 4) commit","",                "success"),
        ("run_command",  "pip install -r requirements.txt",               "Successfully installed 14 packages (0.8s)",                  "",                 "success"),
        ("read_file",    "src/main.py",                                   "Read 312 lines. Module: data_processor",                     "src/main.py",      "success"),
        ("llm_call",     "Review main.py for bugs and code quality issues","Found: null-check missing line 45, off-by-one at line 78",   "",                "success"),
        ("write_file",   "src/main.py — applied 2 fixes",                 "Wrote 314 lines successfully",                               "src/main.py",      "success"),
        ("run_command",  "pytest tests/ -v --tb=short",                    "24 passed, 2 skipped in 3.41s",                             "",                 "success"),
        ("llm_call",     "Generate semantic commit message for the fixes", "fix: add null guard and correct loop boundary in main.py",   "",                "success"),
        ("run_command",  "git commit -am 'fix: null guard + loop boundary'","[main a3f9c2b] 1 file changed, 4 ins(+), 2 del(-)",         "",                "success"),
        ("write_file",   "CHANGELOG.md — append release note",             "CHANGELOG updated with v1.2.1 entry",                        "CHANGELOG.md",    "success"),
    ]
    for i, (action, inp, out, file, status) in enumerate(steps, 1):
        send_event(session_id, i, action, inp, out, status, file or None)


# ---------------------------------------------------------------------------
# Scenario: Loop
# ---------------------------------------------------------------------------

def simulate_loop(session_id: str):
    print(f"\n🔄 LOOP | {session_id}")

    # Normal start
    send_event(session_id, 1, "read_file", "src/processor.py",
               "Read 280 lines. Found process_data() function.", "success", "src/processor.py")
    send_event(session_id, 2, "llm_call",
               "Analyze process_data() in src/processor.py for recursion issue",
               "Detected unbounded recursion in process_data(). Missing base case.", "success")

    # Varied loop — slightly different inputs/outputs each time to avoid exact duplicates
    loop_templates = [
        ("run_command", "python debug_tool.py --check process_data",         "Error: RecursionError at depth {d}",          "failure"),
        ("run_command", "python debug_tool.py --check process_data --verbose","Error: RecursionError at depth {d} (verbose)","failure"),
        ("llm_call",    "How to fix RecursionError in process_data function?","Try adding base case: if depth > {d}: return None", "success"),
        ("run_command", "python debug_tool.py --validate process_data",       "Error: RecursionError persists, depth={d}",   "failure"),
        ("read_file",   "src/processor.py",                                   "Re-read processor.py, {d} lines checked",    "success"),
        ("llm_call",    "Re-analyze process_data recursion — attempt {d}",    "Root cause still unclear. Try memoization at depth {d}", "success"),
        ("run_command", "python debug_tool.py --memo process_data --limit {d}","Error: RecursionError with memo, limit={d}", "failure"),
        ("run_command", "python debug_tool.py --trace --depth {d}",           "Error: RecursionError during trace at {d}",  "failure"),
    ]

    for i in range(10):
        depth = random.randint(800, 1100)
        action, inp_tmpl, out_tmpl, status = random.choice(loop_templates)
        inp = inp_tmpl.format(d=depth)
        out = out_tmpl.format(d=depth)
        send_event(session_id, i + 3, action, inp, out, status)


# ---------------------------------------------------------------------------
# Scenario: Drift
# ---------------------------------------------------------------------------

def simulate_drift(session_id: str):
    print(f"\n📡 DRIFT | {session_id}")

    # Phase 1 — OAuth / auth work
    auth_phase = [
        (1,  "read_file",   "auth/oauth_handler.py",                            "Loaded OAuth handler (420 lines), PKCE flow present",              "auth/oauth_handler.py", "success"),
        (2,  "llm_call",    "Review OAuth2 token refresh logic in handler",      "PKCE flow correct; missing scope validation before token save",     "",                      "success"),
        (3,  "read_file",   "auth/token_store.py",                               "Loaded token_store.py (180 lines), save() lacks scope param",       "auth/token_store.py",   "success"),
        (4,  "run_command", "pytest auth/tests/ -v",                              "18/20 passed. FAIL: test_scope_validation, test_refresh_scope",     "",                      "failure"),
        (5,  "llm_call",    "Fix failing scope validation tests in auth module",  "Add scope: str param to token_store.save(), propagate to handler",  "",                      "success"),
        (6,  "write_file",  "auth/token_store.py — add scope parameter",          "Updated save() signature, 3 call sites patched",                   "auth/token_store.py",   "success"),
    ]

    for step, action, inp, out, file, status in auth_phase:
        send_event(session_id, step, action, inp, out, status, file or None)

    # Phase 2 — Drifts to unrelated ETL pipeline work
    pipeline_phase = [
        (7,  "read_file",   "pipeline/etl_processor.py",                         "Switching to ETL pipeline. Loaded batch_write() — 640 lines",      "pipeline/etl_processor.py","success"),
        (8,  "llm_call",    "Identify throughput bottleneck in ETL batch writer", "Bottleneck: batch_size=100 causes 10× extra DB round-trips",        "",                        "success"),
        (9,  "run_command", "python pipeline/benchmark.py --batch-size 1000",     "Throughput: 850 rows/s → 4,200 rows/s (+394%)",                    "",                        "success"),
        (10, "read_file",   "pipeline/schema_validator.py",                       "Loaded schema_validator.py. 12 type checks, 3 nullable fields",    "pipeline/schema_validator.py","success"),
        (11, "write_file",  "pipeline/etl_processor.py — batch size 1000",        "Committed batch-size config change, added fallback to 100",        "pipeline/etl_processor.py","success"),
        (12, "run_command", "python pipeline/run_full_pipeline.py --env staging",  "Pipeline OK: 1.24M rows in 296s. 0 schema errors",                "",                        "success"),
        (13, "llm_call",    "Generate ETL optimization performance report",        "Report: 5× throughput, CPU -40%, memory stable at 1.2 GB peak",   "",                        "success"),
    ]

    for step, action, inp, out, file, status in pipeline_phase:
        send_event(session_id, step, action, inp, out, status, file or None)


# ---------------------------------------------------------------------------
# Scenario: Failure
# ---------------------------------------------------------------------------

def simulate_failure(session_id: str):
    print(f"\n❌ FAILURE | {session_id}")

    send_event(session_id, 1, "read_file",   "deploy/k8s-config.yaml",
               "Loaded deployment spec: 3 replicas, image=myrepo/api:v2.1", "success", "k8s-config.yaml")
    send_event(session_id, 2, "llm_call",
               "Validate k8s config for production deployment",
               "Config valid. Proceed with kubectl apply.", "success")

    failures = [
        (3,  "run_command", "kubectl apply -f deploy/k8s-config.yaml",
             "Error: ImagePullBackOff — container 'api-server' cannot pull image",                 "failure"),
        (4,  "run_command", "kubectl describe pod api-server-7d8f9b-xxxx",
             "Error: Failed to pull 'myrepo/api:v2.1': 401 unauthorized",                         "failure"),
        (5,  "llm_call",    "How to resolve ImagePullBackOff for private registry?",
             "Add imagePullSecrets referencing a valid docker-registry secret",                    "success"),
        (6,  "run_command", "kubectl create secret docker-registry regcred --from-file=.docker/config.json",
             "Error: secret 'regcred' already exists",                                            "failure"),
        (7,  "run_command", "kubectl delete secret regcred",
             "Error: cannot delete secret 'regcred': permission denied for user 'ci-bot'",        "failure"),
        (8,  "run_command", "kubectl apply -f deploy/k8s-config.yaml --force",
             "Error: ImagePullBackOff persists after force apply",                                 "failure"),
        (9,  "llm_call",    "ImagePullBackOff persists after adding pull secret",
             "Verify imagePullSecrets is referenced in pod spec under spec.imagePullSecrets",      "success"),
        (10, "run_command", "kubectl get pods -n production",
             "Error: ci-bot cannot list pods in namespace 'production': forbidden",               "failure"),
        (11, "run_command", "kubectl apply -f deploy/k8s-config.yaml -n staging",
             "Error: ImagePullBackOff in staging namespace too",                                   "failure"),
        (12, "run_command", "kubectl rollout status deployment/api-server",
             "Error: deployment 'api-server' not found in current namespace",                     "failure"),
        (13, "run_command", "kubectl get deployments -A",
             "Error: ci-bot forbidden: cannot list deployments cluster-wide",                     "failure"),
    ]

    for step, action, inp, out, status in failures:
        send_event(session_id, step, action, inp, out, status)


# ---------------------------------------------------------------------------
# Scenario: Mixed (concurrent sessions)
# ---------------------------------------------------------------------------

def simulate_mixed(prefix: str):
    print(f"\n🌀 MIXED | prefix: {prefix}")
    sessions = {
        f"{prefix}-normal":  simulate_normal,
        f"{prefix}-loop":    simulate_loop,
        f"{prefix}-drift":   simulate_drift,
        f"{prefix}-failure": simulate_failure,
    }
    threads = []
    for sid, fn in sessions.items():
        t = threading.Thread(target=fn, args=(sid,))
        threads.append(t)
        t.start()
        time.sleep(0.4)  # stagger starts to interleave events
    for t in threads:
        t.join()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sploink Agent Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "loop", "drift", "failure", "mixed"],
        required=True,
    )
    parser.add_argument("--session", default=None, help="Session ID (auto-generated if omitted)")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.url

    session_id = args.session or f"{args.scenario}-{uuid.uuid4().hex[:8]}"

    print(f"🚀 Sploink Agent Simulator")
    print(f"   Backend  : {BASE_URL}")
    print(f"   Scenario : {args.scenario}")
    print(f"   Session  : {session_id}")

    dispatch = {
        "normal":  simulate_normal,
        "loop":    simulate_loop,
        "drift":   simulate_drift,
        "failure": simulate_failure,
        "mixed":   lambda s: simulate_mixed(s),
    }
    dispatch[args.scenario](session_id)

    frontend = BASE_URL.replace("8000", "3000")
    if args.scenario != "mixed":
        print(f"\n✅ Done → {frontend}/sessions/{session_id}")
    else:
        print(f"\n✅ Done → {frontend}/")


if __name__ == "__main__":
    main()
