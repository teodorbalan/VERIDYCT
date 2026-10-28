"""Conservative text-only billing-period normalization over existing candidates.

No new spans, candidate types, facts or subject/attribute predictions are added.
Explicit period parsing wins. Inference uses the local monetary clause only.
"""
import re

from grammar import Grammar


PERIODS = {"monthly": "month", "annually": "year", "annual": "year", "yearly": "year",
           "weekly": "week", "daily": "day"}
MONEY_NOUN = r"(?:subscription\s+)?(?:charge|fee|price|cost|payment|rate)"
MODIFIER = r"(?:monthly|annual|yearly|weekly|daily)"
BOUNDARY = re.compile(r"[;!?]|[.](?!\d)(?=\s|$)|,(?!\d)|\b(?:and|but|whereas)\b", re.I)
ONE_OFF = re.compile(r"\b(?:one[ -]off|one[ -]time|setup|set-up|activation|purchase)\s+(?:fee|charge|payment|cost|price)\b", re.I)


def clause_bounds(text, start, end):
    left, right = 0, len(text)
    for m in BOUNDARY.finditer(text):
        if m.end() <= start:
            left = m.end()
        elif m.start() >= end:
            right = m.start()
            break
    return left, right


def implied_period(text, candidate, money_candidates):
    if candidate["value"].get("per"):
        return None
    start, end = candidate["start"], candidate["end"]
    left, right = clause_bounds(text, start, end)
    before, after = text[left:start], text[end:right]
    scope = text[left:right]
    if ONE_OFF.search(scope):
        return None
    # Local continuation of this amount, allowing common billing qualifiers.
    suffix = re.match(
        r"\s*(?:(?:per\s+(?:(?:active|licensed|registered)\s+)?(?:user|seat|account))\s+)?"
        r"(?:per|each|every|for\s+each|a)\s+(?:calendar\s+)?(month|year|week|day)\b", after, re.I)
    if suffix:
        return suffix.group(1).casefold()
    # With two amounts in one scope, a leading adjective cannot be safely
    # attached to either amount. Explicit adjacent periods above still work.
    local = [c for c in money_candidates if c["start"] >= left and c["end"] <= right]
    if len(local) != 1:
        return None
    # "monthly report" is deliberately not a money-period cue.
    direct = re.search(rf"\b({MODIFIER})\s+{MONEY_NOUN}\b", before, re.I)
    if direct:
        return PERIODS[direct.group(1).casefold()]
    billed = re.search(r"\b(?:billed|charged|paid|payable)\s+(monthly|annually|yearly|weekly|daily)\b", before, re.I)
    if billed:
        return PERIODS[billed.group(1).casefold()]
    # "a month costs EUR 49" or "for one month ... the charge is EUR 49".
    duration = re.search(r"\b(?:a|one)\s+(?:calendar\s+)?(month|year|week|day)\b", before, re.I)
    if duration and re.search(r"\b(?:costs?|charge|fee|price|payment)\b", before[duration.end():], re.I):
        return duration.group(1).casefold()
    # Amount-first formulations, e.g. "EUR 49 is the monthly fee".
    following = re.match(rf"\s+(?:is|was)\s+(?:the|a)\s+({MODIFIER})\s+{MONEY_NOUN}\b", after, re.I)
    if following:
        return PERIODS[following.group(1).casefold()]
    return None


class RobustGrammar(Grammar):
    def candidates(self, text):
        result = super().candidates(text)
        monies = [c for c in result if c["value"]["kind"] == "money"]
        for c in monies:
            period = implied_period(text, c, monies)
            if period:
                c["value"] = dict(c["value"], per=period)
        return result
