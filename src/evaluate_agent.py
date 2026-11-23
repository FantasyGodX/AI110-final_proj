"""Reliability evaluation for the retrieval + agent pipeline.

    python -m src.evaluate_agent                 # print the report
    python -m src.evaluate_agent --write assets/evaluation_results.md

Four experiments, all deterministic:

1. Retrieval accuracy   - does the right knowledge-base document come back?
2. Paraphrase stability - do different wordings of one request give similar lists?
3. Agent behaviour      - how often did the checks pass, trigger a revision, or fail?
4. Guardrails           - does bad input get handled instead of crashing?

The queries and the "right document" labels were written by me. Retrieval labels
are my judgment of which document a reasonable reader would expect.
"""

import argparse
import io
import logging
from contextlib import redirect_stdout
from statistics import mean

from src.agent import load_system, run_agent
from src.log_setup import get_logger

# (query, set of acceptable top documents)
RETRIEVAL_CASES = [
    ("I need to cram for my chemistry exam", {"scenario:study"}),
    ("lifting weights at the gym", {"scenario:workout"}),
    ("driving across the country with my friends", {"scenario:roadtrip"}),
    ("gloomy weather and a cup of tea", {"scenario:rainy_day"}),
    ("candlelit dinner for our anniversary", {"scenario:date_night"}),
    ("birthday party with all my friends", {"scenario:party"}),
    ("I can't sleep tonight", {"scenario:sleep"}),
    ("making brunch on a lazy sunday", {"scenario:cooking"}),
    ("my girlfriend dumped me and I'm heartbroken", {"scenario:heartbreak", "mood:sad"}),
    ("songs that remind me of my childhood", {"scenario:throwback", "mood:nostalgic"}),
    ("relaxing by the pool on vacation", {"scenario:beach"}),
    ("guided yoga and breathing", {"scenario:meditation"}),
    ("writing code all afternoon", {"scenario:work_focus"}),
    ("something with a lot of rage", {"mood:angry"}),
    ("give me some jazz", {"genre:jazz"}),
    ("classical piano", {"genre:classical"}),
    ("i love reggae", {"genre:reggae"}),
    ("rap with heavy bass", {"genre:hip hop"}),
    ("sunshine and ocean waves", {"scenario:beach"}),
    ("taking the train to work", {"scenario:commute"}),
]

# Requests that contradict themselves. The agent should flag them (status needs_review).
CONFLICT_CASES = [
    "calm and peaceful but also super high energy workout",
    "slow sad party music for heartbreak and dancing",
    "very loud aggressive sad blues",
    "gym workout and also sleep",
]

PARAPHRASE_GROUPS = {
    "study": ["music to study to", "background music for homework",
              "I need to concentrate on reading for my exam"],
    "workout": ["gym workout music", "songs for running and lifting",
                "pump me up for training"],
    "sleep": ["help me sleep", "music for bedtime", "I have insomnia and need to rest"],
    "party": ["party with friends", "music for dancing at a club", "birthday celebration"],
}

# (label, input, what counts as a pass, set of acceptable statuses)
GUARDRAIL_CASES = [
    ("empty string", "", "rejected, no crash", {"rejected"}),
    ("whitespace only", "    ", "rejected, no crash", {"rejected"}),
    ("None instead of text", None, "rejected, no crash", {"rejected"}),
    ("number instead of text", 12345, "rejected, no crash", {"rejected"}),
    ("oversized input (400 chars)", "study " * 70, "rejected, no crash", {"rejected"}),
    ("random letters", "asdfgh qwerty zxcv", "asks for clarification, does not guess", {"needs_clarification"}),
    ("single character", "k", "asks for clarification, does not guess", {"needs_clarification"}),
    ("emoji only", "\U0001F3B5\U0001F3B5", "asks for clarification, does not guess", {"needs_clarification"}),
    ("non-English request", "música para estudiar", "asks for clarification, does not guess", {"needs_clarification"}),
    ("SQL-style text", "'; DROP TABLE songs; --", "handled safely, no crash", {"ok", "needs_review", "needs_clarification"}),
    ("invalid k (0)", ("study music", 0), "rejected, no crash", {"rejected"}),
    ("invalid k (100)", ("study music", 100), "rejected, no crash", {"rejected"}),
]


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 1.0


