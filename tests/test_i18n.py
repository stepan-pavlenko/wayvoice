import unittest
from unittest import mock
from string import Formatter
from wayvoice.i18n import (_EN, _RU, _TRANSLATIONS, SUPPORTED_UI_LANGUAGES,
                           resolve_language, tr, ui_language_labels)

class I18nTests(unittest.TestCase):
    def test_explicit_languages(self):
        self.assertEqual(resolve_language("ru"), "ru")
        self.assertEqual(resolve_language("en"), "en")

    def test_translation_exists(self):
        self.assertEqual(tr("nav.home", "ru"), "Главная")
        self.assertEqual(tr("nav.home", "en"), "Home")

    def test_every_key_is_translated_in_both_languages(self):
        # A key added to only one dictionary silently falls back to English in
        # the Russian UI, which is easy to miss in a screenshot-free review.
        self.assertEqual(sorted(_RU), sorted(_EN))
        self.assertEqual(len(_RU), len(_EN))

    def test_locale_is_used_for_auto(self):
        with mock.patch("wayvoice.i18n.locale.getlocale", return_value=("ru_RU", "UTF-8")):
            self.assertEqual(resolve_language("auto"), "ru")
        with mock.patch("wayvoice.i18n.locale.getlocale", return_value=("de_DE", "UTF-8")):
            self.assertEqual(resolve_language(None), "de")

    def test_explicit_choice_beats_the_locale(self):
        with mock.patch("wayvoice.i18n.locale.getlocale", return_value=("ru_RU", "UTF-8")):
            self.assertEqual(resolve_language("en"), "en")

    def test_all_ten_catalogues_have_keys_and_format_fields(self):
        self.assertEqual(len(_TRANSLATIONS), 10)
        self.assertEqual(len(SUPPORTED_UI_LANGUAGES), 11)  # includes automatic selection
        formatter = Formatter()
        def fields(text):
            return sorted((name, spec, conversion) for _, name, spec, conversion
                          in formatter.parse(text) if name is not None)
        for language, catalogue in _TRANSLATIONS.items():
            with self.subTest(language=language):
                self.assertEqual(set(catalogue), set(_EN))
                self.assertEqual(resolve_language(language), language)
                for key, text in catalogue.items():
                    with self.subTest(key=key):
                        self.assertIsInstance(text, str)
                        self.assertTrue(text.strip())
                        self.assertEqual(fields(text), fields(_EN[key]))

    def test_regional_ui_locales_and_unknown_fallback(self):
        for regional, base in [('pt_BR', 'pt'), ('zh-CN', 'zh'), ('es_MX', 'es'),
                               ('ja_JP', 'ja'), ('ar_SA', 'ar'), ('hi_IN', 'hi')]:
            self.assertEqual(resolve_language(regional), base)
        with mock.patch('wayvoice.i18n.locale.getlocale', return_value=('uk_UA', 'UTF-8')):
            self.assertEqual(resolve_language('auto'), 'en')
        self.assertEqual(len(ui_language_labels('en')), len(SUPPORTED_UI_LANGUAGES))


if __name__ == "__main__":
    unittest.main()
