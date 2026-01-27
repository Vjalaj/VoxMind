import unittest
from response_generator import ResponseGenerator

class TestResponses(unittest.TestCase):

    def setUp(self):
        self.rg = ResponseGenerator()
        self.user = "user1"

    def test_onboarding(self):
        res = self.rg.generate(self.user, "greet", name="Swadhin")
        self.assertIn("Swadhin", res)

    def test_personality_modes(self):
        tones = set(
            self.rg.generate(self.user, "greet", tone=t, name="Swadhin")
            for t in ["friendly", "professional", "humorous"]
        )
        self.assertGreaterEqual(len(tones), 2)

    def test_variation(self):
        responses = set(
            self.rg.generate(self.user, "greet", name="Swadhin")
            for _ in range(10)
        )
        self.assertGreaterEqual(len(responses), 2)

    def test_confirmation(self):
        res = self.rg.generate(self.user, "delete")
        self.assertTrue("confirm" in res.lower() or "sure" in res.lower())

    def test_error(self):
        res = self.rg.generate(self.user, "unknown")
        self.assertTrue(len(res) > 0)

if __name__ == "__main__":
    unittest.main()
