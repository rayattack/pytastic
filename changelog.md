# Changelog

## [0.1.6] - 2026-02-11

### Added
- Added support for specifying what fields should be partial in `.validate(..., partial=["field1", "field2"])`.

## [0.1.5] - 2026-02-10

### Fixed
- Runtime `strip=True` now propagates to all nested TypedDicts, including items inside `List[TypedDict]`.
- Schema-level `strip=True` stays local to the type where it is defined (no propagation).

## [0.1.4] - 2026-02-10

### Added
- `strip=True` support: removes extra fields not defined in the schema. Available via `_: Annotated[Any, "strip=True"]` in the schema or `vx.validate(Schema, data, strip=True)` at runtime. Both paths are compiled and equally fast.
- `partial=True` support: skips required field checks, validating only present fields. Useful for PATCH-style updates. Available via `vx.validate(Schema, data, partial=True)`. Does not fill defaults.

### Changed
- `CodegenCompiler.compile()` now caches by `(schema, strip, partial)` tuple to support compiled variants for all flag combinations.

## [0.1.3] - 2026-02-08

### Added
- Support for `exclusive_min` and `exclusive_max` numeric constraints.
- Support for `step` (multipleOf) numeric constraint.
- Support for string formats: `email`, `uuid`, `ipv4`, `date-time`, `uri`.

### Fixed
- Fixed `UnboundLocalError` when optional fields are followed by required fields in generated validation code.
- Fixed variable shadowing issue in nested list validation loops.
- Added safe type casting for constraints in generated validation code to prevent `TypeError`.


## [0.1.0] - 2026-02-08

### Added
- Added support for more json schema validation increasing syntax coverage
- **Breaking Change** moved to more expressive syntax for schema validation different from 0.0.1


## [0.0.7] - 2026-02-07

### Added
- Add support for json schema syntax
- Add documentation for library to github pages
- Add tests for library


## [0.0.1] - 2026-01-07

### Added
- Initial release