# Wine Patches and Source History

This document records the Wine changes that were needed to reach the current state. It is intentionally descriptive rather than an Alea-specific bypass patchset.

The local Wine source used during the investigation was:

```text
~/retrac-wine-build/wine-staging/src/wine
```

The Arch/CachyOS package build root was:

```text
~/retrac-wine-build/wine-staging
```

Typical build command:

```bash
MAKEFLAGS="-j24" makepkg -e -f --nocheck
```

Generated package:

```text
wine-staging-11.16-1-x86_64.pkg.tar.zst
```

## 1. WinVerifyTrust sharing semantics

### Symptom

Alea setup downloaded `AleaService.exe`, but Wine's Authenticode verification failed because the downloaded file was still open elsewhere with delete access.

### Change

In `dlls/wintrust/softpub.c`, the file used for verification was opened with sharing that includes delete access:

```c
FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
```

This preserves real signature verification. It does **not** skip or fake a signature/hash result.

### Result

Alea setup proceeded while still validating the actual signed executable.

---

## 2. Token privilege LUID correction

### Symptom

AleaService failed privilege setup involving:

- `SeAssignPrimaryTokenPrivilege`
- `SeIncreaseQuotaPrivilege`

### Change

The local server privilege constants included:

```c
static const struct luid SeAssignPrimaryTokenPrivilege = { 3, 0 };
const struct luid SeIncreaseQuotaPrivilege = { 5, 0 };
```

and the administrative token privilege list included both privileges.

### Result

The service privilege checks succeeded and AleaService could progress.

---

## 3. OLE RevokeDragDrop foreign-HWND guard

### Symptom

Retrac previously crashed inside `ole32` during `RevokeDragDrop`, apparently releasing a drop-target pointer associated with a foreign-process window.

### Change

The compatibility fix only releases the stored `IDropTarget` for windows owned by the current process, then removes the properties:

```c
DWORD pid = 0;

GetWindowThreadProcessId(hwnd, &pid);
if (pid == GetCurrentProcessId())
{
    drop_target = GetPropW(hwnd, prop_oledroptarget);
    if (drop_target) IDropTarget_Release(drop_target);
}

RemovePropW(hwnd, prop_oledroptarget);
RemovePropW(hwnd, prop_marshalleddroptarget);
```

### Result

The launcher OLE crash disappeared.

---

## 4. Wine MR 9843: session semantics

Reference:

- Mailing-list thread: <https://list.winehq.org/hyperkitty/list/wine-gitlab%40list.winehq.org/thread/GHZZJ2RMXLAW7W3DSIZU2FLLEJWXJIPK/>
- Patch: <https://gitlab.winehq.org/wine/wine/-/merge_requests/9843.patch>

The six logical changes were:

1. server: allow changing session ID for process tokens
2. WTSQueryUserToken: return a token with the correct session ID
3. winstations: attach to sessions and filter enumeration
4. WTSEnumerateSessions: return Console + Service sessions
5. services: start services with session ID 0
6. connect_process_winstation: allow desktop overwrite where required

The current Wine 11.16 source needed manual conflict adaptation in `server/winstation.c`, and server protocol files were regenerated with:

```bash
./tools/make_requests
```

Known local history from the investigation:

```text
4cf7f09f824 Save current Retrac Wine compatibility state
3302aaff1d2 Regenerate server protocol for session ID support
81a58cbac0e server: Let connect_process_winstation overwrite the desktop if needed
998c8a258a7 services: start services with session id 0
```

A preserved local branch was named approximately:

```text
retrac-mr9843-151708
```

### Result

The prior `TokenSessionId stub!` path disappeared and service/console session behavior became Windows-like enough for Alea to continue.

---

## 5. Wine MR 6423, commit 1: SystemBootEnvironmentInformation

Reference:

- Mailing-list thread: <https://list.winehq.org/hyperkitty/list/wine-gitlab%40list.winehq.org/thread/UJXAUCFLM4Z35ZMF6SHK4DALR7GYSL7I/>
- Patch: <https://gitlab.winehq.org/wine/wine/-/merge_requests/6423.patch>

Only the first logical commit was applied initially for isolation:

```text
ntdll: Implement NtQuerySystemInformation SystemBootEnvironmentInformation.
```

Known local commit:

```text
f1a31f4ec42 ntdll: Implement NtQuerySystemInformation SystemBootEnvironmentInformation.
```

### Result

This was the breakthrough change: AleaClient began signaling ready in roughly 1.5-2 seconds and AleaService resumed the wrapper.

The other MR 6423 commits were deliberately not pulled in at that stage because the goal was to identify the minimum compatibility fix.

---

## 6. Diagnostic-only instrumentation

Several temporary diagnostics were later added to Wine while investigating the remaining wrapper failure. These are **not required compatibility patches** and should not be treated as production changes.

They logged:

- `NtGetNextThread` candidates and access results
- effective token pointers
- whether `SeDebugPrivilege` was enabled
- thread security descriptors and ACEs
- token user/owner/group SIDs
- explicit thread SDs at creation time
- `SystemFirmwareTableInformation` provider/action/status

These diagnostics proved several earlier hypotheses wrong; see [findings.md](findings.md).

## Important maintenance note

The package remains named like a normal `wine-staging-11.16-1` build. A normal distro Wine upgrade can overwrite it. Keep the source branch/commits or export patches before upgrading.
