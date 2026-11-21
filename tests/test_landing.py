from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "index.html"
README_MD = ROOT / "README.md"


class _LandingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_attrs: dict[str, str | None] = {}
        self.metas: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.anchors: list[dict[str, str | None]] = []
        self.ids: set[str] = set()
        self.tags: list[str] = []
        self.h1_count = 0
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        self.tags.append(tag)
        if "id" in attr_map and attr_map["id"]:
            self.ids.add(attr_map["id"])
        if tag == "html":
            self.html_attrs = attr_map
        elif tag == "meta":
            self.metas.append(attr_map)
        elif tag == "link":
            self.links.append(attr_map)
        elif tag == "a":
            self.anchors.append(attr_map)
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


class TestLandingPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html_text = INDEX_HTML.read_text(encoding="utf-8")
        cls.readme_text = README_MD.read_text(encoding="utf-8")
        cls.parser = _LandingParser()
        cls.parser.feed(cls.html_text)

    def test_document_basics(self) -> None:
        self.assertEqual(self.parser.html_attrs.get("lang"), "en")
        self.assertTrue(self.parser.title.strip())
        charsets = [m.get("charset") for m in self.parser.metas if m.get("charset")]
        self.assertIn("utf-8", [c.lower() for c in charsets])
        viewports = [m.get("content", "") for m in self.parser.metas if m.get("name") == "viewport"]
        self.assertTrue(any("width=device-width" in v for v in viewports))

    def test_seo_and_open_graph_metadata(self) -> None:
        descriptions = [m.get("content", "") for m in self.parser.metas if m.get("name") == "description"]
        self.assertTrue(any(len(d.strip()) >= 40 for d in descriptions))
        canonicals = [l.get("href", "") for l in self.parser.links if l.get("rel") == "canonical"]
        self.assertIn("https://goktugozkanmd.github.io/clinical-ai-eval-starter/", canonicals)
        og_props = {m.get("property") for m in self.parser.metas if m.get("property")}
        for prop in ("og:type", "og:title", "og:description", "og:url"):
            self.assertIn(prop, og_props)

    def test_semantic_landmarks_and_skip_link(self) -> None:
        self.assertEqual(self.parser.h1_count, 1)
        self.assertIn("header", self.parser.tags)
        self.assertIn("main", self.parser.tags)
        self.assertIn("main-content", self.parser.ids)
        skip_hrefs = [
            a.get("href")
            for a in self.parser.anchors
            if "skip-link" in (a.get("class") or "").split()
        ]
        self.assertIn("#main-content", skip_hrefs)

    def test_internal_fragment_links_resolve(self) -> None:
        for anchor in self.parser.anchors:
            href = anchor.get("href") or ""
            if href.startswith("#") and len(href) > 1:
                self.assertIn(href[1:], self.parser.ids, f"Broken fragment link: {href}")

    def test_external_target_blank_links_are_safe(self) -> None:
        blank_anchors = [a for a in self.parser.anchors if a.get("target") == "_blank"]
        self.assertTrue(blank_anchors)
        for anchor in blank_anchors:
            rel_tokens = set((anchor.get("rel") or "").split())
            self.assertTrue(
                {"noopener", "noreferrer"}.issubset(rel_tokens),
                f"Missing noopener/noreferrer on {anchor.get('href')}",
            )

    def test_keyboard_focus_and_mobile_tap_targets(self) -> None:
        self.assertIn(":focus-visible", self.html_text)
        self.assertIn("min-height:44px", self.html_text)
        self.assertIn("overflow-wrap:anywhere", self.html_text)

    def test_readme_and_landing_urls_stay_in_sync(self) -> None:
        shared_urls = [
            "https://github.com/goktugozkanmd/clinical-ai-eval-starter/releases/download/free-starter-slice-v1/Free-Starter-Slice-v1.zip",
            "https://goktugozkanmd-manugate-md.static.hf.space",
            "https://github.com/goktugozkanmd/manugate-md",
            "drozkan2+para@gmail.com",
        ]
        for url in shared_urls:
            self.assertIn(url, self.html_text)
            self.assertIn(url, self.readme_text)

    def test_no_raw_ampersand_in_mailto_href(self) -> None:
        self.assertNotIn("&body=", self.html_text)
        self.assertIn("&amp;body=", self.html_text)


if __name__ == "__main__":
    unittest.main()
