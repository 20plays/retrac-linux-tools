# AGENTS.md

## Mission

Your first task in this repository is **reproduction, not new investigation**.

Start from [REPRODUCE.md](REPRODUCE.md) and reproduce the documented checkpoint
exactly. Do not invent new Wine patches, chase new hypotheses, or reinterpret
the current blocker until the checkpoint verifier passes or you have isolated
a concrete bug in the reproduction path itself.

If reproduction is broken, fixing reproduction takes priority over research.

## Required reading order

Before changing code, read:

1. [REPRODUCE.md](REPRODUCE.md)
2. [docs/current-status.md](docs/current-status.md)
3. [docs/evidence.md](docs/evidence.md)
4. [docs/wine-patches.md](docs/wine-patches.md)
5. [docs/findings.md](docs/findings.md)
6. [docs/next-steps.md](docs/next-steps.md)
7. [SECURITY.md](SECURITY.md)

Do not rely on private conversation history to fill gaps. If an essential step
exists only in someone's memory, add it to the repository.

## Reproduction acceptance criterion

The baseline is reproduced when a fresh-clone run reaches all of the following:

- the pinned Wine 11.16 source checkpoint verifies,
- the generated Wine package builds,
- Retrac 3.0.9 is installed in a fresh prefix,
- Retrac/WebView2 launches,
- Alea is installed through the normal vendor flow,
- `AleaAntiCheat` is running,
- AleaClient reaches its ready signal,
- AleaService records `Launch succeeded`,
- the protected Fortnite wrapper starts,
- the run reaches the same later known timeout/fatal-dialog state documented in
  `docs/current-status.md`.

Use:

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/verify-checkpoint.sh
```

while the current fatal dialog is still open.

The final fatal-dialog observation is currently manual; do not add invasive
protected-process instrumentation merely to automate that last visual check.

## Canonical build state

Pinned inputs live in:

```text
repro/versions.env
```

The canonical Wine transformation is:

```text
scripts/apply-retrac-wine-11.16.py
```

The canonical build path is:

```bash
bash scripts/build-wine-arch.sh --syncdeps
bash scripts/verify-wine-source.sh
```

Do not make a one-off edit under
`~/retrac-wine-build/wine-staging/src/wine` and call the repository fixed.
Prepared Wine source is disposable build output.

If a legitimate source change is required, encode it in the repository so a
fresh clone can regenerate it.

## Rules for Wine compatibility changes

A Wine change is acceptable only when it is explainable as implementing or
correcting Windows-compatible behavior.

Prefer this evidence order:

1. a native Windows observation or test,
2. Windows/API documentation,
3. an upstream Wine patch/MR/test,
4. a minimal standalone test that distinguishes Windows behavior from Wine.

For each new compatibility change, preserve a generic explanation and, where
practical, a regression test or verifier check.

Do not add application-name-specific exceptions when the underlying Windows
semantic can be implemented generically.

## Hard project boundary

Do not:

- disable or bypass Alea or another anti-cheat component,
- fake a successful signature, hash, integrity, or anti-cheat result,
- forge expected WebSocket/backend responses,
- weaken protected-object ACLs just to make a protected process accessible,
- patch the protected Fortnite wrapper to skip checks,
- hide or spoof Wine solely to defeat deliberate environment detection,
- defeat anti-debugging checks,
- decode or publish opaque fatal diagnostic blobs,
- emulate or bypass a required Windows kernel anti-cheat driver.

Passive compatibility diagnostics and generic Windows-semantic fixes are in
scope.

## Sensitive-data handling

Raw launcher traces can contain live-looking credentials.

Never commit or quote:

- authentication passwords,
- exchange codes,
- bearer/JWT-style tokens,
- cookies or Authorization headers,
- complete protected-wrapper command lines,
- WebSocket payload bodies,
- opaque fatal diagnostic blobs.

Prefer API names, statuses, timings, packet lengths/directions, redacted
service markers, and hashes of public binaries.

If you encounter an unredacted credential in local material, do not reproduce
it in notes, commits, issue text, or model output.

## Investigation discipline after reproduction

Only after the baseline is reproduced:

- work from the strongest current evidence in `docs/current-status.md`,
- check `docs/findings.md` before reopening a ruled-out lead,
- make one compatibility hypothesis test at a time,
- keep diagnostics behavior-preserving,
- distinguish observation from inference,
- update the repository whenever a conclusion changes.

Do not decode protected protocol payloads or synthesize server behavior. Packet
direction, length, timing, ordinary API behavior, and native-Windows
comparisons are sufficient for the current research plan.

## Documentation/commit expectations

A meaningful checkpoint change should update the corresponding documentation
in the same work:

- `docs/current-status.md` for the active blocker,
- `docs/evidence.md` for durable redacted evidence,
- `docs/findings.md` for ruled-in/ruled-out hypotheses,
- `docs/investigation-timeline.md` for major milestones,
- `REPRODUCE.md` and verifier scripts if the reproduction path changed.

Keep commits coherent and descriptive. Do not commit build products, raw
sensitive traces, Wine prefixes, or authentication material.

## When handing the repo to another agent/person

The handoff must be repository-complete. The recipient should be able to
answer these questions without private context:

- Which exact inputs are pinned?
- How do I build the Wine package?
- How do I create a fresh prefix?
- Which step requires interactive authentication?
- How do I start the service and launcher?
- How do I know I reached the established checkpoint?
- What is the current blocker?
- Which hypotheses have already been ruled out?
- Which safety/redaction boundaries must not be crossed?

If any answer requires chat history, fix the repository before continuing.
