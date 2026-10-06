# Contributing

[Deutsch](CONTRIBUTING.de.md) · [Project README](README.md)

Contributions are welcome in English and German. Please keep discussions
respectful, specific and focused on the change.

## Report a problem

Use the bug report template if the project is hosted on GitHub. Include the
application version (`python app.py --version`), Python/Git versions, operating
system, reproduction steps and expected versus actual behavior. Reduce Git
problems to disposable repositories when possible. Remove credentials and
personal repository paths from shared logs.

Use the feature-request template to describe the workflow and desired result.

## Make a change

1. Create a branch for the change in your checkout.
2. Keep application code under `src/git_repo_manager/`, tests under `tests/`
   and supporting developer commands under `scripts/`.
3. Keep runtime dependencies in the standard library unless the feature provides
   a clear reason for adding a package.
4. Run the relevant tests and `python scripts/check_docs.py`. For changes to the
   Git backend or UI, also run `python scripts/test.py` in a graphical session.
5. Update English and German documentation together and add a change-log entry.
6. Explain the behavior change, validation and any remaining limitations in the PR.

Keep Git operations explicit. Preserve fast-forward-only Pull and branch-scoped
Push unless a reviewed feature deliberately changes their user-facing behavior.
Keep Tk calls on the main thread. Tests must use temporary repositories and local
remotes, with no network access or changes to a contributor's projects.

Do not commit user settings, credentials, build artifacts or virtual environments.
The [development guide](docs/en/development.md) explains setup, builds and releases.

## License

By submitting a contribution, you agree to distribute it under the project's
[MIT License](LICENSE). Keep third-party notices with any code that requires them.
