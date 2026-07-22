"""Unit tests for the backend localization foundation — see
app/core/i18n.py and docs/localization-and-accessibility.md
#backend-message-localization."""

import pytest

from app.core.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, resolve_locale, translate


class TestResolveLocale:
    def test_returns_default_when_header_missing(self) -> None:
        assert resolve_locale(None) == DEFAULT_LOCALE

    def test_returns_default_when_header_empty(self) -> None:
        assert resolve_locale("") == DEFAULT_LOCALE

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_matches_a_supported_primary_subtag(self, locale: str) -> None:
        assert resolve_locale(f"{locale}-XX,en;q=0.5") == locale

    def test_falls_back_to_default_for_an_unsupported_locale(self) -> None:
        assert resolve_locale("fr-FR,de;q=0.5") == DEFAULT_LOCALE

    def test_picks_the_first_supported_tag_in_listed_order(self) -> None:
        assert resolve_locale("fr-FR,hi;q=0.8,en;q=0.5") == "hi"


class TestTranslate:
    def test_returns_none_for_an_unknown_code(self) -> None:
        assert translate("does.not.exist", "en") is None

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_every_supported_locale_has_every_catalog_key(self, locale: str) -> None:
        for code in ("auth.required", "auth.forbidden", "validation.failed", "error.internal"):
            value = translate(code, locale)
            assert value
            assert isinstance(value, str)

    def test_falls_back_to_default_locale_for_an_unsupported_locale_code(self) -> None:
        assert translate("auth.required", "fr") == translate("auth.required", DEFAULT_LOCALE)
