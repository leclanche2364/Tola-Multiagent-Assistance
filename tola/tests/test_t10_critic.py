# Batch T10 - Critic Tests
# unittest tests covering QA T10 cases T10-01..T10-08
# Fixture-driven, deterministic, plain ASCII.

from __future__ import annotations

import unittest

from tola.critic.critic import (
    CriticVerdict,
    Verdict,
    Finding,
    RequiredChange,
    critique_plan,
    FC_MISSING_SUCCESS_METRIC,
    FC_MISSING_DEPENDENCY,
    FC_MISSING_DEPENDENCY_IMPLIED,
    FC_UNSUPPORTED_ASSUMPTION,
    FC_OVERCOMPLICATION,
    FC_BOUNDARY_VIOLATION,
    FC_ROUTINE_BYPASS,
    FC_EXTERNAL_COMMITMENT,
    FC_BUDGET_IMPACT,
    SEV_ERROR,
    SEV_WARNING,
    SEV_INFO,
)
from tola.critic.review_classes import (
    ReviewClass,
    PlanInput,
)


# ===========================================================================
# Fixtures
# ===========================================================================

def _strong_plan() -> PlanInput:
    """T10-01: Strong plan with success metric, dependencies, no issues."""
    return PlanInput(
        title="Update daily brief template",
        domain="scheduling",
        steps=[
            "Review current template",
            "Update section headers",
            "Add summary field",
        ],
        artifacts=["template_v2.md"],
        success_criteria=["Template renders without errors"],
        dependencies=["current template exists"],
        assumptions=["Users have markdown editor access"],
        impact_area="scheduling",
    )


def _missing_metric_plan() -> PlanInput:
    """T10-02: Plan with no success metric -> REVISE."""
    return PlanInput(
        title="Refresh dashboard data",
        domain="scheduling",
        steps=["Pull latest data", "Rebuild cache"],
        artifacts=[],
        success_criteria=[],
        dependencies=[],
        assumptions=[],
        impact_area="scheduling",
    )


def _missing_dependency_plan() -> PlanInput:
    """T10-03: Plan with implied dependency not listed -> REVISE."""
    return PlanInput(
        title="Deploy after migration",
        domain="product",
        steps=[
            "Run migration script",
            "Deploy after migration completes",
        ],
        artifacts=["migration.sql"],
        success_criteria=["Schema version bumped"],
        dependencies=[],
        assumptions=[],
        impact_area="product",
    )


def _unsupported_assumption_plan() -> PlanInput:
    """T10-04: Plan with unsupported assumption -> flagged."""
    return PlanInput(
        title="Expand to new market",
        domain="growth",
        steps=["Research market", "Build outreach list", "Send campaigns"],
        artifacts=["research.pdf", "outreach.csv", "campaigns.yaml"],
        success_criteria=["100 leads generated"],
        dependencies=["market research complete"],
        assumptions=[
            "Market size is large enough",
            "No competitor response",
            "Budget is available",
            "Legal clearance is granted",
            "Partners are ready",
        ],
        impact_area="growth",
    )


def _overcomplicated_plan() -> PlanInput:
    """T10-05: Plan with too many steps/artifacts -> APPROVE_WITH_CHANGES."""
    return PlanInput(
        title="Full product launch",
        domain="product",
        steps=[
            "Step 1", "Step 2", "Step 3", "Step 4", "Step 5",
            "Step 6", "Step 7", "Step 8", "Step 9", "Step 10",
            "Step 11", "Step 12",
        ],
        artifacts=["a", "b", "c", "d", "e", "f"],
        success_criteria=["Launch complete"],
        dependencies=["all steps done"],
        assumptions=[],
        impact_area="product",
    )


def _routine_plan() -> PlanInput:
    """T10-06: Routine plan that bypasses full review."""
    return PlanInput(
        title="status_report",
        domain="scheduling",
        steps=["Generate report"],
        artifacts=[],
        success_criteria=["Report sent"],
        dependencies=[],
        assumptions=[],
        impact_area="scheduling",
    )


def _consequential_plan() -> PlanInput:
    """T10-07: Consequential plan that follows full approval path."""
    return PlanInput(
        title="Quarterly budget reallocation",
        domain="growth",
        steps=["Analyze spend", "Propose reallocation", "Get stakeholder signoff"],
        artifacts=["budget_proposal.xlsx"],
        success_criteria=["Stakeholder approval obtained"],
        dependencies=["current budget data"],
        assumptions=["No budget cuts from above"],
        impact_area="growth",
        affects_budget=True,
    )


