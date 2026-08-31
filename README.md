# Retrac Linux Tools

Community research and compatibility tooling for running Retrac's Fortnite launcher stack under Wine on Linux.

> **Current status:** Retrac itself and WebView2 run, Alea installs and starts, AleaClient reaches its ready signal, and AleaService reports a successful protected-game launch. The remaining blocker is later: the protected Fortnite wrapper completes a WebSocket handshake with the Alea backend, exchanges several messages, then sends two final messages that receive TCP ACKs but no application response. After roughly 25 seconds the wrapper times out and deliberately shows its fatal-error dialog.

This repository collects the findings, reproducible diagnostics, Wine compatibility patches already identified, and the safest next experiments. It is **not** an anti-cheat bypass project.

## Start here

- **[Clean-clone reproduction guide](REPRODUCE.md)** — canonical path for people and coding agents
- **[Agent instructions](AGENTS.md)** — reproduction-first rules for Codex/Claude/other agents
- [Current status and strongest findings](docs/current-status.md)
- [Redacted diagnostic evidence](docs/evidence.md)
- [Investigation timeline](docs/investigation-timeline.md)
- [Wine patches and source history](docs/wine-patches.md)
- [Investigation notes / ruled-out leads](docs/findings.md)
- [Next steps](docs/next-steps.md)
- [Native Windows reference test](docs/windows-reference.md)
- [Reproduction and logging commands](docs/reproduction.md)
- [Patch contribution notes](patches/README.md)
- [Security / redaction rules](SECURITY.md)

## Known-good test environment

The investigation so far used:

- Wine Staging 11.16, locally built from the Arch/CachyOS `wine-staging` PKGBUILD
- Prefix: `/home/sprite/Games/retrac-wine`
- Retrac 3.0.9
- AMD/RADV graphics
- Linux host with a modern UEFI system
- Retrac frontend: Tauri + WebView2

Paths in this repository are examples from that test environment. Change them to match your own installation.

## High-level progress

1. Retrac launches under Wine and WebView2 works.
2. Retrac OAuth custom-protocol handling works.
3. Alea setup was fixed without weakening signature verification.
4. Alea service-token privilege semantics were corrected.
5. A Wine OLE drag/drop crash affecting the launcher was fixed.
6. Wine session semantics from MR 9843 were adapted to Wine 11.16.
7. `SystemBootEnvironmentInformation` support was added from Wine MR 6423.
8. **Breakthrough:** AleaClient now signals ready; AleaService resumes the game and records `Launch succeeded`.
9. The remaining protected wrapper reaches the Alea backend over WebSocket, but the backend stops sending application data after the final client messages.
10. Packet capture confirms the timeout is real: Wine is not hiding queued socket data, and the remote peer does not close first.

## Helper scripts

The `scripts/` directory contains helpers for:

- building the pinned Wine Staging 11.16 package from a fresh clone,
- verifying the resulting Wine source checkpoint,
- creating a fresh Wine prefix and installing the pinned Retrac MSI,
- registering the `retrac:` OAuth URI handler,
- starting the Alea service with a persistent wineserver,
- launching Retrac,
- verifying the established end-to-end checkpoint without printing secrets,
- capturing TCP timing/headers,
- extracting the wrapper thread that reaches the fatal MessageBox from a relay trace.

They intentionally avoid dumping or interpreting protected protocol payloads.

## Scope

Useful contributions are welcome when they improve Windows compatibility, diagnostics, documentation, or reproducibility.

Please do **not** submit changes that:

- disable or bypass Alea / anti-cheat checks,
- fake signature or hash verification,
- weaken protected-object ACLs,
- forge expected network responses,
- patch the protected game wrapper to skip checks,
- conceal Wine from software that deliberately checks for it,
- attempt to emulate or bypass a required Windows kernel anti-cheat driver.

The goal is to make Wine behave more like Windows where a legitimate compatibility discrepancy can be demonstrated.

## Repository state

This repo intentionally does **not** contain captured authentication tokens, launcher passwords, WebSocket payloads, fatal diagnostic blobs, or other live credentials. Some launcher command lines and raw traces can contain those values.

See [SECURITY.md](SECURITY.md) before sharing logs.
