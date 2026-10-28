import unittest

from grammar import Grammar
from grammar_robust import RobustGrammar


class PeriodNormalizationTests(unittest.TestCase):
    def setUp(self):
        lex = {"subjects": [{"name": "Hooly AI Pro", "aliases": [], "attributes": ["price"]}]}
        self.base, self.robust = Grammar(lex), RobustGrammar(lex)

    def money(self, text):
        return [x["value"] for x in self.robust.candidates(text) if x["value"]["kind"] == "money"]

    def test_leading_monthly_charge(self):
        self.assertEqual(self.money("The monthly charge for Hooly AI Pro is EUR 79.")[0]["per"], "month")

    def test_false_stated_amount_is_preserved(self):
        self.assertEqual(self.money("Hooly AI Pro is billed monthly at EUR 987.")[0]["value"], 987)

    def test_per_active_user(self):
        self.assertEqual(self.money("Hooly AI Pro costs EUR 79 per active user per month.")[0]["per"], "month")

    def test_calendar_period(self):
        self.assertEqual(self.money("Hooly AI Pro costs EUR 79 per calendar month.")[0]["per"], "month")

    def test_amount_first(self):
        self.assertEqual(self.money("EUR 79 is the monthly fee for Hooly AI Pro.")[0]["per"], "month")

    def test_month_costs(self):
        self.assertEqual(self.money("For Hooly AI Pro, a month costs EUR 79.")[0]["per"], "month")

    def test_monthly_report_one_off_fee(self):
        value = self.money("The monthly report says the one-off fee for Hooly AI Pro is EUR 79.")[0]
        self.assertNotIn("per", value)

    def test_monthly_report_is_not_a_price_modifier(self):
        value = self.money("The monthly report gives Hooly AI Pro a price of EUR 79.")[0]
        self.assertNotIn("per", value)

    def test_two_clauses_keep_separate_periods(self):
        values = self.money("The monthly fee is EUR 79; the annual fee is EUR 790.")
        self.assertEqual([v["per"] for v in values], ["month", "year"])

    def test_setup_fee_after_comma(self):
        values = self.money("The monthly fee is EUR 79, the setup fee is EUR 20.")
        self.assertEqual(values[0]["per"], "month")
        self.assertNotIn("per", values[1])

    def test_ambiguous_multiple_money_amounts(self):
        values = self.money("The monthly fee for the EUR 79 plan may become EUR 89.")
        self.assertTrue(all("per" not in v for v in values))

    def test_explicit_period_wins(self):
        value = self.money("The monthly report says Hooly AI Pro costs EUR 790 per year.")[0]
        self.assertEqual(value["per"], "year")

    def test_candidate_spans_and_kinds_are_unchanged(self):
        text = "The monthly price is EUR 79 and the trial lasts 14 days."
        strip = lambda cs: [(c["start"], c["end"], c["value"]["kind"]) for c in cs]
        self.assertEqual(strip(self.base.candidates(text)), strip(self.robust.candidates(text)))


if __name__ == "__main__":
    unittest.main()
