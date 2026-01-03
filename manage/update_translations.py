#!/usr/bin/env python
"""
Script to update translations for the multilingual adoration registration system.
This script helps maintain and update translation files for Polish and Dutch.
"""

import os
import subprocess
import sys


def run_command(command, cwd=None):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, cwd=cwd)
        print(f"✓ {command}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error running: {command}")
        print(f"Error: {e.stderr}")
        return False


def update_translations():
    """Update translation files for all supported languages."""

    print("Updating translations for the multilingual adoration app...")
    print("=" * 60)

    # Change to the src directory where manage.py is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level from manage/ to project root, then into src/
    project_root = os.path.dirname(script_dir)
    src_dir = os.path.join(project_root, "src")

    if not os.path.exists(os.path.join(src_dir, "manage.py")):
        print(f"Error: manage.py not found in {src_dir}")
        print(f"Script is running from: {script_dir}")
        print(f"Looking for manage.py in: {src_dir}")
        sys.exit(1)

    # Languages to update
    languages = ["pl", "nl"]

    print("Step 1: Extracting translatable strings...")

    # Extract messages for each language
    for lang in languages:
        print(f"\nExtracting messages for {lang}...")
        success = run_command(f"python manage.py makemessages -l {lang}", cwd=src_dir)
        if not success:
            print(f"Failed to extract messages for {lang}")
            continue

    print("\nStep 2: Compiling translation files...")

    # Compile all messages
    success = run_command("python manage.py compilemessages", cwd=src_dir)

    if success:
        print("\n🎉 Translation update completed successfully!")
        print("\nNext steps:")
        print("1. Review the .po files in src/locale/*/LC_MESSAGES/ for any new strings")
        print("2. Add translations for any empty msgstr entries")
        print("3. Run this script again to compile the updated translations")
        print("4. Test the application in different languages")

        print(f"\nTranslation files location:")
        for lang in languages:
            lang_name = "Polish" if lang == "pl" else "Dutch"
            print(f"- {lang_name}: src/locale/{lang}/LC_MESSAGES/django.po")
    else:
        print("\n❌ Translation compilation failed!")
        sys.exit(1)


def check_translations():
    """Check if all translation files are properly compiled."""

    print("Checking translation files...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level from manage/ to project root, then into src/
    project_root = os.path.dirname(script_dir)
    src_dir = os.path.join(project_root, "src")

    languages = ["pl", "nl"]

    all_good = True

    for lang in languages:
        po_file = os.path.join(src_dir, "locale", lang, "LC_MESSAGES", "django.po")
        mo_file = os.path.join(src_dir, "locale", lang, "LC_MESSAGES", "django.mo")

        lang_name = "Polish" if lang == "pl" else "Dutch"

        if os.path.exists(po_file):
            print(f"✓ {lang_name} translation source file exists")
        else:
            print(f"✗ {lang_name} translation source file missing: {po_file}")
            all_good = False

        if os.path.exists(mo_file):
            print(f"✓ {lang_name} compiled translation file exists")
        else:
            print(f"✗ {lang_name} compiled translation file missing: {mo_file}")
            all_good = False

    if all_good:
        print("\n✅ All translation files are present!")
    else:
        print("\n⚠️  Some translation files are missing. Run the update command.")

    return all_good


def show_usage():
    """Show script usage information."""
    script_name = os.path.basename(__file__)
    print(
        f"""
Translation Management Script

Usage: python manage/{script_name} [command]

Commands:
    update    Extract and compile translations (default)
    check     Check if translation files exist
    help      Show this help message

Examples:
    python manage/{script_name}          # Update translations
    python manage/{script_name} update   # Update translations
    python manage/{script_name} check    # Check translation files

Location: Run from project root directory
Purpose:  Manages Django i18n translation files

Supported languages:
    🇺🇸 English (en) - default language
    🇵🇱 Polish (pl)
    🇳🇱 Dutch (nl)

What this script does:
    1. Extracts translatable strings from templates, forms, and views
    2. Updates .po files in src/locale/*/LC_MESSAGES/
    3. Compiles .po files to .mo files for Django to use
    4. Checks translation file integrity

Translation files location:
    - Polish:  src/locale/pl/LC_MESSAGES/django.po
    - Dutch:   src/locale/nl/LC_MESSAGES/django.po

After running this script:
    1. Edit the .po files to add/update translations
    2. Run the script again to compile changes
    3. Test your app with different languages
    """
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "check":
            check_translations()
        elif command == "help":
            show_usage()
        elif command == "update":
            update_translations()
        else:
            print(f"Unknown command: {command}")
            show_usage()
            sys.exit(1)
    else:
        # Default action is to update translations
        update_translations()
