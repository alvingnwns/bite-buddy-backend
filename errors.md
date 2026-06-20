TEMPLATE = [timestamp] ERROR_NAME: description [from: FILE_DIRECTORY]

[2026-06-20T21:22] InterpreterHandleError: "Unable to handle python.exe" — VS Code tidak bisa membaca interpreter bbb_venv karena venv berada di dalam folder OneDrive yang mengunci file binary (.pyd, .exe) saat proses sinkronisasi. [from: bbb_venv\Scripts\python.exe]

[2026-06-20T21:29] InterpreterHandleError: "Unable to handle python.exe" — Masih error meski venv dipindah ke C:\Dev\bbb_venv. Root cause: sistem menggunakan Anaconda (C:\Users\leona\anaconda3\python.exe), bukan Python standar. VS Code Pylance/Python extension mengharapkan conda environment atau interpreter dari base Anaconda, bukan venv biasa yang dibuat dari python -m venv. [from: C:\Dev\bbb_venv\Scripts\python.exe]

[2026-06-20T21:34] InterpreterHandleError: "Unable to handle python.exe" — Error tetap muncul pada bbb-venv. Root cause yang diidentifikasi sebelumnya SALAH (diasumsikan VS Code/Cursor). IDE yang digunakan adalah Antigravity IDE, yang punya mekanisme Select Python Interpreter berbeda. Venv berfungsi normal di terminal. [from: bbb-venv\Scripts\python.exe]