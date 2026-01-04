## AI guidelines context:
- follow linter guidelines via pre-commit hooks
- always add type annotations for functions and classes
- use # type: ignore only when absolutely necessary
- always write unit tests when implementing new features
- when ensuring that tests PASS you have to either:
  - correct the test
  - correct the code functionality that the test is checking
- don't use unittest.patch, use monkeypatch instead
- don't use unittest module, use pytest instead
- keep monkeypatching to the minimum and only for external dependencies if possible like:
  - mocking external APIs
  - mocking database connections
  - mocking external services (like email)
- keep the code coverage on the required level
- don't leave any test as failed
- never create test scripts, always create unit tests and integration tests instead
- don't reformat the code which was already formatted by the linters
- don't add any new features or scripts if not asked for, add only things you are directly asked for
- if it's necessary or useful to add something additional ask before adding it
- if you want to add a new command or management script add it to the makefile
- if you want to add a new library ask first
- never modify pyproject.toml without permission
- never modify .pre-commit-config.yaml without permission
- never modify Makefile without permission
- when ending work, create a PROJECT_STATUS.md summary file

## General programming principles:
- use SOLID:
  - Single Responsibility Principle (SRP)
  - Open/Closed Principle (OCP)
  - Liskov Substitution Principle (LSP)
  - Interface Segregation Principle (ISP)
  - Dependency Inversion Principle (DIP)
- use DRY - Don't Repeat Yourself (DRY)
- use KISS - Keep It Simple, Stupid (KISS)

## Useful available make commands:
- make check-hooks
- make tests-unit
- make tests-integration
- make migrations

## Useful files:
- .pre-commit-config.yaml
- Makefile
- pyproject.toml
- README.md
