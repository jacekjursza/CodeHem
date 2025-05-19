# Developer Guide

This guide explains how to extend and use CodeHem for custom workflows.

## Plugins

Language support is provided via entry-points named `codehem.languages`. A plugin
exposes a `<Lang>LanguageService` and registers it using the
`@language_service` decorator from `codehem.core.registry`.
The easiest starting point is the `codehem-lang-template` cookiecutter which
wires a service, formatter and manipulator skeleton.

## Patch API

Use `CodeHem.apply_patch` to modify code fragments in a controlled way. Each call
requires an XPath pointing to the element, the new code and the desired mode
(`replace`, `append`, `prepend`). The method returns a JSON diff including
line statistics.

## Builder helpers

Convenience methods `new_function`, `new_class` and `new_method` generate code
from structured data and insert it automatically. These helpers keep code
formatting consistent across languages.

## Diagrams

Architecture and plugin relations are illustrated in `docs/architecture.puml`.
PlantUML renders the diagrams for the GitHub Pages site.
