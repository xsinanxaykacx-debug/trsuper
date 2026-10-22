Set-Location "C:\Users\bzdye\Downloads\trsuper"
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
python scripts\check_paths.py
if ($LASTEXITCODE -ne 0) {
    throw "check_paths.py hata koduyla sonlandi: $LASTEXITCODE"
}
