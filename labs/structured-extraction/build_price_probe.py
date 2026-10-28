"""Development-only semantic price-period probe, authored after baseline audit.

Never a fresh blind test; some phrasings exceed the organizer's generation grammar.
The gold records linguistic content, not knowledge of the actual subscription price.
"""
import argparse
import json
import pathlib


PHRASES = [
    "The monthly subscription fee for Hooly AI Pro is EUR {n}.",
    "Hooly AI Pro is billed monthly at EUR {n}.",
    "Hooly AI Pro costs EUR {n} per active user per month.",
    "Hooly AI Pro costs EUR {n} per seat per month.",
    "Hooly AI Pro costs EUR {n} per calendar month.",
    "Hooly AI Pro is offered at a monthly rate of EUR {n}.",
    "The monthly cost of Hooly AI Pro amounts to EUR {n}.",
    "Hooly AI Pro costs EUR {n} / month.",
    "Hooly AI Pro costs \u20ac{n}/month.",
    "Hooly AI Pro costs EUR {n} every month.",
    "For one month of Hooly AI Pro, the charge is EUR {n}.",
    "EUR {n} is the monthly fee for Hooly AI Pro.",
    "The Hooly AI Pro subscription is EUR {n} a month.",
    "Hooly AI Pro costs EUR {n} per user per month.",
    "A monthly payment of EUR {n} buys access to Hooly AI Pro.",
    "Hooly AI Pro is priced at EUR {n} for each month of use.",
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    path = pathlib.Path(args.out)
    if path.exists():
        raise ValueError("Use a fresh fixture path")
    rows = []
    for i, phrase in enumerate(PHRASES):
        n = 43 + i * 3
        rows.append({"id": f"dev-period-{i:02d}", "split": "dev", "category": "monthly_period_semantics",
                     "text": phrase.format(n=n), "previous_text": "", "form": [{"subject": "Hooly AI Pro", "attribute": "price", "value": {"kind": "money", "value": n, "currency": "EUR", "per": "month"}}],
                     "provenance": "Codex-authored development diagnostic after inspecting dev parser failures; not blind or organizer-validity guarantee"})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


if __name__ == "__main__":
    main()
