# Next Steps

The investigation has reached the point where more blind Wine patching is likely to waste time. The next steps should be comparative and testable.

## 1. Native Windows reference run — highest value

Use Windows 10/11 on the same physical machine if possible. A native boot is preferable to a VM because anti-cheat and hardware/platform reporting can behave differently in virtual machines.

Keep the same:

- Retrac version
- account
- physical machine
- home network

Capture the Alea backend TCP stream with Wireshark or similar tooling.

The Linux/Wine reference currently looks like:

```text
GET /ws
101 Switching Protocols

client 38 -> server 50
client 34 -> server 36
client 46 -> no application reply
client 62 -> no application reply
~25 second timeout
```

The key questions for Windows are:

1. Are the first message sizes the same?
2. Does Windows receive a response after the 46-byte or 62-byte message?
3. Does Windows send a differently-sized message at the point where Wine diverges?
4. Does the connection continue into normal game startup?

Do **not** publish WebSocket payloads or authentication headers. Packet direction, length, TCP flags, and relative timing are enough for the first comparison.

## 2. Build a standalone Windows-vs-Wine compatibility probe

If Windows succeeds where Wine stalls, create a tiny ordinary Windows executable that records the output/status of standard APIs seen in the wrapper trace.

Candidates include:

- `NtQuerySystemInformation(SystemBootEnvironmentInformation)`
- `GetFirmwareType`
- `SystemFirmwareTableInformation` for RSMB/FIRM
- process and thread basic information
- token session ID
- WTS session enumeration
- token user/groups/privileges
- relevant process/thread access checks
- computer name / username
- OS version information

Run the same binary on native Windows and this Wine build, then diff the output.

Any difference that can be independently shown to violate Windows behavior is a strong candidate for a generic Wine fix.

## 3. Validate the SeDebugPrivilege / NtGetNextThread discrepancy separately

This is probably not the current wrapper blocker, but it may be a real Wine bug.

Build a standalone test that:

1. creates a thread with a restrictive DACL,
2. tries `NtGetNextThread` without `SeDebugPrivilege`,
3. enables `SeDebugPrivilege`,
4. tries again,
5. compares native Windows and Wine.

Do not special-case Alea or Fortnite. If native Windows grants access and Wine does not, write a Wine conformance test first, then implement the generic behavior.

## 4. Compare platform data only if network sizes diverge

If the Windows packet-size sequence differs from Wine, trace backward from the differing send and identify which ordinary system properties feed that message.

Prefer passive logging and standalone API probes.

Do not:

- patch the protected wrapper,
- forge a server reply,
- weaken anti-cheat ACLs,
- alter signatures/hashes,
- conceal Wine markers,
- defeat anti-debug logic.

## 5. Upstream generic fixes

The changes most suitable for eventual Wine upstreaming are ones that can be demonstrated with small tests unrelated to Retrac.

Strong examples:

- correct file-sharing behavior during WinTrust verification,
- session/token semantics,
- missing documented/observed system-information classes,
- generic object-access behavior backed by Windows tests.

Include standalone regression tests whenever possible.

## 6. Support-staff route

The fatal popup explicitly asks the user to send its diagnostic text to staff. That is a legitimate next path.

Keep that diagnostic private and send it directly to Retrac/Alea support. Do not commit the opaque blob to this public repository.

## Definition of useful progress

A future finding is especially valuable if it gives one of these:

- a native-Windows vs Wine API result difference,
- a native-Windows vs Wine packet-size/timing divergence,
- a minimal Wine test that reproduces the discrepancy,
- an upstream Wine commit/MR that fixes the exact behavior,
- a server-side diagnostic from Retrac/Alea staff identifying a Windows compatibility assumption.
