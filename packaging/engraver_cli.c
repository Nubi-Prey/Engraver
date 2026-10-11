#include <windows.h>
#include <stdio.h>
#include <string.h>

/**
 * Launcher nativo leve para console no Windows (engraver-cli.exe).
 * Encaminha argumentos para 'Engraver.exe cli ...' herdando o terminal (stdin/stdout/stderr).
 */
int main(int argc, char *argv[]) {
    char dir[MAX_PATH];
    GetModuleFileNameA(NULL, dir, MAX_PATH);
    char *last_slash = strrchr(dir, '\\');
    if (last_slash) {
        *last_slash = '\0';
    }

    char exe_path[MAX_PATH];
    snprintf(exe_path, sizeof(exe_path), "%s\\Engraver.exe", dir);

    char cmd_line[32768];
    int offset = snprintf(cmd_line, sizeof(cmd_line), "\"%s\" cli", exe_path);

    for (int i = 1; i < argc; i++) {
        if (strchr(argv[i], ' ') != NULL) {
            offset += snprintf(cmd_line + offset, sizeof(cmd_line) - offset, " \"%s\"", argv[i]);
        } else {
            offset += snprintf(cmd_line + offset, sizeof(cmd_line) - offset, " %s", argv[i]);
        }
        if (offset >= (int)sizeof(cmd_line) - 1) break;
    }

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessA(NULL, cmd_line, NULL, NULL, TRUE, 0, NULL, dir, &si, &pi)) {
        fprintf(stderr, "[ERRO] Nao foi possivel iniciar Engraver.exe (Codigo de erro: %lu)\n", GetLastError());
        return 1;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exit_code = 0;
    GetExitCodeProcess(pi.hProcess, &exit_code);

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return (int)exit_code;
}