def run_all():
    songs, docs, retriever = load_system()
    out = {}

    # 1. retrieval
    rows, h1, h3 = [], 0, 0
    for query, expected in RETRIEVAL_CASES:
        hits = [d["id"] for d, _ in retriever.search(query, 3)]
        top1 = bool(hits) and hits[0] in expected
        top3 = any(h in expected for h in hits)
        h1 += top1
        h3 += top3
        rows.append((query, sorted(expected), hits, top1, top3))
    out["retrieval"] = {"rows": rows, "hit1": h1 / len(rows), "hit3": h3 / len(rows)}

    # 2. paraphrase stability
    groups = {}
    for name, queries in PARAPHRASE_GROUPS.items():
        results = [run_agent(q, songs, retriever) for q in queries]
        sets = [{s["title"] for s, _, _ in r.recs} for r in results]
        pairs = [(i, j) for i in range(len(sets)) for j in range(i + 1, len(sets))]
        top_docs = [r.citations[0]["id"] if r.citations else None for r in results]
        groups[name] = {
            "jaccard": mean(jaccard(sets[i], sets[j]) for i, j in pairs),
            "same_top_doc": len(set(top_docs)) == 1,
            "top1_songs": [r.recs[0][0]["title"] if r.recs else None for r in results],
        }
    out["paraphrase"] = groups

    # 3. agent behaviour over the retrieval queries
    results = [run_agent(q, songs, retriever) for q, _ in RETRIEVAL_CASES]
    revised = [r for r in results if sum(s.name.startswith("attempt") for s in r.trace) > 1]
    recovered = [r for r in revised if r.status == "ok"]
    out["agent"] = {
        "n": len(results),
        "ok": sum(r.status == "ok" for r in results),
        "needs_review": sum(r.status == "needs_review" for r in results),
        "clarification": sum(r.status == "needs_clarification" for r in results),
        "revised": len(revised), "recovered": len(recovered),
        "mean_ratio": mean(r.ratio for r in results if r.recs),
        "confidence": {lab: sum(r.confidence == lab for r in results) for lab in ("high", "medium", "low")},
    }

    reasons = {}
    for r_ in results:
        for step in r_.trace:
            if step.name == "attempt 1" and "failed:" in step.detail:
                for reason in step.detail.split("failed: ")[1].split(", "):
                    reasons[reason] = reasons.get(reason, 0) + 1
    out["agent"]["first_attempt_failures"] = reasons
    out["false_flags"] = [q for (q, _), r_ in zip(RETRIEVAL_CASES, results) if r_.status != "ok"]
    out["conflicts"] = [(q, run_agent(q, songs, retriever).status) for q in CONFLICT_CASES]

    # determinism
    first = run_agent("music to study to", songs, retriever)
    repeats = [run_agent("music to study to", songs, retriever) for _ in range(4)]
    out["deterministic"] = all(
        [s["id"] for s, _, _ in r.recs] == [s["id"] for s, _, _ in first.recs] for r in repeats)

    # 4. guardrails
    g_rows = []
    for label, value, criterion, accepted in GUARDRAIL_CASES:
        try:
            if isinstance(value, tuple):
                res = run_agent(value[0], songs, retriever, k=value[1])
            else:
                res = run_agent(value, songs, retriever)
            status, ok = res.status, res.status in accepted
        except Exception as err:  # a crash is a failure of the guardrail
            status, ok = f"CRASH: {type(err).__name__}", False
        shown = repr(value if not isinstance(value, (str, tuple)) or len(str(value)) < 40 else str(value)[:37] + "...")
        g_rows.append((label, shown, criterion, status, ok))
    out["guardrails"] = g_rows
    return out


