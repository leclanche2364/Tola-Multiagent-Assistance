import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOLAR_ROOT = REPO_ROOT


class TestS0DirectorySkeleton(unittest.TestCase):
    """S0-01: Verify the directory skeleton exists and is importable."""

    EXPECTED_PACKAGES = [
        "contracts",
        "curriculum",
        "goals",
        "learner_state",
        "mastery",
        "intensiq",
        "research",
        "evidence",
        "literature",
        "integrity",
        "events",
        "skills",
        "tests",
        "fixtures",
    ]

    EXPECTED_PLAIN_DIRS = ["docs", "reports"]

    def test_skeleton_packages_exist(self):
        for pkg in self.EXPECTED_PACKAGES:
            path = os.path.join(SCHOLAR_ROOT, pkg)
            self.assertTrue(os.path.isdir(path), f"Missing package dir: {pkg}")

    def test_skeleton_plain_dirs_exist(self):
        for d in self.EXPECTED_PLAIN_DIRS:
            path = os.path.join(SCHOLAR_ROOT, d)
            self.assertTrue(os.path.isdir(path), f"Missing plain dir: {d}")

    def test_python_packages_have_init(self):
        for pkg in self.EXPECTED_PACKAGES:
            init_path = os.path.join(SCHOLAR_ROOT, pkg, "__init__.py")
            self.assertTrue(os.path.isfile(init_path), f"Missing __init__.py in {pkg}")

    def test_plain_dirs_have_no_init(self):
        for d in self.EXPECTED_PLAIN_DIRS:
            init_path = os.path.join(SCHOLAR_ROOT, d, "__init__.py")
            self.assertFalse(os.path.isfile(init_path), f"Unexpected __init__.py in {d}")

    def test_contracts_files_exist(self):
        for fname in ["boundaries.md", "model_routing.md", "intensiq_handover.md"]:
            path = os.path.join(SCHOLAR_ROOT, "contracts", fname)
            self.assertTrue(os.path.isfile(path), f"Missing contract file: {fname}")

    def test_baseline_restore_manifest_exists(self):
        path = os.path.join(SCHOLAR_ROOT, "baseline", "RESTORE_MANIFEST.md")
        self.assertTrue(os.path.isfile(path), "Missing baseline/RESTORE_MANIFEST.md")

    def test_frozen_skills_file_exists(self):
        path = os.path.join(SCHOLAR_ROOT, "skills", "FROZEN_SKILLS.md")
        self.assertTrue(os.path.isfile(path), "Missing skills/FROZEN_SKILLS.md")

    def test_s0_test_file_exists(self):
        path = os.path.join(SCHOLAR_ROOT, "tests", "test_s0_baseline.py")
        self.assertTrue(os.path.isfile(path), "Missing tests/test_s0_baseline.py")


class TestS0FrozenSkills(unittest.TestCase):
    """S0-02: Verify every frozen skill name matches the plan exactly."""

    PLAN_SKILLS = [
        "curriculum-ingestion",
        "proficiency-mapping",
        "learning-goal-decomposition",
        "learner-state-analysis",
        "learning-gap-analysis",
        "adaptive-learning-strategy",
        "mastery-estimation",
        "proficiency-readiness",
        "intensiq-plan-orchestration",
        "intensiq-feedback-analysis",
        "intensiq-feature-gap-detection",
        "study-requirement-to-rhythm",
        "literature-discovery",
        "evidence-appraisal",
        "evidence-to-learning-strategy",
        "research-question-decomposition",
        "source-quality-assessment",
        "claim-verification",
        "evidence-synthesis",
        "research-to-tola",
        "assessment-integrity",
        "learning-effectiveness-review",
    ]

    PLAN_EXCLUDED = [
        "quiz-generation",
        "flashcard-generation",
        "case-teaching",
        "direct tutoring",
        "study-material-generation",
        "weekly-test-generation",
    ]

    def _read_skills_md(self):
        path = os.path.join(SCHOLAR_ROOT, "skills", "FROZEN_SKILLS.md")
        with open(path, "r", encoding="ascii") as f:
            return f.read()

    def test_frozen_skills_match_plan(self):
        content = self._read_skills_md()
        for skill in self.PLAN_SKILLS:
            self.assertIn(skill, content, f"Missing frozen skill: {skill}")

    def test_excluded_skills_present(self):
        content = self._read_skills_md()
        for skill in self.PLAN_EXCLUDED:
            self.assertIn(skill, content, f"Missing excluded skill: {skill}")

    def test_no_extra_frozen_skills(self):
        content = self._read_skills_md()
        # Only scan the frozen skills section (before the excluded section)
        frozen_section = content.split("## Explicitly Excluded")[0]
        found = re.findall(r"^\d+\.\s+([a-z][a-z0-9-]*)", frozen_section, re.MULTILINE)
        extra = set(found) - set(self.PLAN_SKILLS)
        self.assertEqual(extra, set(), f"Unexpected frozen skills in md: {extra}")

    def test_frozen_skill_count(self):
        content = self._read_skills_md()
        frozen_section = content.split("## Explicitly Excluded")[0]
        found = re.findall(r"^\d+\.\s+([a-z][a-z0-9-]*)", frozen_section, re.MULTILINE)
        self.assertEqual(len(found), 22, f"Expected 22 frozen skills, found {len(found)}")


