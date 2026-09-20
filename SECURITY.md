# Security Policy

## Scope

This repository is a Python package and research harness. It runs **no server or
network service by default** and contains **no secrets**. The only outbound network
calls happen when you explicitly opt into the **live Jev backend**, which sends game
state to the TypeSafe API (`https://api.typesafe.ai`) using a key you provide.
Everything else — the offline backend, tests, CI, the terminal and web viewers —
runs locally with no network access.

The practical risks are (a) a bug in the code, and (b) mishandling of your TypeSafe
API key.

## Handling your API key

- Set `TYPESAFE_API_KEY` via your environment or a local `.env` (git-ignored). The
  committed `.env.example` is a template with no secret in it.
- Never commit a real key, and never paste a key into an agent session, an issue,
  or a pull request.
- Keys are read only by the live backend and sent only to the TypeSafe API. They
  are never written to run artifacts, logs, or the exported web viewer.

## Reporting a vulnerability

Please report privately using GitHub's **"Report a vulnerability"** button on the
repository's **Security** tab (Security Advisories). Do **not** open a public issue
for security reports. We aim to respond promptly and will credit reporters who wish
to be credited.
