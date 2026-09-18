import importlib
import unittest


class GeminiClientImportTest(unittest.TestCase):
    def test_module_imports_without_google_sdk_installed(self):
        module = importlib.import_module("core_engine.integrations.gemini_client")
        self.assertTrue(hasattr(module, "_get_client"))


if __name__ == "__main__":
    unittest.main()
