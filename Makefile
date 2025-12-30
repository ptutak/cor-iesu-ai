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

.PHONY: run-dev
run-dev:
	python src/manage.py runserver

.PHONY: migrations
migrations:
	python src/manage.py makemigrations
	python src/manage.py migrate
