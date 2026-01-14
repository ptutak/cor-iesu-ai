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

.PHONY: update
update:
	@pdm update --update-all --prod

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

.PHONY: tests-integration
tests-integration:
	@echo "🔧 Running all integration tests..."
	pytest tests/integration/ -v
	@echo "✅ All integration tests completed!"

.PHONY: tests
tests:
	@echo "🧪 Running all tests (unit + integration)..."
	@echo ""
	@echo "📋 Running unit tests with coverage..."
	pytest tests/unit --cov --cov-report term-missing
	@echo ""
	@echo "🔧 Running integration tests..."
	pytest tests/integration/ -v
	@echo ""
	@echo "✅ All tests completed successfully!"

.PHONY: make-messages
make-messages:
	@echo "📝 Extracting translatable strings..."
	cd src && python manage.py makemessages -a
	@echo "✅ Translation files updated!"

.PHONY: compile-messages
compile-messages:
	@echo "🔨 Compiling translation files..."
	cd src && python manage.py compilemessages
	@echo "✅ Translation files compiled!"

.PHONY: update-translations
update-translations: make-messages compile-messages
	@echo "🌐 Translation update complete!"

.PHONY: static
static:
	@echo "🔨 Compiling static files..."
	cd src && python manage.py collectstatic --noinput
	@echo "✅ Static files compiled!"
