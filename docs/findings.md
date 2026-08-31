# Findings and Ruled-Out Leads

This is the condensed investigation record. The goal is to keep future work from repeating dead ends.

## Versions and artifacts

Retrac version under test:

```text
3.0.9
```

Observed Retrac installer URL:

```text
https://cdn.retrac.site/launcher_patches/Retrac_3.0.9_x64_en-US.msi
```

Original downloaded `AleaService.exe` SHA-256 observed during setup:

```text
cc8a15025d4aa409d7d82569088949dafb7cd0f8e23770959ec6f89f8e0a67d3
```

The downloaded binary had a valid signature from Lezah Limited.

## Retrac / WebView2

Retrac 3.0.9 is a Tauri application using WebView2. WebView2 itself works under the tested Wine prefix. The launcher UI and authentication flow are therefore not the current blocker.

## Alea installer and Authenticode

The Alea setup initially failed with a download/install error for `AleaService.exe`. The downloaded binary was genuinely signed. The failure was caused by Wine opening the file for trust verification without compatible sharing while another handle had delete access.

Adding `FILE_SHARE_DELETE` to the verification file sharing fixed setup while preserving the real signature verification.

Conclusion: **not a signature bypass issue**.

## Alea service privileges

AleaService needed standard Windows token privileges. Correcting `SeAssignPrimaryTokenPrivilege` to LUID 3 and ensuring the expected administrative privileges were represented allowed service startup to proceed.

## Service state

Alea can be kept alive with a persistent wineserver and started using:

```bash
WINEPREFIX="$P" wineserver -p
WINEPREFIX="$P" wine sc start AleaAntiCheat
```

The service listens on:

```text
\\.\pipe\AleaAntiCheat
```

## Session behavior

Windows service/session semantics mattered. Wine MR 9843 was highly relevant:

- services in session 0
- interactive console session
- token session IDs
- WTS session enumeration
- process window-station attachment

After adapting these changes, the earlier session-ID stub disappeared.

## Boot environment query

AleaClient queried `NtQuerySystemInformation` class `0x5a`, which is `SystemBootEnvironmentInformation`.

Wine 11.16 did not provide the expected implementation in the tested tree. Applying the first commit from Wine MR 6423 fixed this.

This was the key change that moved AleaClient from not-ready to:

```text
Alea client signaled ready
Resuming game
Launch succeeded
```

## Deliberate anti-debug / protection probes

The wrapper performs deliberate single-step exception probes and debugger-related queries such as:

- `ProcessDebugPort`
- `ProcessDebugObjectHandle`
- thread information changes

These probes are handled and are not, by themselves, evidence of a Wine bug.

The wrapper also checks for `sbiedll.dll` (Sandboxie); it is absent. That is expected and not correlated with the final failure.

Do not patch or defeat these checks.

## FlsGetValue2

The wrapper/runtime asks for `FlsGetValue2`, which Wine 11.16 does not export in this path. The trace then falls back to `FlsGetValue`, which succeeds.

Conclusion: **not currently a compelling blocker**.

## NtGetNextThread and protected-thread ACLs

An important false lead was `NtGetNextThread` returning `STATUS_NO_MORE_ENTRIES`.

Standalone testing showed Wine's implementation works for ordinary processes with the exact requested access mask `0x0802`:

- `THREAD_QUERY_LIMITED_INFORMATION` = `0x0800`
- `THREAD_SUSPEND_RESUME` = `0x0002`

The protected processes are different because their initial threads have explicit security descriptors.

Creation-time diagnostics showed an incoming DACL equivalent to:

```text
DENY  Everyone  mask=0x00000eba
ALLOW Everyone  mask=0x10000000 (GENERIC_ALL)
```

The caller token contains Everyone (`S-1-1-0`), so the deny ACE correctly wins for the requested protected rights.

That means the access denial is intentional protection behavior, not evidence that Wine lost the thread.

### Separate SeDebugPrivilege observation

One protected process had `SeDebugPrivilege` enabled and Wine still denied `NtGetNextThread` access. Older Windows kernel source indicates `NtGetNextThread` may special-case enabled `SeDebugPrivilege`.

That may be a legitimate generic Wine semantic discrepancy worth testing separately, but it is **not the current wrapper blocker**, because the wrapper process executing the fatal path did not have `SeDebugPrivilege` enabled.

Do not weaken the DACL as a workaround.

## Firmware tables

The wrapper queries `SystemFirmwareTableInformation` (class `0x4c`).

Observed providers:

- `RSMB` — working
- `FIRM` — returns `STATUS_NOT_IMPLEMENTED`

The logger printed the FourCC backwards when showing raw integer bytes because the integer is little-endian:

```text
0x52534d42 = RSMB
0x4649524d = FIRM
```

RSMB enumeration and retrieval both follow the expected buffer-sizing pattern and succeed:

```text
RSMB action=0: STATUS_BUFFER_TOO_SMALL -> SUCCESS
RSMB action=1: STATUS_BUFFER_TOO_SMALL -> SUCCESS
```

The FIRM provider is not expected on modern UEFI Windows systems, so this is not a useful lead by itself.

## Wine-internal environment variables

Do not interpret every `WINE...` environment lookup as anti-Wine detection.

For example, Wine's own `GetUserNameW()` implementation uses `WINEUSERNAME`. Likewise `WINEUNIXCP` can appear as an internal Wine implementation detail.

## Wrapper network behavior

The wrapper resolves:

```text
alea-service-prod.retr.ac:80
```

It uses a nonblocking Winsock connection. The initial `connect()` returns the expected would-block condition, then `select()` and `getsockopt()` confirm connection completion.

It performs an HTTP WebSocket upgrade:

```text
GET /ws HTTP/1.1
HTTP/1.1 101 Switching Protocols
```

The observed application-direction sizes were:

```text
client -> 38
server -> 50

client -> 34
server -> 36

client -> 46
server -> ACK only

client -> 62
server -> ACK only
```

After the final message, the wrapper calls `select()` for readability. Wine's underlying AFD request waits normally and returns no readable event; Winsock `select()` returns 0.

External `tcpdump` independently confirmed that the server sent no application response during this period.

Roughly 25 seconds later, the wrapper enters its fatal path.

## Fatal path

After the real network timeout, the wrapper performs cleanup/diagnostic/protection operations including:

- random-data generation
- `NtGetNextThread`
- `NtSuspendProcess`
- additional thread enumeration
- `MessageBoxW`

The MessageBox is deliberate. There is no crash at this point.

The popup contains an opaque diagnostic blob intended for support staff. This repository does not attempt to decode it.

## What the packet capture proved

The remote server ACKed the final client messages. Therefore:

- the packets reached the remote peer,
- TCP transport did not silently drop the final messages,
- Wine did not falsely report a timeout while application data was already queued,
- the server did not send FIN/RST before the timeout,
- the wrapper eventually initiated connection close.

That shifts the investigation toward **client state / request contents / Windows-visible platform differences**, not basic Wine networking.
