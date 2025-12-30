.PHONY: install
install:
	@echo "Installing packages..."
	@pip install .
	@echo "Done."

.PHONY: install-dev
install-dev:
	@echo "Installing dev packages..."
	@pip install --upgrade pipx
	@pipx install pdm
	@pdm install --dev
	@echo "Installing pre-commit hooks..."
	@pre-commit install

.PHONY: check-hooks
check-hooks:
	@echo "Checking pre-commit hooks..."
	@pre-commit run --all-files
	@echo "Done."
