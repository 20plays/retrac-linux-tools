#!/usr/bin/env python3
"""Apply the minimal Retrac/Alea compatibility changes to Wine 11.16.

Pinned upstream Wine base:
    wine-11.16 / 8da89f8493b21ebfbe344a54dbef0cde23c7ea59

The target is the prepared Wine source tree from the pinned Arch
wine-staging PKGBUILD. prepare() applies Wine-Staging first; this script then
applies the additional compatibility work that reached the documented Retrac
checkpoint.

Temporary RETRAC diagnostic logging is intentionally NOT installed here.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

EXPECTED_WINE_HEAD = "8da89f8493b21ebfbe344a54dbef0cde23c7ea59"


class PatchError(RuntimeError):
    pass


def run(cmd: list[str], cwd: pathlib.Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def read(root: pathlib.Path, rel: str) -> str:
    return (root / rel).read_text()


def write(root: pathlib.Path, rel: str, data: str) -> None:
    (root / rel).write_text(data)


def replace_once(root: pathlib.Path, rel: str, old: str, new: str, marker: str | None = None) -> bool:
    data = read(root, rel)
    if marker and marker in data:
        print(f"already: {rel}: {marker}")
        return False
    count = data.count(old)
    if count != 1:
        raise PatchError(f"{rel}: expected anchor exactly once, found {count}: {old[:120]!r}")
    write(root, rel, data.replace(old, new, 1))
    print(f"patched: {rel}")
    return True


def insert_before(root: pathlib.Path, rel: str, anchor: str, text: str, marker: str) -> bool:
    data = read(root, rel)
    if marker in data:
        print(f"already: {rel}: {marker}")
        return False
    count = data.count(anchor)
    if count != 1:
        raise PatchError(f"{rel}: expected insertion anchor exactly once, found {count}: {anchor[:120]!r}")
    write(root, rel, data.replace(anchor, text + anchor, 1))
    print(f"patched: {rel}")
    return True


def verify_base(root: pathlib.Path) -> None:
    if not (root / ".git").exists():
        raise PatchError(f"{root} is not a Wine git checkout")
    head = run(["git", "rev-parse", "HEAD"], root)
    if head != EXPECTED_WINE_HEAD:
        raise PatchError(
            f"wrong Wine base: expected {EXPECTED_WINE_HEAD} (wine-11.16), got {head}. "
            "Use scripts/build-wine-arch.sh so the packaging/source revisions are pinned."
        )


def patch_wintrust(root: pathlib.Path) -> None:
    replace_once(
        root, "dlls/wintrust/softpub.c",
        "FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);",
        "FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);",
        "FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE",
    )


def patch_service_privileges(root: pathlib.Path) -> None:
    replace_once(
        root, "server/token.c",
        "const struct luid SeIncreaseQuotaPrivilege = { 5, 0 };",
        "static const struct luid SeAssignPrimaryTokenPrivilege = { 3, 0 };\n"
        "const struct luid SeIncreaseQuotaPrivilege = { 5, 0 };",
        "SeAssignPrimaryTokenPrivilege = { 3, 0 }",
    )
    replace_once(
        root, "server/token.c",
        "        { SeCreatePagefilePrivilege, 0 },\n"
        "        { SeIncreaseQuotaPrivilege, 0 },",
        "        { SeCreatePagefilePrivilege, 0 },\n"
        "        { SeAssignPrimaryTokenPrivilege, 0 },\n"
        "        { SeIncreaseQuotaPrivilege, 0 },",
        "{ SeAssignPrimaryTokenPrivilege, 0 },",
    )


def patch_ole(root: pathlib.Path) -> None:
    replace_once(
        root, "dlls/ole32/ole2.c",
        "    IStream *stream;\n"
        "    IDropTarget *drop_target;\n"
        "    HRESULT hr;",
        "    IStream *stream;\n"
        "    IDropTarget *drop_target;\n"
        "    DWORD pid = 0;\n"
        "    HRESULT hr;",
        "IDropTarget *drop_target;\\n    DWORD pid = 0;\\n    HRESULT hr;",
    )
    replace_once(
        root, "dlls/ole32/ole2.c",
        "    drop_target = GetPropW(hwnd, prop_oledroptarget);\n"
        "    if(drop_target) IDropTarget_Release(drop_target);\n\n"
        "    RemovePropW(hwnd, prop_oledroptarget);",
        "    GetWindowThreadProcessId(hwnd, &pid);\n"
        "    if (pid == GetCurrentProcessId())\n"
        "    {\n"
        "        drop_target = GetPropW(hwnd, prop_oledroptarget);\n"
        "        if(drop_target) IDropTarget_Release(drop_target);\n"
        "    }\n\n"
        "    RemovePropW(hwnd, prop_oledroptarget);",
        "GetWindowThreadProcessId(hwnd, &pid);",
    )


def patch_mr9843_token_session(root: pathlib.Path) -> None:
    replace_once(
        root, "dlls/ntdll/unix/security.c",
        """    case TokenSessionId:
        if (length < sizeof(DWORD))
        {
            ret = STATUS_INFO_LENGTH_MISMATCH;
            break;
        }
        if (!info)
        {
            ret = STATUS_ACCESS_VIOLATION;
            break;
        }
        FIXME("TokenSessionId stub!\\n");
        ret = STATUS_SUCCESS;
        break;""",
        """    case TokenSessionId:
        if (length < sizeof(ULONG))
        {
            ret = STATUS_INFO_LENGTH_MISMATCH;
            break;
        }
        if (!info)
        {
            ret = STATUS_ACCESS_VIOLATION;
            break;
        }
        SERVER_START_REQ( set_token_session_id )
        {
            req->handle = wine_server_obj_handle( token );
            req->session_id = *((ULONG *)info);
            ret = wine_server_call( req );
        }
        SERVER_END_REQ;
        ret = STATUS_SUCCESS;
        break;""",
        "SERVER_START_REQ( set_token_session_id )",
    )
    insert_before(
        root, "server/protocol.def", "@REQ(set_security_object)",
        """@REQ(set_token_session_id)
    obj_handle_t    handle;     /* handle to the token */
    unsigned int    session_id; /* session id the token should become */
