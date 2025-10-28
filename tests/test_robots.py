import unittest
from urllib import robotparser

from opg_scraper_pkg.config import USER_AGENT


class TestRobots(unittest.TestCase):
    def test_basic_rules(self):
        rp = robotparser.RobotFileParser()
        robots_txt = """
        User-agent: *
        Disallow: /private
        Allow: /
        """.strip().splitlines()
        rp.parse(robots_txt)
        self.assertTrue(rp.can_fetch(USER_AGENT, "https://example.com/"))
        self.assertFalse(rp.can_fetch(USER_AGENT, "https://example.com/private/secret.html"))


if __name__ == "__main__":
    unittest.main()

