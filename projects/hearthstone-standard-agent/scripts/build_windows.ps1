$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if (-not (Test-Path "data\knowledge\cards.collectible.zhCN.json.gz")) {
    & .\.venv\Scripts\python.exe scripts\update_data.py
}
& .\.venv\Scripts\python.exe scripts\report_standard_coverage.py --output data\knowledge\coverage.json
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean hearthstone-agent.spec

Write-Host "Built: dist\HearthstoneStandardAgent.exe"
