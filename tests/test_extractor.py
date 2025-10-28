import unittest

from opg_scraper_pkg.extractor import EmailExtractor


class TestExtractor(unittest.TestCase):
    def test_extraction_sources(self):
        html = (
            "<html><head><title>OPG Jurić – Kontakt</title></head>"
            "<body>"
            "<a href='mailto:kontakt@opg-juric.hr'>Email</a>"
            "<p>Za upite: opg.juric@example.hr ili INFO@EXAMPLE.HR</p>"
            "<script type='application/ld+json'>{\"email\": \"prodaja@opg-juric.hr\"}</script>"
            "</body></html>"
        )
        ex = EmailExtractor()
        found = ex.extract(html, "https://opg-juric.hr/kontakt")
        emails = sorted([e for e, _ in found])
        self.assertIn("kontakt@opg-juric.hr", emails)
        self.assertIn("opg.juric@example.hr", emails)
        self.assertIn("prodaja@opg-juric.hr", emails)
        self.assertIn("INFO@example.hr", emails)  # role-based filtering happens in crawler


if __name__ == "__main__":
    unittest.main()
