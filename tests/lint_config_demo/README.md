# Lint Config Demo

This directory simulates a project root for testing the OSED linter's acknowledgement and unacknowledgement system.

- `.osed/config.yaml` acknowledges the sensitive field warning for `clean_valid.yaml` (Person.password).
- `clean_valid.yaml` is a test file local to this environment.

## New CLI Features

- You can now acknowledge or unacknowledge warnings using:
  - `osed lint acknowledge --kind sensitiveFields --path tests/lint_config_demo/clean_valid.yaml#Person.password --user test-user`
  - `osed lint unacknowledge --kind sensitiveFields --path tests/lint_config_demo/clean_valid.yaml#Person.password --user test-user`
- Add `--global` to operate on user config (`~/.osed/config.yaml`).

When running the linter with this directory as the working directory, the warning for Person.password should be downgraded to info if the acknowledgement logic is working correctly, and restored to warning if unacknowledged.
