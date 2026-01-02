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

.PHONY: start-mailcatcher
start-mailcatcher:
	@echo "Starting MailCatcher..."
	mailcatcher || echo "MailCatcher is already running at http://localhost:1080"

.PHONY: stop-mailcatcher
stop-mailcatcher:
	@echo "Stopping MailCatcher..."
	@pkill -f mailcatcher || echo "MailCatcher was not running"

.PHONY: run-dev
run-dev: start-mailcatcher
	@echo "🚀 Starting Django development environment..."
	@echo ""
	@echo "📧 Email Testing:"
	@echo "   • All emails will be captured by MailCatcher"
	@echo "   • View emails at: http://localhost:1080"
	@echo ""
	@echo "🌐 Development URLs:"
	@echo "   • Django App: http://localhost:8000"
	@echo "   • MailCatcher: http://localhost:1080"
	@echo ""
	@echo "💡 Tips:"
	@echo "   • Register for a period to test email functionality"
	@echo "   • Check MailCatcher web interface to see captured emails"
	@echo "   • Use Ctrl+C to stop the server"
	@echo "   • Run 'make clean-dev' to stop all background services"
	@echo ""
	@echo "Starting Django server..."
	python src/manage.py runserver

.PHONY: migrations
migrations:
	python src/manage.py makemigrations
	python src/manage.py migrate

.PHONY: tests-unit
tests-unit:
	pytest tests/unit --cov --cov-report term-missing
