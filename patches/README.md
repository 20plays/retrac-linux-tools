# Patch Notes

The project currently documents known Wine changes in [../docs/wine-patches.md](../docs/wine-patches.md) instead of publishing an Alea/Fortnite-specific bypass patchset.

Why:

- some changes came from existing Wine merge requests,
- some were manually adapted to the Wine 11.16 source tree,
- temporary diagnostics are not production fixes,
- we want every permanent change to remain explainable as a generic Windows-compatibility correction.

If you have a clean local branch containing the compatibility work, useful future contributions would be:

1. export each generic fix as a separate patch,
2. add a minimal Wine test for the behavior,
3. note the exact upstream Wine base commit,
4. keep diagnostic-only changes separate.

Known logical patch groups:

- WinTrust file sharing: include `FILE_SHARE_DELETE`
- token privilege LUID / admin privilege representation
- OLE `RevokeDragDrop` foreign-HWND guard
- Wine MR 9843 session semantics
- Wine MR 6423 `SystemBootEnvironmentInformation` implementation

Do not add patches that fake anti-cheat success, modify protected binaries, weaken ACLs, or synthesize network responses.
