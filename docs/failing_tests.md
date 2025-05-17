# Failing Tests Overview

The following tests currently fail when running the test suite with `pytest`.
Each entry includes the test module and the specific test cases that need to be
addressed.

## tests/core

- **test_error_utilities.py** – fails to import `retry_exponential` during test collection.
- **test_input_validation.py**
  - `BasicValidatorsTest.test_validate_max_value`
  - `BasicValidatorsTest.test_validate_min_value`
  - `BasicValidatorsTest.test_validate_range`
  - `ComplexValidatorsTest.test_validate_list_items`
  - `UtilityFunctionsTest.test_create_schema_validator`
  - `PrebuiltValidatorsTest.test_numeric_validators`
  - `IntegrationTest.test_real_world_example`
- **test_retry_mechanisms.py**
  - `RetryUtilitiesTests.test_can_retry_with_exception_predicate`
  - `RetryUtilitiesTests.test_can_retry_with_wait_strategy`

## tests/common

- **test_codehem2.py**
  - `CodeHem2Tests.test_get_property_methods_by_xpath`
  - `CodeHem2Tests.test_get_text_by_xpath`
  - `CodeHem2Tests.test_get_text_by_xpath_properties`

## tests/python

- **test_element_extraction.py**
  - `test_extract_property`
  - `test_extract_imports`
- **test_xpath_results.py**
  - `test_property_getter`
  - `test_property_setter`
  - `test_property_setter_def`
  - `test_property_setter_body`
  - `test_duplicated_method`
  - `test_getter_vs_setter`

## Other integration tests

- **test_full_integration.py**
  - `FullIntegrationTest.test_python_complex_code`
  - `FullIntegrationTest.test_typescript_complex_code`
- **test_post_processor_integration.py**
  - `PostProcessorIntegrationTest.test_post_processor_factory_registration`
  - `PostProcessorIntegrationTest.test_post_processor_instantiation`
- **test_refactored_extraction_service.py**
  - `TestExtractionService.test_find_element`
- **typescript/test_element_extraction.py**
  - `test_extract_ts_interface`
  - `test_extract_ts_imports`

In total there are **28 failing tests** plus the import error in
`test_error_utilities.py`. These tests will require updates to bring the suite
back to a passing state.
