# Contributing

Issues and pull requests are welcome in English or Chinese. Keep each change focused on one problem.

## Report a problem

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include the release or commit, operating system, Python version, MCP client/editor version, reproduction steps, and expected versus actual results. For an inspection problem, include the tool input, `exit_code`, `report.status`, and a short report excerpt.

Prefer the [synthetic trial](README.md#try-the-synthetic-example) or a small redistributable input. Remove private paths and credentials, and keep customer APKs and AARs private. The synthetic trial intentionally returns `exit_code: 1` with ELF failure and ZIP success.

## Setup and checks

Use Python 3.11 or newer and keep the virtual environment outside the checkout. Follow the [setup instructions](README.md#set-up), then run these commands from the repository root with that environment's Python:

```sh
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s vendor/apk-page-size-check/tests -v
```

The stdio suite starts the server with the official Python MCP client and compares complete responses with direct CLI results on synthetic inputs. The bundled CLI suite checks generated APK and AAR fixtures.

The suites validate MCP transport and static APK analysis with synthetic inputs. Inspecting a real APK also remains static analysis. Neither verifies installation, launch or runtime on an Android device. Record any device checks separately.

## Submit a change

Describe the problem, resulting behavior, exact validation commands and results in the pull request. Identify checks not run and explain why. Add or update regression coverage when behavior changes; for documentation changes, check the affected links and commands.

Update both README files when setup or tool usage changes. Keep new fixtures synthetic or redistributable, and leave generated trial archives and local environment files out of the change.
