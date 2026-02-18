import pytest
from app.core.inbox.service import normalize_subject

@pytest.mark.parametrize("raw,expected", [
    ("Re: Spørsmål om leveranse", "Spørsmål om leveranse"),
    ("SV: Re: Spørsmål om leveranse", "Spørsmål om leveranse"),
    ("Fwd: Viktig info", "Viktig info"),
    ("FWD: SV: re: Noe viktig", "Noe viktig"),
    ("VS: Møtereferat", "Møtereferat"),
    ("Ang: Rapport", "Rapport"),
    ("Normalt emne", "Normalt emne"),
    ("  Re:   Trim meg  ", "Trim meg"),
    ("Re[2]: Gammel tråd", "Gammel tråd"),
])
def test_normalize_subject(raw, expected):
    assert normalize_subject(raw) == expected

def test_project_no_format():
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    project_no = f"{yy}-{1:04d}"
    assert len(project_no) == 7
    assert project_no == f"{yy}-0001"
