# Investigation Timeline

This is a chronological map of the major blockers and what moved the project forward.

## Stage 1 — Retrac frontend

- Retrac 3.0.9 installed under Wine.
- Tauri/WebView2 frontend works.
- Linux custom URI handler added for the `retrac:` scheme.

Result: launcher UI/authentication usable.

## Stage 2 — Alea setup

Alea setup failed while downloading/installing `AleaService.exe`.

Evidence showed the binary itself had a valid vendor signature. Wine's trust verification failed because of file-sharing semantics.

Fix: allow `FILE_SHARE_DELETE` while opening the file for WinVerifyTrust.

Result: Alea setup succeeds without bypassing signature verification.

## Stage 3 — Alea service privilege setup

AleaService failed privilege operations involving primary-token assignment and quota privilege.

Fixes:

- `SeAssignPrimaryTokenPrivilege` LUID 3
- `SeIncreaseQuotaPrivilege` LUID 5
- expected admin-token privilege entries

Result: service proceeds and listens on `\\.\pipe\AleaAntiCheat`.

## Stage 4 — launcher OLE crash

Retrac crashed in `ole32` around `RevokeDragDrop`.

Fix: do not release a foreign-process drop-target pointer as if it belonged to the current process.

Result: Retrac remains stable.

## Stage 5 — Windows session semantics

Alea expected Windows-like session IDs and WTS behavior.

Wine MR 9843 was adapted to the Wine 11.16 tree.

Result: service/session behavior became much closer to Windows; earlier session-ID stubs disappeared.

## Stage 6 — AleaClient not-ready

Focused traces showed AleaClient querying `NtQuerySystemInformation` class `0x5a` (`SystemBootEnvironmentInformation`), which the tested Wine tree did not implement.

Applied the first commit from Wine MR 6423.

Result: major breakthrough. AleaClient signals ready and AleaService logs `Launch succeeded`.

## Stage 7 — protected wrapper fatal dialog

The wrapper still showed a deliberate fatal MessageBox.

Early hypotheses included:

- debugger/single-step handling,
- Sandboxie detection,
- missing `FlsGetValue2`,
- protected-thread enumeration,
- firmware queries,
- socket implementation.

Each was investigated.

## Stage 8 — protected-thread access

Wine server diagnostics showed protected threads exist but have explicit DACLs denying the exact query/suspend rights being requested.

Result: the `NtGetNextThread` failures in the fatal path are expected protection behavior, not missing threads.

## Stage 9 — firmware

The wrapper queried RSMB and FIRM firmware providers.

RSMB works correctly. FIRM is unsupported, which is expected on modern UEFI systems.

Result: firmware-provider behavior is not the current lead.

## Stage 10 — network breakthrough

Relay trace showed the wrapper sends final WebSocket messages and then waits in `select()`.

External packet capture independently showed:

- WebSocket upgrade succeeds.
- Earlier request/reply pairs succeed.
- Final client messages are ACKed by the remote peer.
- No application response arrives.
- The server does not close first.
- The wrapper times out and enters the fatal path.

Current status: investigate native-Windows differences in client state rather than patching networking or anti-cheat checks.
