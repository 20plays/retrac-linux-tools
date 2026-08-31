# Native Windows Reference Test

This is currently the highest-value next experiment.

The purpose is **not** to inspect or reverse the protected protocol. We only need a native Windows baseline for packet direction, length, and timing, plus ordinary OS state.

## Preferred setup

Use the same physical PC if possible:

- same Retrac version,
- same account,
- same home network,
- native Windows 10/11 rather than a VM.

A spare SSD or temporary Windows install is ideal because virtualization can change hardware and anti-cheat behavior.

## Before launching Retrac

Record basic Windows state:

```powershell
Get-ComputerInfo |
  Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, BiosFirmwareType

whoami /user
whoami /groups
```

Resolve the backend:

```powershell
Resolve-DnsName alea-service-prod.retr.ac
```

## Packet capture

In Wireshark, capture the active network interface with:

```text
tcp port 80
```

Start capture before pressing Play.

Find the connection containing:

```text
GET /ws HTTP/1.1
```

The Wine reference is:

```text
client -> GET /ws
server -> 101 Switching Protocols

client -> 38 bytes
server -> 50 bytes

client -> 34 bytes
server -> 36 bytes

client -> 46 bytes
server -> no application reply

client -> 62 bytes
server -> no application reply

~25 seconds silence
client eventually closes
```

For the first comparison, record only:

- direction,
- packet/application-data length,
- timestamps / relative timing,
- TCP flags.

Do not publish WebSocket payloads, auth headers, cookies, launcher command lines, or tokens.

## Interpretation

### Windows receives a reply where Wine does not

This strongly suggests the server accepted native Windows client state but rejected or ignored the Wine client's final state.

Next action: compare ordinary Windows API results with standalone probes.

### Windows message sizes differ

This is even more useful. The first size divergence gives a concrete place to work backward from.

Example:

```text
Wine:    46, 62
Windows: 46, 78
```

Next action: identify which standard system properties feed the differently-sized message, then test those APIs outside the protected wrapper.

### Windows also times out identically

Then the current network hypothesis is wrong or the backend/account state itself is failing. Re-check service logs and contact Retrac/Alea support with the private fatal diagnostic.

## Process snapshot

After the protected launch starts:

```powershell
tasklist | findstr /I "Alea Fortnite Retrac"
netstat -ano | findstr ":80"
```

Again, do not publish command lines containing credentials.