def _style_only_plan() -> PlanInput:
    """T10-08: Strong plan where Tola should not rewrite for style."""
    return PlanInput(
        title="Optimize weekly digest",
        domain="scheduling",
        steps=[
            "Aggregate data from sources",
            "Format sections consistently",
            "Add executive summary",
            "Review for clarity",
            "Send to stakeholders",
        ],
        artifacts=["digest_v3.md"],
        success_criteria=["Digest delivered within 2 hours of cutoff"],
        dependencies=["data sources available"],
        assumptions=["Stakeholders read email"],
        impact_area="scheduling",
    )


# ===========================================================================
# T10-01: Strong plan approved without needless rewriting
# ===========================================================================

class TestT10_01_StrongPlanApproved(unittest.TestCase):
    def test_strong_plan_approved(self):
        result = critique_plan(_strong_plan())
        self.assertEqual(result.verdict, Verdict.APPROVE)
        self.assertEqual(len(result.required_changes), 0)

    def test_strong_plan_no_style_findings(self):
        result = critique_plan(_strong_plan())
        for f in result.findings:
            self.assertNotIn("style", f.message.lower())


# ===========================================================================
# T10-02: Missing success metric triggers revision
# ===========================================================================

class TestT10_02_MissingSuccessMetric(unittest.TestCase):
    def test_missing_metric_revised(self):
        result = critique_plan(_missing_metric_plan())
        self.assertEqual(result.verdict, Verdict.REVISE)

    def test_missing_metric_finding_present(self):
        result = critique_plan(_missing_metric_plan())
        codes = [f.code for f in result.findings]
        self.assertIn(FC_MISSING_SUCCESS_METRIC, codes)

    def test_missing_metric_required_change_present(self):
        result = critique_plan(_missing_metric_plan())
        self.assertTrue(
            any(rc.code == FC_MISSING_SUCCESS_METRIC for rc in result.required_changes)
        )


# ===========================================================================
# T10-03: Missing dependency detected
# ===========================================================================

class TestT10_03_MissingDependency(unittest.TestCase):
    def test_missing_dependency_revised(self):
        result = critique_plan(_missing_dependency_plan())
        self.assertEqual(result.verdict, Verdict.REVISE)

    def test_missing_dependency_finding_present(self):
        result = critique_plan(_missing_dependency_plan())
        codes = [f.code for f in result.findings]
        self.assertIn(FC_MISSING_DEPENDENCY_IMPLIED, codes)


# ===========================================================================
# T10-04: Unsupported assumption flagged
# ===========================================================================

class TestT10_04_UnsupportedAssumption(unittest.TestCase):
    def test_unsupported_assumption_flagged(self):
        result = critique_plan(_unsupported_assumption_plan())
        codes = [f.code for f in result.findings]
        self.assertIn(FC_UNSUPPORTED_ASSUMPTION, codes)

    def test_unsupported_assumption_has_required_change(self):
        result = critique_plan(_unsupported_assumption_plan())
        self.assertTrue(
            any(rc.code == FC_UNSUPPORTED_ASSUMPTION for rc in result.required_changes)
        )


# ===========================================================================
# T10-05: Overcomplicated plan simplified
# ===========================================================================

class TestT10_05_OvercomplicatedPlan(unittest.TestCase):
    def test_overcomplicated_approve_with_changes(self):
        result = critique_plan(_overcomplicated_plan())
        self.assertEqual(result.verdict, Verdict.APPROVE_WITH_CHANGES)

    def test_overcomplicated_has_trim_suggestions(self):
        result = critique_plan(_overcomplicated_plan())
        self.assertTrue(
            any("Reduce" in f.message for f in result.findings)
        )


# ===========================================================================
# T10-06: Routine task bypasses full Tola review
# ===========================================================================

class TestT10_06_RoutineBypass(unittest.TestCase):
    def test_routine_bypass_approved(self):
        result = critique_plan(_routine_plan())
        self.assertEqual(result.verdict, Verdict.APPROVE)

    def test_routine_bypass_review_class(self):
        result = critique_plan(_routine_plan())
        self.assertEqual(result.review_class, ReviewClass.ROUTINE)

    def test_routine_bypass_has_bypass_finding(self):
        result = critique_plan(_routine_plan())
        codes = [f.code for f in result.findings]
        self.assertIn(FC_ROUTINE_BYPASS, codes)


