# वाक् launcher for PowerShell:  .\vak.ps1 examples\01_namaste.vak
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python -m vaak @args
exit $LASTEXITCODE