def render(out) -> str:
    r, a = out["retrieval"], out["agent"]
    lines = ["# Evaluation results", "",
             "Generated by `python -m src.evaluate_agent`. Queries and labels are mine.", "",
             "## 1. Retrieval accuracy", "",
             f"Top-1 hit rate: **{r['hit1']:.0%}** ({round(r['hit1'] * len(r['rows']))}/{len(r['rows'])}). "
             f"Top-3 hit rate: **{r['hit3']:.0%}** ({round(r['hit3'] * len(r['rows']))}/{len(r['rows'])}).", "",
             "| Query | Expected | Retrieved (top 3) | Top-1 | Top-3 |", "|---|---|---|---|---|"]
    for q, exp, hits, t1, t3 in r["rows"]:
        lines.append(f"| {q} | {', '.join(exp)} | {', '.join(hits) or '(none)'} | "
                     f"{'Pass' if t1 else 'Fail'} | {'Pass' if t3 else 'Fail'} |")
    lines += ["", "## 2. Paraphrase stability", "",
              "Three wordings of one request should give similar lists. Jaccard is the overlap of the top-5 titles (1.00 = identical).", "",
              "| Request | Mean Jaccard | Same top document | Top song per wording |", "|---|---|---|---|"]
    for name, g in out["paraphrase"].items():
        lines.append(f"| {name} | {g['jaccard']:.2f} | {'Yes' if g['same_top_doc'] else 'No'} | {', '.join(map(str, g['top1_songs']))} |")
    mean_j = mean(g["jaccard"] for g in out["paraphrase"].values())
    lines += ["", f"Average Jaccard across groups: **{mean_j:.2f}**. "
              f"Repeating one query 5 times gave identical lists: **{'Yes' if out['deterministic'] else 'No'}**.", "",
              "## 3. Agent behaviour", "",
              f"Over the {a['n']} retrieval queries: {a['ok']} finished `ok`, {a['needs_review']} `needs_review`, "
              f"{a['clarification']} asked for clarification. "
              f"The agent revised its first attempt in **{a['revised']}** runs and recovered (all checks passed) in **{a['recovered']}** of them. "
              f"Mean confidence ratio {a['mean_ratio']:.2f}; labels: {a['confidence']['high']} high, "
              f"{a['confidence']['medium']} medium, {a['confidence']['low']} low.", "",
              f"First-attempt failures by check: {a['first_attempt_failures'] or 'none'}.", "",
              f"Normal queries flagged `needs_review` (false alarms): "
              f"**{len(out['false_flags'])}/{a['n']}** {out['false_flags'] or ''}", "",
              "Contradictory requests (should be flagged `needs_review`):", "",
              "| Query | Status | Result |", "|---|---|---|"] + [
              f"| {q} | {st} | {'Pass' if st == 'needs_review' else 'Fail'} |" for q, st in out["conflicts"]] + ["",
              "## 4. Guardrails", "",
              "| Test input | Evaluation criterion | Status returned | Result |", "|---|---|---|---|"]
    for label, shown, criterion, status, ok in out["guardrails"]:
        lines.append(f"| {label}: {shown} | {criterion} | {status} | {'Pass' if ok else 'Fail'} |")
    passed = sum(row[4] for row in out["guardrails"])
    lines += ["", f"Guardrails passed: **{passed}/{len(out['guardrails'])}**.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate retrieval, agent and guardrails")
    parser.add_argument("--write", help="also save the report to this markdown file")
    args = parser.parse_args(argv)
    # keep console clean: warnings from guardrail tests are expected here
    get_logger().handlers[0].setLevel(logging.CRITICAL)
    report = render(run_all())
    print(report)
    if args.write:
        with open(args.write, "w", encoding="utf-8") as f:
            f.write(report)


if __name__ == "__main__":
    main()