@END

""",
        "@REQ(set_token_session_id)",
    )
    insert_before(
        root, "server/token.c", "DECL_HANDLER(create_linked_token)",
        """DECL_HANDLER(set_token_session_id)
{
    struct token *token;

    if ((token = (struct token *)get_handle_obj( current->process, req->handle,
                                                 TOKEN_ADJUST_DEFAULT,
                                                 &token_ops )))
    {
        token->session_id = req->session_id;
        release_object( token );
    }
}

""",
        "DECL_HANDLER(set_token_session_id)",
    )


def patch_mr9843_wts(root: pathlib.Path) -> None:
    replace_once(
        root, "dlls/wtsapi32/wtsapi32.c",
        """    return DuplicateHandle(GetCurrentProcess(), GetCurrentProcessToken(),
                           GetCurrentProcess(), token,
                           0, FALSE, DUPLICATE_SAME_ACCESS);""",
        """    if (!DuplicateHandle(GetCurrentProcess(), GetCurrentProcessToken(),
                         GetCurrentProcess(), token,
                         0, FALSE, DUPLICATE_SAME_ACCESS))
        return FALSE;

    return SetTokenInformation(*token, TokenSessionId, &session_id, sizeof(ULONG));""",
        "return SetTokenInformation(*token, TokenSessionId",
    )

    old = """BOOL WINAPI WTSEnumerateSessionsW(HANDLE server, DWORD reserved, DWORD version,
        PWTS_SESSION_INFOW *session_info, DWORD *count)
{
    static const WCHAR session_name[] = L"Console";

    FIXME("%p 0x%08lx 0x%08lx %p %p semi-stub.\\n", server, reserved, version, session_info, count);

    if (!session_info || !count) return FALSE;

    if (!(*session_info = malloc(sizeof(**session_info) + sizeof(session_name))))
    {
        SetLastError(ERROR_OUTOFMEMORY);
        return FALSE;
    }
    if (!ProcessIdToSessionId( GetCurrentProcessId(), &(*session_info)->SessionId))
    {
        WTSFreeMemory(*session_info);
        return FALSE;
    }
    *count = 1;
    (*session_info)->State = WTSActive;
    (*session_info)->pWinStationName = (WCHAR *)((char *)*session_info + sizeof(**session_info));
    memcpy((*session_info)->pWinStationName, session_name, sizeof(session_name));

    return TRUE;
}"""
    new = """BOOL WINAPI WTSEnumerateSessionsW(HANDLE server, DWORD reserved, DWORD version,
        PWTS_SESSION_INFOW *session_info, DWORD *count)
{
    static const WCHAR services_name[] = L"Services";
    static const WCHAR console_name[] = L"Console";
    WCHAR *names;

    FIXME("%p 0x%08lx 0x%08lx %p %p semi-stub; returning service and console sessions.\\n",
          server, reserved, version, session_info, count);

    if (!session_info || !count) return FALSE;

    if (!(*session_info = malloc(2 * sizeof(**session_info) +
                                sizeof(services_name) + sizeof(console_name))))
    {
        SetLastError(ERROR_OUTOFMEMORY);
        return FALSE;
    }

    *count = 2;
    names = (WCHAR *)((char *)*session_info + 2 * sizeof(**session_info));

    (*session_info)[0].SessionId = 0;
    (*session_info)[0].State = WTSDisconnected;
    (*session_info)[0].pWinStationName = names;
    memcpy(names, services_name, sizeof(services_name));
    names += ARRAY_SIZE(services_name);

    (*session_info)[1].SessionId = 1;
    (*session_info)[1].State = WTSActive;
    (*session_info)[1].pWinStationName = names;
    memcpy(names, console_name, sizeof(console_name));

    return TRUE;
}"""
    replace_once(root, "dlls/wtsapi32/wtsapi32.c", old, new, 'static const WCHAR services_name[] = L"Services";')


def patch_mr9843_winstations(root: pathlib.Path) -> None:
    replace_once(
        root, "server/user.h",
        "    unsigned __int64   monitor_serial;     /* winstation monitor update counter */\n};",
        "    unsigned __int64   monitor_serial;     /* winstation monitor update counter */\n"
        "    unsigned int       session_id;         /* session id this winstation belongs to */\n};",
        "session id this winstation belongs to",
    )
    replace_once(
        root, "server/winstation.c",
        "struct winstation_init_data\n{\n    unsigned int           flags;\n};",
        "struct winstation_init_data\n{\n    unsigned int           flags;\n    unsigned int           session_id;\n};",
        "unsigned int           session_id;",
    )
    replace_once(
        root, "server/winstation.c",
        "    winstation->flags = data->flags;\n    winstation->input_desktop = NULL;",
        "    winstation->flags = data->flags;\n    winstation->session_id = data->session_id;\n"
        "    winstation->input_desktop = NULL;",
        "winstation->session_id = data->session_id;",
    )
    replace_once(
        root, "server/winstation.c",
        "    struct winstation_init_data data = { .flags = req->flags };",
        "    struct winstation_init_data data = { .flags = req->flags, "
        ".session_id = current->process->session_id };",
        ".session_id = current->process->session_id",
    )
    replace_once(
        root, "server/winstation.c",
        "            if (!check_object_access( NULL, &winstation->obj, &access )) continue;\n"
        "            reply->count++;",
        "            if (!check_object_access( NULL, &winstation->obj, &access )) continue;\n"
        "            if (current->process->session_id != winstation->session_id) continue;\n"
        "            reply->count++;",
        "current->process->session_id != winstation->session_id",
    )


def patch_mr9843_services(root: pathlib.Path) -> None:
    replace_once(
        root, "programs/services/services.c",
        "    HANDLE token;\n    WCHAR *path;\n    DWORD err;\n    BOOL r;",
        "    HANDLE token;\n    WCHAR *path;\n    DWORD err, service_session_id = 0;\n    BOOL r;",
        "service_session_id = 0",
    )
    replace_once(
        root, "programs/services/services.c",
        """    if (!environment && OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY | TOKEN_DUPLICATE, &token))
    {
        WCHAR val[16];
        CreateEnvironmentBlock(&environment, token, FALSE);
        if (GetEnvironmentVariableW( L"WINEBOOTSTRAPMODE", val, ARRAY_SIZE(val) ))
        {
            UNICODE_STRING name = RTL_CONSTANT_STRING(L"WINEBOOTSTRAPMODE");
            UNICODE_STRING value;

            RtlInitUnicodeString( &value, val );
            RtlSetEnvironmentVariable( (WCHAR **)&environment, &name, &value );
        }
        CloseHandle(token);
    }""",
        """    r = DuplicateHandle(GetCurrentProcess(), GetCurrentProcessToken(),
                        GetCurrentProcess(), &token, 0, FALSE, DUPLICATE_SAME_ACCESS);
    TRACE("DuplicateHandle %u %lu\\n", r, GetLastError());
    if (!r)
    {
        err = GetLastError();
        free(path);
        service_unlock(service_entry);
        release_process(process);
        return err;
    }

    if (!environment)
    {
        WCHAR val[16];
        CreateEnvironmentBlock(&environment, token, FALSE);
        if (GetEnvironmentVariableW( L"WINEBOOTSTRAPMODE", val, ARRAY_SIZE(val) ))
        {
            UNICODE_STRING name = RTL_CONSTANT_STRING(L"WINEBOOTSTRAPMODE");
            UNICODE_STRING value;

            RtlInitUnicodeString( &value, val );
            RtlSetEnvironmentVariable( (WCHAR **)&environment, &name, &value );
        }
    }""",
        'TRACE("DuplicateHandle %u %lu\\n"',
    )
    replace_once(
        root, "programs/services/services.c",
        """    r = CreateProcessW(NULL, path, NULL, NULL, FALSE, CREATE_UNICODE_ENVIRONMENT | DETACHED_PROCESS, environment, NULL, &si, &pi);
    free(path);""",
        """    r = SetTokenInformation(token, TokenSessionId, &service_session_id, sizeof(service_session_id));
    if (!r)
    {
        err = GetLastError();
        CloseHandle(token);
        free(path);
        process_terminate(process);
        release_process(process);
        return err;
    }

    r = CreateProcessAsUserW(token, NULL, path, NULL, NULL, FALSE,
                             CREATE_UNICODE_ENVIRONMENT | DETACHED_PROCESS,
                             environment, NULL, &si, &pi);
    CloseHandle(token);
    free(path);""",
        "r = SetTokenInformation(token, TokenSessionId",
    )


def patch_mr9843_connect_winstation(root: pathlib.Path) -> None:
    replace_once(
        root, "server/winstation.c",
        '#include "security.h"\n',
        '#include "security.h"\n#include "unicode.h"\n',
        '#include "unicode.h"',
    )
    old = """void connect_process_winstation( struct process *process, struct unicode_str desktop_name,
                                 struct thread *parent_thread, struct process *parent_process )
{
    struct unicode_str winstation_name = {0};
    struct winstation *winstation = NULL;
    struct desktop *desktop = NULL;
    const WCHAR *wch, *end;
    obj_handle_t handle;
    struct object_params params = { .attr = OBJ_CASE_INSENSITIVE | OBJ_OPENIF };"""
    new = """void connect_process_winstation( struct process *process, struct unicode_str desktop_name,
                                 struct thread *parent_thread, struct process *parent_process )
{
    struct unicode_str winstation_name = {0}, root_name = {0}, full_winstation_name = {0};
    struct winstation *winstation = NULL;
    struct desktop *desktop = NULL;
    const WCHAR *wch, *end;
    obj_handle_t handle = 0;
    char ascii_root[50];
    static const WCHAR service_winstationW[] = L"__wineservice_winstation";
    static const WCHAR console_winstationW[] = L"WinSta0";
    static const WCHAR default_desktopW[] = L"Default";
    static const struct unicode_str service_winstation =
        { service_winstationW, sizeof(service_winstationW) - sizeof(WCHAR) };
    static const struct unicode_str console_winstation =
        { console_winstationW, sizeof(console_winstationW) - sizeof(WCHAR) };
    static const struct unicode_str default_desktop =
        { default_desktopW, sizeof(default_desktopW) - sizeof(WCHAR) };
    struct object_params params = { .attr = OBJ_CASE_INSENSITIVE | OBJ_OPENIF };"""
    replace_once(root, "server/winstation.c", old, new,
                 'static const WCHAR service_winstationW[] = L"__wineservice_winstation";')

    anchor = """    params.ops  = &winstation_ops;
    params.name = winstation_name;

