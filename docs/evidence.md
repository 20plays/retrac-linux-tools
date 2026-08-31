# Diagnostic Evidence

This file preserves the most useful **redacted, non-secret** excerpts from the investigation so future contributors do not have to rediscover the same facts.

Process/thread IDs are examples from individual runs and are not stable.

## AleaService success after session + boot-environment fixes

```text
Started Alea client suspended
Started game suspended
Exchanging process handles
Resuming Alea client
Waiting for Alea client to signal ready
Alea client signaled ready (about 1.6s in one run)
Resuming game
Launch succeeded
Request completed successfully
```

This is the strongest evidence that AleaService and AleaClient startup are no longer the current blocker.

## Session layout observed with tasklist

A representative run showed:

```text
services.exe                    Services  session 0
winedevice.exe                 Services  session 0
AleaService.exe                Services  session 0

explorer.exe                   Console   session 1
retrac.exe                     Console   session 1
msedgewebview2.exe             Console   session 1
AleaClient.exe                 Console   session 1
FortniteClient-Win64-Shipping  Console   session 1
```

This matches the intended service-vs-interactive split much better than the pre-MR-9843 state.

## Standalone NtGetNextThread sanity test

A helper calling `NtGetNextThread` on its own ordinary process showed:

```text
access=0x0000 status=0x8000001a handle=0
access=0x0002 status=SUCCESS    handle=<valid>
access=0x0800 status=SUCCESS    handle=<valid>
access=0x0802 status=SUCCESS    handle=<valid>
```

Important detail: access 0 fails because Wine's handle allocator rejects a zero-access handle. The exact wrapper mask `0x0802` succeeds for ordinary threads.

Conclusion: the generic enumeration loop can find ordinary threads.

## Cross-process protected-thread test

While the protected wrapper was alive, an external helper could enumerate its thread ID via Toolhelp but could not open it:

```text
Toolhelp: protected thread is visible

OpenThread access=0x0000 -> failure / access denied
OpenThread access=0x0002 -> failure / access denied
OpenThread access=0x0800 -> failure / access denied
OpenThread access=0x0802 -> failure / access denied

OpenProcess(PROCESS_QUERY_INFORMATION) -> access denied
```

This also explained why WineDbg reported error 5. It was a Wine object-security denial, not merely Linux Yama/ptrace policy.

## Wine-server security-descriptor diagnostics

Protected process creation supplied explicit thread security descriptors.

Representative token:

```text
user          S-1-5-21-0-0-0-1000
owner         S-1-5-21-0-0-0-513
primary group S-1-5-21-0-0-0-513

groups include:
S-1-1-0          Everyone
S-1-2-0
S-1-5-4
S-1-5-11
S-1-5-21-0-0-0-513
S-1-5-32-544
S-1-5-32-545
S-1-5-5-0-0
```

Representative incoming thread DACL:

```text
ACE type=DENY  flags=0 mask=0x00000eba SID=S-1-1-0
ACE type=ALLOW flags=0 mask=0x10000000 SID=S-1-1-0
```

The failed wrapper request was:

```text
NtGetNextThread(... desired_access=0x0802 ...)
-> Wine server alloc_handle()
-> STATUS_ACCESS_DENIED
-> enumeration eventually returns STATUS_NO_MORE_ENTRIES
```

The DACL explicitly denies Everyone the requested query/suspend rights before the generic allow ACE, so the denial is expected.

## SeDebugPrivilege observation

One protected process had:

```text
se_debug_enabled=1
desired_access=0x0800
-> STATUS_ACCESS_DENIED
```

The wrapper process later executing the fatal path had:

```text
se_debug_enabled=0
desired_access=0x0800 / 0x0802
-> STATUS_ACCESS_DENIED
```

This means a possible generic `SeDebugPrivilege` difference in Wine is worth testing independently, but it cannot by itself explain the wrapper's fatal path.

## Firmware provider diagnostics

Observed `SystemFirmwareTableInformation` calls:

```text
RSMB action=0, small buffer -> STATUS_BUFFER_TOO_SMALL
RSMB action=0, sized buffer -> STATUS_SUCCESS

RSMB action=1, small buffer -> STATUS_BUFFER_TOO_SMALL
RSMB action=1, sized buffer -> STATUS_SUCCESS

FIRM action=0 -> STATUS_NOT_IMPLEMENTED
```

Observed RSMB table length in the tested environment was roughly 0x22b bytes, with required caller buffer around 0x23b bytes.

The temporary logger printed integer FourCC bytes in reverse-looking order:

```text
0x52534d42 = RSMB
0x4649524d = FIRM
```

RSMB is therefore functioning. FIRM is not a compelling issue on UEFI.

## Wrapper startup probes

The wrapper performed:

```text
NtQueryInformationProcess(ProcessDebugPort) -> success
NtQueryInformationProcess(ProcessDebugObjectHandle) -> status indicating no debug object
single-step exception probes -> handled
GetModuleHandle("sbiedll.dll") -> not found
```

No evidence currently ties these normal protection probes to the final failure.

## FlsGetValue2 fallback

The runtime asks for:

```text
GetProcAddress(..., "FlsGetValue2") -> not found
```

It then uses ordinary FLS calls successfully:

```text
FlsAlloc -> success
FlsGetValue -> success
FlsSetValue -> success
```

This is not currently considered the blocker.

## Backend connection establishment

The wrapper resolves:

```text
alea-service-prod.retr.ac
port 80
```

The socket is nonblocking. Representative sequence:

```text
connect() -> SOCKET_ERROR
WSAGetLastError() -> WSAEWOULDBLOCK
select(write/except sets) -> ready
getsockopt(SO_ERROR) -> success
```

The connection then proceeds normally.

## WebSocket exchange

Packet capture and Wine relay agree on:

```text
GET /ws HTTP/1.1
HTTP/1.1 101 Switching Protocols

client -> 38 bytes
server -> 50 bytes

client -> 34 bytes
server -> 36 bytes

client -> 46 bytes
server -> TCP ACK only

client -> 62 bytes
server -> TCP ACK only
```

Then there is roughly 25 seconds with no application data from the server.

## Final wait

The wrapper calls Winsock `select()` on the socket's read set.

Wine's AFD operation goes pending, waits, completes normally, and `select()` returns:

```text
0
```

That means timeout/no readable socket, not API failure.

## External TCP capture

A representative capture showed:

```text
SYN
SYN/ACK
ACK
GET /ws
ACK
101 Switching Protocols
ACK

application request/reply traffic

final client application packet
server ACK

final client application packet
server ACK

~26 seconds silence

client FIN
server FIN
client ACK
```

Crucially, the server did not FIN/RST first. The client initiated close after entering its error path.

## Fatal path after timeout

Only after the network wait expires does the wrapper perform operations such as:

```text
random-data generation
NtGetNextThread(...)
NtSuspendProcess(companion)
NtGetNextThread(companion,...)
MessageBoxW(...)
```

The dialog is deliberate, not a crash.

The opaque diagnostic text from the popup is intentionally omitted from this public repository.
