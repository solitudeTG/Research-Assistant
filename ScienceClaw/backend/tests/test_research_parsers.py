from backend.research_assistant.parsers import _parse_grobid_tei, _parse_pdf_with_grobid


def test_parse_grobid_tei_extracts_metadata_sections_and_pages():
    tei = """<?xml version="1.0" encoding="UTF-8"?>
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader>
        <fileDesc>
          <titleStmt>
            <title>Evidence-Aware Paper Assistants</title>
          </titleStmt>
          <sourceDesc>
            <biblStruct>
              <analytic>
                <author><persName><forename>Ada</forename><surname>Lovelace</surname></persName></author>
                <author><persName><forename>Grace</forename><surname>Hopper</surname></persName></author>
              </analytic>
            </biblStruct>
          </sourceDesc>
        </fileDesc>
        <profileDesc>
          <abstract><p>This paper studies evidence-aware research assistants.</p></abstract>
        </profileDesc>
      </teiHeader>
      <text>
        <body>
          <div>
            <head>Introduction</head>
            <pb n="2"/>
            <p>Research assistants need paper-grounded citations.</p>
          </div>
          <div>
            <head>Method</head>
            <pb n="5"/>
            <p>Hybrid retrieval combines lexical and vector evidence.</p>
          </div>
        </body>
      </text>
    </TEI>
    """

    parsed = _parse_grobid_tei(tei, fallback_title="fallback")

    assert parsed.title == "Evidence-Aware Paper Assistants"
    assert parsed.authors == ["Ada Lovelace", "Grace Hopper"]
    assert parsed.abstract == "This paper studies evidence-aware research assistants."
    assert parsed.sections[0].name == "Introduction"
    assert parsed.sections[0].page == 2
    assert "paper-grounded citations" in parsed.sections[0].text
    assert parsed.sections[1].page == 5
    assert parsed.raw_text


def test_parse_pdf_with_grobid_ignores_environment_proxy(monkeypatch, tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    calls = []

    class FakeResponse:
        text = """<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <fileDesc><titleStmt><title>Proxy Safe GROBID</title></titleStmt></fileDesc>
            <profileDesc><abstract><p>Abstract text.</p></abstract></profileDesc>
          </teiHeader>
          <text><body><div><head>Intro</head><p>Paper-grounded citation text.</p></div></body></text>
        </TEI>
        """

        def raise_for_status(self):
            return None

    def fake_post(*args, **kwargs):
        calls.append(kwargs)
        return FakeResponse()

    monkeypatch.setattr("backend.research_assistant.parsers.httpx.post", fake_post)

    parsed = _parse_pdf_with_grobid(
        pdf_path,
        grobid_url="http://localhost:8070",
        timeout_seconds=3,
    )

    assert parsed.parser == "grobid-tei"
    assert parsed.title == "Proxy Safe GROBID"
    assert calls[0]["trust_env"] is False
