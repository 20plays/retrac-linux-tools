# Reproduction and Diagnostic Commands

These commands reflect the test setup used during the investigation. Adjust paths to your own prefix.

## Environment

```bash
P=/home/sprite/Games/retrac-wine
EXE="$P/drive_c/Program Files/Retrac/retrac.exe"
```

## Start Alea service cleanly

```bash
WINEPREFIX="$P" wineserver -k
sleep 2
WINEPREFIX="$P" wineserver -p
WINEPREFIX="$P" wine sc start AleaAntiCheat
```

## Launch Retrac

```bash
WINEPREFIX="$P" wine "$EXE"
```

## List relevant Wine processes

```bash
WINEPREFIX="$P" wine tasklist | grep -Ei 'Alea|Fortnite|Retrac'
```

Avoid `pgrep -af` when sharing output publicly: the protected wrapper command line may contain live-looking authentication material.

## OAuth URI handler

Example desktop entry:

```ini
[Desktop Entry]
Name=Retrac
Type=Application
NoDisplay=true
Terminal=false
Exec=env WINEPREFIX=/home/sprite/Games/retrac-wine wine "/home/sprite/Games/retrac-wine/drive_c/Program Files/Retrac/retrac.exe" %u
MimeType=x-scheme-handler/retrac;
```

Register it:

```bash
xdg-mime default retrac-wine.desktop x-scheme-handler/retrac
kbuildsycoca6
```

## Focused wrapper relay trace

The investigation used Wine's relay channel with the caller constrained to the wrapper.

Example registry filter:

```bash
WINEPREFIX="$P" wine reg add   'HKCU\Software\Wine\Debug'   /v RelayFromInclude   /t REG_SZ   /d 'FortniteClient-Win64-Shipping.exe;FortniteClient-Win64-Shipping'   /f
```

Then:

```bash
TRACE="$HOME/retrac-debug/wrapper-relay.log"

WINEPREFIX="$P" wineserver -k
sleep 2
: > "$TRACE"

WINEPREFIX="$P" WINEDEBUG='-all,+relay,+process,+seh' wine sc start AleaAntiCheat > "$TRACE" 2>&1
```

Launch Retrac separately and reproduce the popup.

### Extract the thread that called MessageBoxW

```bash
M="$(grep -aEn 'Call user32\.MessageBoxW' "$TRACE" | tail -1)"
N="$(printf '%s\n' "$M" | cut -d: -f1)"
TID="$(printf '%s\n' "$M" | sed -E 's/^[0-9]+:([0-9a-fA-F]{4}):.*/\1/')"

sed -n "1,${N}p" "$TRACE"   | grep -a "^${TID}:"   > "$HOME/retrac-debug/wrapper-thread-all.txt"
```

Do not publish the literal MessageBox text if it contains an opaque support diagnostic.

## TCP timing capture

Resolve the backend first:

```bash
getent ahostsv4 alea-service-prod.retr.ac
```

Once the current IP is known, capture headers/timing only:

```bash
sudo tcpdump   -i any   -nn   -tttt   'host <CURRENT_IP> and tcp port 80'   > "$HOME/retrac-debug/wrapper-network-timing.txt"
```

The endpoint observed by the wrapper was:

```text
alea-service-prod.retr.ac:80
```

The address is behind Cloudflare and may change.

## Socket ownership

While the fatal popup is open:

```bash
LPID="$(pgrep -f 'FortniteClient-Win64-Shipping.exe' | tail -1)"

sudo ss -ntp | grep "pid=$LPID,"
sudo ss -unp | grep "pid=$LPID,"
sudo ss -xnp | grep "pid=$LPID,"
sudo lsof -Pan -p "$LPID" -i 2>/dev/null
```

## Thread-security diagnostic concepts

Temporary Wine server logging used during investigation printed:

- caller PID
- target PID
- candidate TID
- requested access
- `is_system`
- security descriptor pointer
- effective token
- `SeDebugPrivilege` enabled state
- SD owner/group/DACL/ACEs
- token user/group SIDs

This was sufficient to prove that protected threads existed and were intentionally denied by their explicit DACLs.

Those logs are diagnostic only; they are not required for normal operation.

## Firmware diagnostic concepts

Temporary logging around `SystemFirmwareTableInformation` printed:

- provider signature
- action
- table ID
- input buffer size
- status
- required size
- returned table length

Observed:

```text
RSMB enumerate: buffer-too-small -> success
RSMB get:       buffer-too-small -> success
FIRM enumerate: STATUS_NOT_IMPLEMENTED
```

On a UEFI system, the FIRM result is not itself suspicious.
