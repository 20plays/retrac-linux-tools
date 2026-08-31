# Reproduce the Current Checkpoint

This is the canonical clean-clone path for reproducing the current Retrac/Alea
Wine checkpoint.

> **Checkpoint:** Retrac 3.0.9 and WebView2 run, Alea installs and its service
> runs, AleaClient reaches its ready signal, AleaService records a successful
> protected-game launch, and the protected Fortnite wrapper starts. The current
> investigation then reaches the known later wrapper/backend timeout and fatal
> dialog described in [docs/current-status.md](docs/current-status.md).

The goal of this document is that a real person, Codex, Claude, or another
agent can start from a fresh clone without needing private chat history.

## Important status

The repository now pins the Wine/packaging/Retrac inputs and contains the
source transformer, build script, prefix bootstrap, OAuth registration helper,
service launcher, launcher helper, and checkpoint verifier.

The procedure has **not yet been independently clean-room verified on a second
machine**. Until that happens, failures in this document are reproduction bugs
to fix, not reasons to silently improvise around the documented state.

## Supported reproduction host

The known investigation environment is Arch/CachyOS-family Linux. The build
script intentionally uses Arch's pinned `wine-staging` packaging revision.

You need:

- an Arch/CachyOS-family system with multilib enabled,
- `base-devel`, `git`, `curl`, `python`, and `sha256sum`,
- enough disk space and time to build Wine,
- a graphical desktop for Retrac/WebView2,
- network access to the public Wine/Arch/Retrac inputs,
- a legitimate Retrac account for the interactive sign-in step.

Do not put credentials, launcher command lines, WebSocket payloads, or fatal
diagnostic blobs into this repository. Read [SECURITY.md](SECURITY.md).

## 1. Fresh clone

```bash
git clone https://github.com/20plays/retrac-linux-tools.git
cd retrac-linux-tools
```

All version pins are in:

```text
repro/versions.env
```

At the current checkpoint these include Wine 11.16, a specific upstream Wine
commit, a specific Arch `wine-staging` packaging commit, Retrac 3.0.9, and the
known Retrac MSI SHA-256.

## 2. Build the pinned Wine package

The build script checks out the pinned Arch packaging revision, lets
`makepkg` prepare Wine-Staging, verifies the upstream Wine commit, applies
the repository's deterministic compatibility source transformations,
regenerates the Wine server protocol, checks the diff, and builds the package.

```bash
MAKEFLAGS="-j$(nproc)" bash scripts/build-wine-arch.sh --syncdeps
```

The script does **not** install the resulting package.

The default work directory is:

```text
~/retrac-wine-build/wine-staging
```

Verify the prepared source checkpoint:

```bash
bash scripts/verify-wine-source.sh
```

Do not manually edit the prepared Wine source if this step fails. Fix the
canonical transformer or pins in this repository instead.

## 3. Install the generated Wine package

Inspect the package path printed by the build script, then install it
explicitly:

```bash
sudo pacman -U ~/retrac-wine-build/wine-staging/wine-staging-*.pkg.tar.zst
```

Confirm the expected major checkpoint:

```bash
wine --version
```

It should report Wine Staging 11.16.

A later normal system Wine upgrade can replace this custom package. If that
happens, reinstall the generated package before comparing behavior.

## 4. Create a fresh prefix and install Retrac

The bootstrap script downloads the pinned Retrac MSI over HTTPS, verifies its
SHA-256, initializes the prefix, and runs the MSI.

Default prefix:

```text
~/Games/retrac-wine
```

Run:

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/setup-prefix.sh
```

The installer is interactive. The script does not store or request Retrac
credentials.

After a successful install the expected launcher path is:

```text
C:\Program Files\Retrac\retrac.exe
```

## 5. Register the Retrac OAuth URI handler

This creates a small per-user Linux wrapper and desktop entry, then registers
`retrac:` as the URI scheme handler.

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/register-retrac-oauth.sh
```

## 6. First launcher run and Alea installation

Launch Retrac:

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/launch-retrac.sh
```

Complete the normal interactive Retrac sign-in. Allow the launcher's normal
Alea setup flow to install its vendor files.

This is intentionally the only manual account-dependent step. Do not automate
credential entry, copy credentials into logs, or commit launcher command
lines.

When Alea has been installed, close Retrac before the clean service start in
the next step.

## 7. Start Alea cleanly and relaunch Retrac

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/start-alea-service.sh
```

Then, in another terminal:

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/launch-retrac.sh
```

Start the game through the normal launcher flow.

For the current checkpoint, leave the eventual fatal dialog open while running
the verifier.

## 8. Verify the reproduced checkpoint

```bash
WINEPREFIX="$HOME/Games/retrac-wine" bash scripts/verify-checkpoint.sh
```

The verifier checks only non-secret state:

- pinned Wine source checkpoint when the build tree is available,
- Retrac launcher installation,
- Alea service state,
- service-log markers for AleaClient ready / launch success,
- presence of the protected wrapper process.

It does not print raw service logs or protected command lines.

A successful run should end with:

```text
CHECKPOINT REPRODUCED
```

The final known wrapper/backend timeout is currently a manual observation:
after the protected wrapper starts, the current investigation reaches the
fatal dialog after the later timeout described in
[docs/current-status.md](docs/current-status.md). Packet/payload inspection is
not required to establish the base checkpoint.

## What the Wine transformer contains

The canonical compatibility transformations are in:

```text
scripts/apply-retrac-wine-11.16.py
```

They cover the compatibility work that reached the current checkpoint,
including:

- WinTrust file sharing while preserving Authenticode verification,
- the missing `SeAssignPrimaryTokenPrivilege` LUID/administrator privilege,
- the OLE `RevokeDragDrop` foreign-window lifetime fix,
- the Wine MR 9843 token/session/WTS/service semantics adapted to Wine 11.16,
- the Wine MR 6423 `SystemBootEnvironmentInformation` implementation used by
  this checkpoint.

Temporary `RETRAC ...` diagnostic logging used during investigation is not
part of the reproduction build.

## Reproduction invariant

A source edit is not considered part of this project merely because it works
in one local Wine tree.

If a new Wine compatibility change becomes required, update all applicable
parts of the repository:

1. the canonical source transformer or patch input,
2. the source/checkpoint verifier,
3. the relevant documentation,
4. the pinned versions/hashes when an input changed.

Then repeat this document from a fresh work directory.

## Known boundary

This project does not disable or bypass Alea, forge integrity/signature/hash
results, weaken deliberately restrictive ACLs, patch the protected wrapper to
skip checks, conceal Wine from deliberate detection, defeat anti-debug checks,
or fabricate backend responses.

If progress eventually depends on such behavior rather than a demonstrable
Windows compatibility semantic, that is outside this repository's scope.