# ===========================================================================
# T10-07: Consequential plan follows approval path
# ===========================================================================

class TestT10_07_ConsequentialPath(unittest.TestCase):
    def test_consequential_uses_full_path(self):
        result = critique_plan(_consequential_plan())
        # Budget impact -> NEEDS_USER_DECISION
        self.assertEqual(result.verdict, Verdict.NEEDS_USER_DECISION)

    def test_consequential_budget_finding(self):
        result = critique_plan(_consequential_plan())
        codes = [f.code for f in result.findings]
        self.assertIn(FC_BUDGET_IMPACT, codes)


# ===========================================================================
# T10-08: Tola preserves good specialist reasoning, no style rewrites
# ===========================================================================

class TestT10_08_NoStyleRewrite(unittest.TestCase):
    def test_strong_plan_not_rewritten(self):
        result = critique_plan(_style_only_plan())
        self.assertEqual(result.verdict, Verdict.APPROVE)

    def test_no_style_only_findings(self):
        result = critique_plan(_style_only_plan())
        for f in result.findings:
            self.assertNotIn("style", f.message.lower())
            self.assertNotIn("rewrite", f.message.lower())
            self.assertNotIn("cosmetic", f.message.lower())
            self.assertNotIn("formatting", f.message.lower())

    def test_reasoning_preserved(self):
        result = critique_plan(_style_only_plan())
        # Strong plan should have zero or only INFO findings
        for f in result.findings:
            self.assertIn(f.severity, (SEV_INFO, SEV_WARNING))


# ===========================================================================
# Additional: boundary violation -> REJECT
# ===========================================================================

class TestT10_BoundaryViolation(unittest.TestCase):
    def test_boundary_violation_rejected(self):
        plan = PlanInput(
            title="Growth direct schedule write",
            domain="growth",
            steps=["Perform direct_schedule_write to rhythm"],
            artifacts=[],
            success_criteria=["Schedule updated"],
            dependencies=[],
            assumptions=[],
            impact_area="scheduling",
        )
        result = critique_plan(plan)
        self.assertEqual(result.verdict, Verdict.REJECT)
        codes = [f.code for f in result.findings]
        self.assertIn(FC_BOUNDARY_VIOLATION, codes)


# ===========================================================================
# Additional: NEEDS_USER_DECISION for external commitment
# ===========================================================================

class TestT10_ExternalCommitment(unittest.TestCase):
    def test_external_commitment_needs_user_decision(self):
        plan = PlanInput(
            title="Sign vendor contract",
            domain="product",
            steps=["Review terms", "Negotiate", "Sign"],
            artifacts=["contract_draft.pdf"],
            success_criteria=["Contract signed"],
            dependencies=["legal review"],
            assumptions=[],
            impact_area="product",
            requires_external_commit=True,
        )
        result = critique_plan(plan)
        self.assertEqual(result.verdict, Verdict.NEEDS_USER_DECISION)
        codes = [f.code for f in result.findings]
        self.assertIn(FC_EXTERNAL_COMMITMENT, codes)


# ===========================================================================
# Additional: boundary violation via frozen boundary check
# ===========================================================================

class TestT10_BoundaryViolationFrozen(unittest.TestCase):
    def test_frozen_boundary_violation_rejected(self):
        """T4 boundary check integration: REJECT on frozen boundary violation."""
        from tola.registry.boundaries import BoundaryViolation, enforce_boundary
        plan = PlanInput(
            title="Growth schedule write",
            domain="growth",
            steps=["Growth performs direct_schedule_write"],
            artifacts=[],
            success_criteria=["Done"],
            dependencies=[],
            assumptions=[],
            impact_area="scheduling",
        )
        # Verify the boundary check itself works
        with self.assertRaises(BoundaryViolation):
            enforce_boundary("growth", "direct_schedule_write")
        # And that the critic detects it in the plan
        result = critique_plan(plan)
        self.assertEqual(result.verdict, Verdict.REJECT)
        codes = [f.code for f in result.findings]
        self.assertIn(FC_BOUNDARY_VIOLATION, codes)


if __name__ == "__main__":
    unittest.main()
