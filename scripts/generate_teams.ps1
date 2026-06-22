# Generate team1..team8 folders from teams/_template, substituting each team's
# name, unique DB password, and unique gateway port.
# Re-run any time to regenerate. Existing team folders are overwritten.

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$template = Join-Path $root "teams\_template"

# Unique dev-only DB password per team.
$passwords = @{
    1 = "plf_team1_K7m2Qx"
    2 = "plf_team2_R3n8Vt"
    3 = "plf_team3_W9p4Lc"
    4 = "plf_team4_Z2h6Bn"
    5 = "plf_team5_D5k1Jr"
    6 = "plf_team6_F8s3Mq"
    7 = "plf_team7_T4v7Gx"
    8 = "plf_team8_Y6c9Pw"
}

foreach ($i in 1..8) {
    $team = "team$i"
    $port = 9100 + $i
    $pass = $passwords[$i]
    $dest = Join-Path $root "teams\$team"

    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item $template $dest -Recurse

    # Read/write as UTF-8 without BOM so the Persian text is never corrupted
    # (Windows PowerShell's default Get-Content/Set-Content mangles UTF-8).
    $utf8 = New-Object System.Text.UTF8Encoding $false
    Get-ChildItem $dest -Recurse -File | ForEach-Object {
        $text = [System.IO.File]::ReadAllText($_.FullName, $utf8)
        $text = $text -replace "__TEAM__", $team `
                      -replace "__DB_PASSWORD__", $pass `
                      -replace "__PORT__", $port
        [System.IO.File]::WriteAllText($_.FullName, $text, $utf8)
    }
    Write-Output "generated $team  (port $port, db password $pass)"
}
