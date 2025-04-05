# Plik: core/registry.py
# Zmiany: Usunięcie rejestracji dla TemplatePropertyGetterExtractor i TemplatePropertySetterExtractor

import importlib
import logging
import os
import traceback
from typing import Any, List, Optional, Type
import rich

from codehem.core.language_service import LanguageService
from codehem.core.extractors.base import BaseExtractor
# Usunięto importy nieistniejących już klas, jeśli były
# from codehem.core.extractors.template_property_getter_extractor import TemplatePropertyGetterExtractor # USUNIĘTE
# from codehem.core.extractors.template_property_setter_extractor import TemplatePropertySetterExtractor # USUNIĘTE


logger = logging.getLogger(__name__)

class Registry:
    """Centralny rejestr komponentów CodeHem."""
    _instance = None

    def __init__(self):
        self._initialized = False
        self._initialize() # Inicjalizuj od razu

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
            # Inicjalizacja przeniesiona do __init__, aby uniknąć problemów z wielokrotnym wywołaniem
        return cls._instance

    def _initialize(self):
        """Inicjalizuje puste rejestry."""
        # Sprawdź, czy już zainicjalizowano, aby uniknąć resetowania przy ponownym tworzeniu instancji
        if hasattr(self, '_initialized') and self._initialized:
             return
        self.language_detectors = {}
        self.language_services = {}
        self.all_descriptors = {}
        self.all_extractors = {} # { 'lang/type': ExtractorClass }
        self.all_manipulators = {} # { 'lang_type': ManipulatorClass }
        self.discovered_modules = set()
        self.language_service_instances = {} # Cache dla instancji LanguageService
        self._initialized = False # Ustaw na False, zostanie zmienione w initialize_components
        logger.debug("Registry _initialize completed.")


    def register_language_detector(self, cls):
        """Rejestruje klasę detektora języka."""
        try:
            instance = cls()
            language_code = instance.language_code.lower()
            if language_code in self.language_detectors:
                 logger.warning(f"Detektor języka dla '{language_code}' jest już zarejestrowany ({self.language_detectors[language_code].__class__.__name__}). Nadpisywanie przez {cls.__name__}.")
            self.language_detectors[language_code] = instance
            rich.print(f'Registered language detector: {cls.__name__} for {language_code}')
        except Exception as e:
            logger.error(f"Błąd podczas rejestracji detektora języka {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_language_service(self, cls: Type[LanguageService]):
        """Rejestruje klasę serwisu językowego."""
        try:
            language_code = cls.LANGUAGE_CODE.lower()
            if language_code in self.language_services:
                 logger.warning(f"Serwis językowy dla '{language_code}' jest już zarejestrowany ({self.language_services[language_code].__name__}). Nadpisywanie przez {cls.__name__}.")
            self.language_services[language_code] = cls
            rich.print(f'Registered language service: {cls.__name__} for {language_code}')
        except Exception as e:
            logger.error(f"Błąd podczas rejestracji serwisu językowego {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_extractor(self, cls: Type[BaseExtractor]):
        """Rejestruje klasę ekstraktora."""
        try:
            # Sprawdzenie, czy usunięte klasy są rejestrowane
            # if cls.__name__ in ['TemplatePropertyGetterExtractor', 'TemplatePropertySetterExtractor',
            #                    'PythonPropertyGetterExtractor', 'PythonPropertySetterExtractor']:
            #     logger.warning(f"Próba rejestracji usuniętego ekstraktora: {cls.__name__}. Pomijanie.")
            #     return cls # Nie rejestruj usuniętych

            language_code = cls.LANGUAGE_CODE.lower()
            element_type = cls.ELEMENT_TYPE.value.lower()
            extractor_key = f'{language_code}/{element_type}'

            if extractor_key in self.all_extractors:
                # Zezwalaj na nadpisywanie, ale loguj ostrzeżenie
                logger.warning(f"Ekstraktor dla '{extractor_key}' jest już zarejestrowany ({self.all_extractors[extractor_key].__name__}). Nadpisywanie przez {cls.__name__}.")
            self.all_extractors[extractor_key] = cls
            rich.print(f'Registered extractor: {cls.__name__} for {extractor_key}')
        except Exception as e:
            logger.error(f"Błąd podczas rejestracji ekstraktora {cls.__name__}: {e}", exc_info=True)
        return cls


    def register_manipulator(self, cls):
        """Rejestruje klasę manipulatora."""
        try:
            language_code = cls.LANGUAGE_CODE.lower()
            element_type = cls.ELEMENT_TYPE.value.lower()
            key = f'{language_code}_{element_type}' # Klucz używany w starym kodzie
            if key in self.all_manipulators:
                 logger.warning(f"Manipulator dla '{key}' jest już zarejestrowany ({self.all_manipulators[key].__name__}). Nadpisywanie przez {cls.__name__}.")
            self.all_manipulators[key] = cls
            rich.print(f'Registered manipulator: {cls.__name__} for {language_code}/{element_type}')
        except Exception as e:
            logger.error(f"Błąd podczas rejestracji manipulatora {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_element_type_descriptor(self, cls):
        """Rejestruje deskryptor typu elementu."""
        try:
            instance = cls()
            language_code = instance.language_code.lower()
            element_type = instance.element_type.value.lower()
            if language_code not in self.all_descriptors:
                self.all_descriptors[language_code] = {}
            if element_type in self.all_descriptors[language_code]:
                 logger.warning(f"Deskryptor dla '{language_code}/{element_type}' jest już zarejestrowany ({self.all_descriptors[language_code][element_type].__class__.__name__}). Nadpisywanie przez {cls.__name__}.")
            self.all_descriptors[language_code][element_type] = instance
            rich.print(f'Registered descriptor: {cls.__name__} for {language_code}/{element_type}')
        except Exception as e:
            logger.error(f"Błąd podczas rejestracji deskryptora {cls.__name__}: {e}", exc_info=True)
        return cls


    def get_language_detector(self, language_code: str) -> Optional[Any]:
        """Pobiera instancję detektora języka."""
        return self.language_detectors.get(language_code.lower())

    def get_language_service(self, language_code: str) -> Optional[LanguageService]:
        """Pobiera lub tworzy instancję serwisu językowego (singleton per język)."""
        if not isinstance(language_code, str):
            logger.error(f'Nieprawidłowy typ language_code: {type(language_code)}')
            return None

        lang_code_lower = language_code.lower()

        # Sprawdź cache
        if lang_code_lower in self.language_service_instances:
            logger.debug(f"Zwracanie istniejącej instancji LanguageService dla '{lang_code_lower}'.")
            return self.language_service_instances[lang_code_lower]

        # Jeśli nie ma w cache, spróbuj stworzyć nową instancję
        language_service_cls = self.language_services.get(lang_code_lower)
        if not language_service_cls:
            logger.error(f"Nie znaleziono zarejestrowanej klasy LanguageService dla '{lang_code_lower}'.")
            return None

        logger.debug(f"Tworzenie nowej instancji LanguageService dla '{lang_code_lower}'.")
        try:
            # Wstrzykiwanie zależności - przekazujemy *całe* słowniki klas/deskryptorów
            # Instancja LanguageService sama sobie wybierze potrzebne komponenty
            # i stworzy instancje ekstraktorów/manipulatorów
            formatter_class = None
            if lang_code_lower == 'python':
                 # Leniwe importowanie, aby uniknąć cyklicznych zależności
                 from codehem.languages.lang_python.formatting.python_formatter import PythonFormatter
                 formatter_class = PythonFormatter
            # Można dodać więcej warunków dla innych języków

            # Tworzenie instancji
            instance = language_service_cls(
                extractors=self.all_extractors,
                manipulators=self.all_manipulators,
                element_type_descriptors=self.all_descriptors,
                formatter_class=formatter_class
            )

            # Zapisz w cache
            self.language_service_instances[lang_code_lower] = instance
            logger.debug(f"Utworzono i zapisano w cache instancję LanguageService dla '{lang_code_lower}'.")
            return instance
        except Exception as e:
            logger.exception(f"Krytyczny błąd podczas inicjalizacji LanguageService dla '{lang_code_lower}': {e}")
            # Nie zapisuj błędnej instancji w cache
            return None


    def get_supported_languages(self) -> List[str]:
        """Zwraca listę kodów obsługiwanych języków."""
        return list(self.language_services.keys())

    def discover_modules(self, package_name='codehem', recursive=True):
        """Odkrywa i importuje moduły w pakiecie, aby wywołać rejestrację."""
        rich.print(f'Discovering modules in package: {package_name}')
        try:
            package = importlib.import_module(package_name)
            package_dir = os.path.dirname(package.__file__)

            for item in os.listdir(package_dir):
                full_path = os.path.join(package_dir, item)

                if item.startswith('_') or item.startswith('.'):
                    continue

                if item.endswith('.py'):
                    module_name = f'{package_name}.{item[:-3]}'
                    if module_name not in self.discovered_modules:
                        try:
                            importlib.import_module(module_name)
                            self.discovered_modules.add(module_name)
                            # Ograniczono gadatliwość logowania
                            # rich.print(f'Imported module: {module_name}')
                        except ModuleNotFoundError:
                             logger.warning(f"Nie można zaimportować modułu {module_name} (nie znaleziono).")
                        except Exception as e:
                            logger.warning(f'Error importing module {module_name}: {e}\n{traceback.format_exc(limit=1)}')
                            # print(traceback.format_exc()) # Pełny traceback w razie potrzeby

                elif os.path.isdir(full_path) and recursive:
                    # Sprawdź, czy to pakiet (zawiera __init__.py)
                    if os.path.exists(os.path.join(full_path, '__init__.py')):
                        subpackage_name = f'{package_name}.{item}'
                        self.discover_modules(subpackage_name, recursive=recursive)

        except ModuleNotFoundError:
             logger.error(f"Nie można znaleźć pakietu startowego: {package_name}")
        except Exception as e:
            logger.error(f'Error discovering modules in {package_name}: {e}', exc_info=True)


    def initialize_components(self):
        """Odkrywa i inicjalizuje wszystkie komponenty. Wywoływana raz."""
        if self._initialized:
            logger.debug("Komponenty już zainicjalizowane.")
            return

        logger.info("Rozpoczynanie inicjalizacji komponentów CodeHem...")
        self.discover_modules()
        self._initialized = True # Ustaw flagę *po* odkryciu modułów
        rich.print(f'Components initialized: {len(self.language_detectors)} detectors, {len(self.language_services)} services, {len(self.all_extractors)} extractors, {len(self.all_manipulators)} manipulators registered.')
        logger.info("Inicjalizacja komponentów zakończona.")

# --- Instancja globalna ---
registry = Registry()

# --- Dekoratory rejestracyjne ---
def language_detector(cls):
    """Dekorator do rejestracji detektora języka."""
    return registry.register_language_detector(cls)

def language_service(cls):
    """Dekorator do rejestracji serwisu językowego."""
    return registry.register_language_service(cls)

def extractor(cls):
    """Dekorator do rejestracji ekstraktora."""
    return registry.register_extractor(cls)


def manipulator(cls):
    """Dekorator do rejestracji manipulatora."""
    return registry.register_manipulator(cls)

def element_type_descriptor(cls):
    """Dekorator do rejestracji deskryptora typu elementu."""
    return registry.register_element_type_descriptor(cls)