    /* check for an inherited winstation handle (don't ask...) */"""
    repl = """    if (parent_thread && process->session_id != parent_thread->process->session_id)
    {
        /* CreateProcessAsUserW into another session: attach to that session's default station/desktop. */
        winstation_name = process->session_id ? console_winstation : service_winstation;
        desktop_name = default_desktop;
    }

    params.ops  = &winstation_ops;
    params.name = winstation_name;

    /* check for an inherited winstation handle (don't ask...) */"""
    replace_once(root, "server/winstation.c", anchor, repl, "CreateProcessAsUserW into another session")

    old_branch = """    else if (winstation_name.len && (winstation = open_named_object( &params )))
    {
        handle = alloc_handle( process, winstation, STANDARD_RIGHTS_REQUIRED | WINSTA_ALL_ACCESS, 0 );
    }"""
    new_branch = """    else if (winstation_name.len)
    {
        snprintf( ascii_root, sizeof(ascii_root), "\\\\Sessions\\\\%u\\\\Windows\\\\WindowStations\\\\",
                  process->session_id );
        if (!ascii_to_unicode_str( ascii_root, &root_name )) goto done;

        full_winstation_name.len = root_name.len + winstation_name.len;
        if (!(full_winstation_name.str = malloc( full_winstation_name.len ))) goto done;
        memcpy( (WCHAR *)full_winstation_name.str, root_name.str, root_name.len );
        memcpy( (WCHAR *)full_winstation_name.str + root_name.len / sizeof(WCHAR),
                winstation_name.str, winstation_name.len );

        params.root = NULL;
        params.name = full_winstation_name;
        if ((winstation = open_named_object( &params )))
            handle = alloc_handle( process, winstation, STANDARD_RIGHTS_REQUIRED | WINSTA_ALL_ACCESS, 0 );
    }"""
    replace_once(root, "server/winstation.c", old_branch, new_branch,
                 "full_winstation_name.len = root_name.len + winstation_name.len")

    replace_once(
        root, "server/winstation.c",
        """done:
    if (desktop) release_object( desktop );
    if (winstation) release_object( winstation );
    clear_error();""",
        """done:
    free( (void *)full_winstation_name.str );
    free( (void *)root_name.str );
    if (desktop) release_object( desktop );
    if (winstation) release_object( winstation );
    clear_error();""",
        "free( (void *)full_winstation_name.str );",
    )


def patch_boot_environment(root: pathlib.Path) -> None:
    replace_once(
        root, "dlls/ntdll/unix/system.c",
        "#include <string.h>\n#include <sys/types.h>",
        "#include <string.h>\n#include <sys/stat.h>\n#include <sys/types.h>",
        "#include <sys/stat.h>",
    )

    helper = r'''/******************************************************************************
 * retrac_hexstr32_to_guid
 */
static inline BOOL retrac_hexstr32_to_guid( const char *s, GUID *id )
{
    int i;

    if (!s)
    {
        memset( id, 0, sizeof(*id) );
        return FALSE;
    }

    id->Data1 = 0;
    for (i = 0; i < 8; ++i)
    {
        if (!(((s[i] >= '0') && (s[i] <= '9')) || ((s[i] >= 'a') && (s[i] <= 'f')) ||
              ((s[i] >= 'A') && (s[i] <= 'F')))) return FALSE;
        id->Data1 = (id->Data1 << 4) | ((s[i] & 0xf) + (s[i] >> 6)) | ((s[i] >> 3) & 8);
    }

    id->Data2 = 0;
    for (i = 8; i < 12; ++i)
    {
        if (!(((s[i] >= '0') && (s[i] <= '9')) || ((s[i] >= 'a') && (s[i] <= 'f')) ||
              ((s[i] >= 'A') && (s[i] <= 'F')))) return FALSE;
        id->Data2 = (id->Data2 << 4) | ((s[i] & 0xf) + (s[i] >> 6)) | ((s[i] >> 3) & 8);
    }

    id->Data3 = 0;
    for (i = 12; i < 16; ++i)
    {
        if (!(((s[i] >= '0') && (s[i] <= '9')) || ((s[i] >= 'a') && (s[i] <= 'f')) ||
              ((s[i] >= 'A') && (s[i] <= 'F')))) return FALSE;
        id->Data3 = (id->Data3 << 4) | ((s[i] & 0xf) + (s[i] >> 6)) | ((s[i] >> 3) & 8);
    }

    for (i = 16; i < 32; i += 2)
    {
        unsigned int hi, lo;
        if (!(((s[i] >= '0') && (s[i] <= '9')) || ((s[i] >= 'a') && (s[i] <= 'f')) ||
              ((s[i] >= 'A') && (s[i] <= 'F')))) return FALSE;
        if (!(((s[i + 1] >= '0') && (s[i + 1] <= '9')) || ((s[i + 1] >= 'a') && (s[i + 1] <= 'f')) ||
              ((s[i + 1] >= 'A') && (s[i + 1] <= 'F')))) return FALSE;
        hi = ((s[i] & 0xf) + (s[i] >> 6)) | ((s[i] >> 3) & 8);
        lo = ((s[i + 1] & 0xf) + (s[i + 1] >> 6)) | ((s[i + 1] >> 3) & 8);
        id->Data4[(i - 16) / 2] = (hi << 4) | lo;
    }
    return TRUE;
}

'''
    insert_before(
        root, "dlls/ntdll/unix/system.c",
        "/******************************************************************************\n *              NtQuerySystemInformation  (NTDLL.@)\n */",
        helper,
        "retrac_hexstr32_to_guid",
    )

    case = r'''    case SystemBootEnvironmentInformation:  /* 90 */
    {
        static SYSTEM_BOOT_ENVIRONMENT_INFORMATION boot_info = {0};
        struct stat stat_info = {0};
#if defined(__linux__) || defined(__gnu_linux__)
        int fd;
        char buffer[32];
        ssize_t ssz;
#endif

        len = sizeof(boot_info);
        if (size == len)
        {
#if defined(__linux__) || defined(__gnu_linux__)
            if (boot_info.FirmwareType == FirmwareTypeUnknown)
                boot_info.FirmwareType = !stat( "/sys/firmware/efi", &stat_info ) ? FirmwareTypeUefi : FirmwareTypeBios;
#elif defined(__APPLE__)
            boot_info.FirmwareType = FirmwareTypeUefi;
#else
            boot_info.FirmwareType = FirmwareTypeBios;
#endif

            if (!boot_info.BootIdentifier.Data1)
            {
#if defined(__linux__) || defined(__gnu_linux__)
                if (!stat( "/etc/machine-id", &stat_info ) && stat_info.st_size >= 32 &&
                    (fd = open( "/etc/machine-id", O_RDONLY )) != -1)
                {
                    ssz = read( fd, buffer, sizeof(buffer) );
                    close( fd );
                    if (ssz != sizeof(buffer) || !retrac_hexstr32_to_guid( buffer, &boot_info.BootIdentifier ))
                        memset( &boot_info.BootIdentifier, 0, sizeof(boot_info.BootIdentifier) );
                }
#endif
                if (!boot_info.BootIdentifier.Data1)
                {
#ifdef __APPLE__
                    if (!stat( "/Users", &stat_info ) || !stat( "/System", &stat_info ))
#else
                    if (!stat( "/home", &stat_info ) || !stat( "/usr", &stat_info ))
#endif
                    {
                        boot_info.BootIdentifier.Data1 = gethostid() & 0xffffffff;
                        boot_info.BootIdentifier.Data2 = stat_info.st_dev & 0xffff;
                        boot_info.BootIdentifier.Data3 = stat_info.st_ino & 0xffff;
                        boot_info.BootIdentifier.Data4[0] = 'W' ^ (boot_info.BootIdentifier.Data1 & 0xff);
                        boot_info.BootIdentifier.Data4[1] = 'I' ^ ((boot_info.BootIdentifier.Data1 >> 4) & 0xff);
                        boot_info.BootIdentifier.Data4[2] = 'N' ^ ((boot_info.BootIdentifier.Data1 >> 8) & 0xff);
                        boot_info.BootIdentifier.Data4[3] = 'E' ^ ((boot_info.BootIdentifier.Data1 >> 12) & 0xff);
                        boot_info.BootIdentifier.Data4[4] = 'B' ^ ((boot_info.BootIdentifier.Data1 >> 16) & 0xff);
                        boot_info.BootIdentifier.Data4[5] = 'O' ^ ((boot_info.BootIdentifier.Data1 >> 20) & 0xff);
                        boot_info.BootIdentifier.Data4[6] = 'O' ^ ((boot_info.BootIdentifier.Data1 >> 24) & 0xff);
                        boot_info.BootIdentifier.Data4[7] = 'T' ^ ((boot_info.BootIdentifier.Data1 >> 28) & 0xff);
                    }
                }
                boot_info.BootIdentifier.Data3 &= 0x0fff;
                boot_info.BootIdentifier.Data3 |= 4 << 12;
                boot_info.BootIdentifier.Data4[0] &= 0x3f;
                boot_info.BootIdentifier.Data4[0] |= 0x80;
            }

            if (!info) ret = STATUS_ACCESS_VIOLATION;
            else memcpy( info, &boot_info, len );
        }
        else ret = STATUS_INFO_LENGTH_MISMATCH;
        break;
    }

'''
    insert_before(
        root, "dlls/ntdll/unix/system.c",
        "    case SystemCpuInformation:  /* 1 */",
        case,
        "case SystemBootEnvironmentInformation:  /* 90 */",
    )

    boot_struct = r'''/* System Information Class 0x90 */
typedef struct _SYSTEM_BOOT_ENVIRONMENT_INFORMATION
{
    GUID BootIdentifier;
    FIRMWARE_TYPE FirmwareType;
    union
    {
        ULONGLONG BootFlags;
        struct
        {
            ULONGLONG DbgMenuOsSelection : 1;
            ULONGLONG DbgHiberBoot : 1;
            ULONGLONG DbgSoftBoot : 1;
            ULONGLONG DbgMeasuredLaunch : 1;
            ULONGLONG DbgMeasuredLaunchCapable : 1;
            ULONGLONG DbgSystemHiveReplace : 1;
            ULONGLONG DbgMeasuredLaunchSmmProtections : 1;
            ULONGLONG DbgMeasuredLaunchSmmLevel : 7;
        };
    };
} SYSTEM_BOOT_ENVIRONMENT_INFORMATION, *PSYSTEM_BOOT_ENVIRONMENT_INFORMATION;

'''
    insert_before(
        root, "include/winternl.h",
        "/* System Information Class 0x01 */",
        boot_struct,
        "typedef struct _SYSTEM_BOOT_ENVIRONMENT_INFORMATION",
    )

    replace_once(
        root, "dlls/wow64/system.c",
        "    case SystemDynamicTimeZoneInformation:  /* RTL_DYNAMIC_TIME_ZONE_INFORMATION */",
        "    case SystemBootEnvironmentInformation:  /* SYSTEM_BOOT_ENVIRONMENT_INFORMATION */\n"
        "    case SystemDynamicTimeZoneInformation:  /* RTL_DYNAMIC_TIME_ZONE_INFORMATION */",
        "case SystemBootEnvironmentInformation:  /* SYSTEM_BOOT_ENVIRONMENT_INFORMATION */",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wine_source", type=pathlib.Path, help="path to prepared Wine 11.16 source tree")
    args = parser.parse_args()
    root = args.wine_source.expanduser().resolve()

    try:
        verify_base(root)
        patch_wintrust(root)
        patch_service_privileges(root)
        patch_ole(root)
        patch_mr9843_token_session(root)
        patch_mr9843_wts(root)
        patch_mr9843_winstations(root)
        patch_mr9843_services(root)
        patch_mr9843_connect_winstation(root)
        patch_boot_environment(root)
    except (PatchError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("\nSource transformations complete.")
    print("Run ./tools/make_requests in the Wine source tree before building (server protocol changed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
