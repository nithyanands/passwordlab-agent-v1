import time
from typing import TypedDict, Literal
import requests
from langgraph.graph import StateGraph, END

from .config import (
    LAB_BASE_URL, HEALTH_URL, ACCOUNTS_URL, LOGIN_URL,
    DEFAULT_MAX_ATTEMPTS, REQUEST_TIMEOUT_SECONDS, MAX_RUN_SECONDS
)
from .safety import validate_target, validate_attempt_limit, SafetyError
from .generators import dictionary_candidates, bounded_bruteforce_candidates
from .storage import save_experiment

class LabState(TypedDict, total=False):
    mode: Literal["dictionary", "brute_force"]
    target: str
    max_attempts: int
    confirmed: bool
    accounts: list[str]
    attempts: int
    successes: int
    elapsed: float
    status: str
    error: str
    report: str

def validate_scope(state: LabState) -> LabState:
    try:
        validate_target(state.get("target", LAB_BASE_URL))
        validate_attempt_limit(state.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
        if not state.get("confirmed", False):
            raise SafetyError("Explicit execution confirmation is required.")
        if state.get("mode") not in {"dictionary", "brute_force"}:
            raise SafetyError("Unknown simulation mode.")
        response = requests.get(HEALTH_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        if response.json().get("environment") != "synthetic-local-lab":
            raise SafetyError("Service did not identify itself as the synthetic lab.")
        return {**state, "status": "validated"}
    except Exception as exc:
        return {**state, "status": "rejected", "error": str(exc)}

def load_accounts(state: LabState) -> LabState:
    if state.get("status") != "validated":
        return state
    try:
        response = requests.get(ACCOUNTS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        accounts = response.json()["accounts"]
        if not accounts or any(not isinstance(a, str) for a in accounts):
            raise SafetyError("No valid synthetic accounts returned.")
        return {**state, "accounts": accounts, "status": "accounts_loaded"}
    except Exception as exc:
        return {**state, "status": "rejected", "error": str(exc)}

def plan_attack(state: LabState) -> LabState:
    if state.get("status") != "accounts_loaded":
        return state
    return {**state, "status": "planned"}

def execute_simulation(state: LabState) -> LabState:
    if state.get("status") != "planned":
        return state

    started = time.monotonic()
    attempts = successes = 0
    mode = state["mode"]
    limit = state["max_attempts"]

    try:
        validate_target(state["target"])
        for username in state["accounts"]:
            candidates = (dictionary_candidates() if mode == "dictionary"
                          else bounded_bruteforce_candidates())
            for candidate in candidates:
                if attempts >= limit:
                    break
                if time.monotonic() - started > MAX_RUN_SECONDS:
                    raise SafetyError("Maximum experiment runtime reached.")
                response = requests.post(
                    LOGIN_URL,
                    json={"username": username, "password": candidate},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                attempts += 1
                if response.json().get("authenticated") is True:
                    successes += 1
                    print(f"[CRACKED] username={username} password={candidate} at attempt {attempts}", flush=True)
            if attempts >= limit:
                break

        elapsed = time.monotonic() - started
        save_experiment(mode, attempts, successes, elapsed, "completed")
        return {**state, "attempts": attempts, "successes": successes,
                "elapsed": elapsed, "status": "completed"}
    except Exception as exc:
        elapsed = time.monotonic() - started
        save_experiment(mode, attempts, successes, elapsed, "stopped")
        return {**state, "attempts": attempts, "successes": successes,
                "elapsed": elapsed, "status": "stopped", "error": str(exc)}

def analyse_results(state: LabState) -> LabState:
    if state.get("status") not in {"completed", "stopped"}:
        return state
    attempts = state.get("attempts", 0)
    successes = state.get("successes", 0)
    rate = successes / attempts * 100 if attempts else 0.0
    advice = [
        "Use long, unique passwords and a password manager.",
        "Enable multi-factor authentication.",
        "Apply server-side rate limiting and progressive delays.",
        "Monitor failed authentication patterns and alert on anomalies.",
        "Use a modern password-hashing scheme with unique salts.",
    ]
    report = (
        f"Mode: {state.get('mode')} | Status: {state.get('status')}\\n"
        f"Attempts: {attempts} | Successful authentications: {successes}\\n"
        f"Observed success rate: {rate:.2f}% | Elapsed: {state.get('elapsed', 0):.3f}s\\n"
        "Defensive recommendations:\\n- " + "\\n- ".join(advice)
    )
    return {**state, "report": report}

def route_after_validation(state: LabState):
    return "load_accounts" if state.get("status") == "validated" else "analyse_results"

def route_after_accounts(state: LabState):
    return "plan_attack" if state.get("status") == "accounts_loaded" else "analyse_results"

def build_graph():
    graph = StateGraph(LabState)
    graph.add_node("validate_scope", validate_scope)
    graph.add_node("load_accounts", load_accounts)
    graph.add_node("plan_attack", plan_attack)
    graph.add_node("execute_simulation", execute_simulation)
    graph.add_node("analyse_results", analyse_results)
    graph.set_entry_point("validate_scope")
    graph.add_conditional_edges("validate_scope", route_after_validation,
        {"load_accounts": "load_accounts", "analyse_results": "analyse_results"})
    graph.add_conditional_edges("load_accounts", route_after_accounts,
        {"plan_attack": "plan_attack", "analyse_results": "analyse_results"})
    graph.add_edge("plan_attack", "execute_simulation")
    graph.add_edge("execute_simulation", "analyse_results")
    graph.add_edge("analyse_results", END)
    return graph.compile()

