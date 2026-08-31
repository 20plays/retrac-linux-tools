# Security and Redaction

This is a public repository. Treat raw Retrac/Alea logs and process command lines as potentially sensitive.

## Never commit

- launcher authentication passwords
- exchange codes
- Alea bearer/JWT-style tokens
- session IDs that may still be live
- full protected-wrapper command lines
- cookies
- Authorization headers
- WebSocket payload bodies
- fatal popup diagnostic blobs
- private user identifiers that are not necessary to reproduce a Wine bug

## Safer things to share

- API names and return statuses
- packet lengths/directions/timestamps
- TCP flags
- generic SIDs from a test prefix
- Wine source diffs that implement Windows semantics
- standalone test programs
- redacted service logs
- hashes of public installers/binaries when useful for version identification

## If you accidentally expose a token

Invalidate it by logging out/re-authenticating or otherwise refreshing the session before assuming it is harmless.

## Project boundary

This project is for compatibility work, not bypassing anti-cheat.

Do not contribute code or instructions that:

- disable Alea,
- forge successful integrity checks,
- bypass Authenticode/hash checks,
- modify protected game binaries,
- weaken deliberately restrictive ACLs,
- hide Wine from deliberate environment detection,
- defeat anti-debug checks,
- synthesize expected backend protocol replies,
- emulate or bypass a required Windows kernel driver.

If a compatibility fix is legitimate, it should be explainable as: **Wine now behaves more like Windows for a documented or experimentally verified API semantic.**