class TestS0Boundaries(unittest.TestCase):
    """S0-02: Verify boundary doc contains mandatory non-responsibility phrases."""

    MANDATORY_PHRASES = [
        "learner-facing tutoring",
        "quiz generation",
        "flashcard generation",
        "case teaching",
        "study-material generation",
        "weekly-test generation",
        "marking study complete",
        "submitting assessments",
        "formal clinical sign-off",
        "My Rhythm writes",
        "portfolio priority",
        "cross-agent delegation",
        "raw Supabase access",
        "model routing changes",
    ]

    def _read_boundaries(self):
        path = os.path.join(SCHOLAR_ROOT, "contracts", "boundaries.md")
        with open(path, "r", encoding="ascii") as f:
            return f.read()

    def test_all_non_responsibility_phrases_present(self):
        content = self._read_boundaries()
        for phrase in self.MANDATORY_PHRASES:
            self.assertIn(phrase, content, f"Missing non-responsibility phrase: {phrase}")

    def test_tola_responsibility_present(self):
        content = self._read_boundaries()
        self.assertIn("Tola", content)
        self.assertIn("Portfolio priority", content)

    def test_rhythm_responsibility_present(self):
        content = self._read_boundaries()
        self.assertIn("Rhythm", content)
        self.assertIn("My Rhythm writes", content)

    def test_intensiq_responsibility_present(self):
        content = self._read_boundaries()
        self.assertIn("IntenSIQ", content)

    def test_scholar_responsibility_present(self):
        content = self._read_boundaries()
        self.assertIn("Scholar", content)


class TestS0ModelRouting(unittest.TestCase):
    """S0-03: Verify model routing doc states ling-3.0-flash as sole reasoning model."""

    def _read_routing(self):
        path = os.path.join(SCHOLAR_ROOT, "contracts", "model_routing.md")
        with open(path, "r", encoding="ascii") as f:
            return f.read()

    def test_ling_3_0_flash_is_sole_reasoning_model(self):
        content = self._read_routing()
        self.assertIn("ling-3.0-flash", content.lower(),
                       "model_routing.md must state ling-3.0-flash as the reasoning model")

    def test_no_semantic_escalation(self):
        content = self._read_routing()
        self.assertIn("no semantic model escalation", content.lower(),
                       "model_routing.md must state no semantic model escalation")

    def test_failure_policy_one_retry(self):
        content = self._read_routing()
        self.assertIn("one retry", content.lower(),
                       "model_routing.md must state one retry failure policy")

    def test_no_silent_model_switch(self):
        content = self._read_routing()
        self.assertIn("never silently switch", content.lower(),
                       "model_routing.md must state Scholar must not silently switch models")

    def test_r0_deterministic_code(self):
        content = self._read_routing()
        self.assertIn("R0", content)
        self.assertIn("DETERMINISTIC CODE", content)

    def test_r1_ling_only(self):
        content = self._read_routing()
        self.assertIn("R1", content)
        self.assertIn("LING 3.0 FLASH", content.upper())


class TestS0IntensiqHandover(unittest.TestCase):
    """S0-04: Verify IntenSIQ handover doc captures inspected capabilities and three new additions."""

    def _read_handover(self):
        path = os.path.join(SCHOLAR_ROOT, "contracts", "intensiq_handover.md")
        with open(path, "r", encoding="ascii") as f:
            return f.read()

    def test_existing_capabilities_captured(self):
        content = self._read_handover()
        self.assertIn("course/topic/content", content)
        self.assertIn("goals", content)
        self.assertIn("progress", content)
        self.assertIn("practice", content)
        self.assertIn("tests", content)
        self.assertIn("cases", content)
        self.assertIn("study materials", content)
        self.assertIn("recordings", content)
        self.assertIn("reasoning", content)

    def test_learner_state_read_model_present(self):
        content = self._read_handover()
        self.assertIn("learner-state", content.lower())
        self.assertIn("GET", content)

    def test_versioned_learning_plan_present(self):
        content = self._read_handover()
        self.assertIn("learning-plan", content.lower())
        self.assertIn("GET", content)
        self.assertIn("PUT", content)

    def test_durable_events_outbox_present(self):
        content = self._read_handover()
        self.assertIn("events", content.lower())
        self.assertIn("cursor", content.lower())

    def test_three_new_integrations_count(self):
        content = self._read_handover()
        count = content.lower().count("new integration")
        self.assertGreaterEqual(count, 1,
                                "Handover must mention the three new integration additions")


class TestS0SecretScan(unittest.TestCase):
    """S0-05: Assert no credential-looking strings in any scholar/ text file."""

    CREDENTIAL_PATTERNS = [
        r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{20,}",
        r"password\s*=\s*['\"]?[^'\"]+",
        r"BEGIN PRIVATE KEY",
    ]

    def test_no_credentials_in_scholar_files(self):
        found = []
        for root, dirs, files in os.walk(SCHOLAR_ROOT):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="ascii", errors="ignore") as f:
                        content = f.read()
                    # Remove our own test-file false positives before scanning
                    content = content.replace("BEGIN PRIVATE KEY", "BEGIN PRIVATE_KEY_PLACEHOLDER")
                    for pattern in self.CREDENTIAL_PATTERNS:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for m in matches:
                            found.append((fpath, pattern, m[:40]))
                except Exception:
                    pass
        self.assertEqual(found, [],
                         f"Credential-like strings found: {found}")


if __name__ == "__main__":
    unittest.main()