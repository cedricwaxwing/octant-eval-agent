import json
from dataclasses import dataclass
from typing import List

from agent import answer_question, load_dataset


@dataclass
class EvalCase:
    id: str
    question: str
    expected_contains: List[str]


CASES: List[EvalCase] = [
    EvalCase(
        id="epoch_4_top_rewards",
        question="Which projects received the highest matched rewards in epoch 4?",
        expected_contains=["epoch 4"],
    ),
    EvalCase(
        id="epoch_5_donors_patrons",
        question="How many donors and patrons participated in epoch 5?",
        expected_contains=["epoch 5", "donors", "patrons"],
    ),
    EvalCase(
        id="giveth_rewards_over_time",
        question="How did rewards for Giveth change across epochs?",
        expected_contains=["giveth"],
    ),
    EvalCase(
        id="unused_rewards_epoch_3",
        question="How much unused reward was left in epoch 3?",
        expected_contains=["epoch 3"],
    ),
]


def run_eval() -> None:
    dataset = load_dataset()
    results = []

    for case in CASES:
        print(f"=== {case.id} ===")
        print(f"Question: {case.question}")
        answer = answer_question(case.question, dataset)
        print("Answer:")
        print(answer)
        print()

        normalized_answer = answer.lower()
        expected_hits = [
            token for token in case.expected_contains if token.lower() in normalized_answer
        ]
        passed = len(expected_hits) == len(case.expected_contains)

        results.append({"id": case.id, "passed": passed, "hits": expected_hits})
        print(f"Expected tokens: {case.expected_contains}")
        print(f"Matched tokens:  {expected_hits}")
        print(f"Result: {'PASS' if passed else 'FAIL'}")
        print()

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    print("=== Summary ===")
    print(json.dumps(results, indent=2))
    print(f"Score: {passed}/{total} tests passed")


if __name__ == "__main__":
    run_eval()

