# PolyLife Docker launcher for Team2.
#
# Usage:
#   .\teams\team2\run.ps1 team-up
#   .\teams\team2\run.ps1 all-up
#   .\teams\team2\run.ps1 all-down
#
# Running the script without an argument defaults to "team-up".

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("team-up", "all-up", "all-down", "help")]
    [string]$Command = "team-up"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\..")
)
$TeamCompose = Join-Path $PSScriptRoot "docker-compose.yml"
$RootEnv = Join-Path $ProjectRoot ".env"
$NetworkName = "polylife_net"

function Write-Log {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[PolyLife] $Message"
}

function Find-ComposeFile {
    param([Parameter(Mandatory = $true)][string]$Directory)

    $Names = @(
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml"
    )

    foreach ($Name in $Names) {
        $Candidate = Join-Path $Directory $Name
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            return $Candidate
        }
    }

    return $null
}

function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is not installed or is not available in PATH."
    }

    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose v2 is not available. Install Docker Desktop or the Compose plugin."
    }
}

function Initialize-RootEnv {
    if (Test-Path -LiteralPath $RootEnv -PathType Leaf) {
        return
    }

    $RootExample = Join-Path $ProjectRoot ".env.example"
    $TeamExample = Join-Path $PSScriptRoot ".env.example"
    $SourceEnv = $null

    if (Test-Path -LiteralPath $RootExample -PathType Leaf) {
        $SourceEnv = $RootExample
    }
    elseif (Test-Path -LiteralPath $TeamExample -PathType Leaf) {
        $SourceEnv = $TeamExample
    }
    else {
        throw "No .env or .env.example file was found in the project root or Team2 directory."
    }

    Copy-Item -LiteralPath $SourceEnv -Destination $RootEnv
    Write-Log "Created $RootEnv from $SourceEnv. Review its values before production use."
}

function Initialize-SharedNetwork {
    & docker network inspect $NetworkName *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Creating shared Docker network: $NetworkName"
        & docker network create $NetworkName *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create Docker network '$NetworkName'."
        }
    }
}

function Invoke-ComposeUp {
    param([Parameter(Mandatory = $true)][string]$ComposeFile)

    $RelativePath = $ComposeFile.Replace("$ProjectRoot\", "")
    Write-Log "Starting: $RelativePath"

    & docker compose `
        --env-file $RootEnv `
        -f $ComposeFile `
        up -d --build

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed while starting '$RelativePath'."
    }
}

function Invoke-ComposeDown {
    param([Parameter(Mandatory = $true)][string]$ComposeFile)

    $RelativePath = $ComposeFile.Replace("$ProjectRoot\", "")
    Write-Log "Stopping: $RelativePath"

    & docker compose `
        --env-file $RootEnv `
        -f $ComposeFile `
        down --remove-orphans

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed while stopping '$RelativePath'."
    }
}

function Get-AllComposeFiles {
    $RootCompose = Find-ComposeFile -Directory $ProjectRoot
    if (-not $RootCompose) {
        throw "The Core Compose file was not found in $ProjectRoot."
    }

    $ComposeFiles = [System.Collections.Generic.List[string]]::new()
    $ComposeFiles.Add($RootCompose)

    $TeamsDirectory = Join-Path $ProjectRoot "teams"
    if (Test-Path -LiteralPath $TeamsDirectory -PathType Container) {
        $TeamDirectories = Get-ChildItem -LiteralPath $TeamsDirectory -Directory |
            Sort-Object Name

        foreach ($TeamDirectory in $TeamDirectories) {
            $TeamComposeFile = Find-ComposeFile -Directory $TeamDirectory.FullName
            if ($TeamComposeFile) {
                $ComposeFiles.Add($TeamComposeFile)
            }
        }
    }

    return $ComposeFiles.ToArray()
}

function Start-Team2 {
    if (-not (Test-Path -LiteralPath $TeamCompose -PathType Leaf)) {
        throw "Team2 Compose file was not found: $TeamCompose"
    }

    Initialize-RootEnv
    Initialize-SharedNetwork
    Invoke-ComposeUp -ComposeFile $TeamCompose

    Write-Log "Team2 services are running."
    Write-Log "Backend: http://localhost:8002/api/team2/health/"
    Write-Log "Gateway: http://localhost:9102/api/team2/health/"
}

function Start-AllServices {
    Initialize-RootEnv
    Initialize-SharedNetwork
    $ComposeFiles = @(Get-AllComposeFiles)

    foreach ($ComposeFile in $ComposeFiles) {
        Invoke-ComposeUp -ComposeFile $ComposeFile
    }

    Write-Log "Core and all team services are running."
}

function Stop-AllServices {
    Initialize-RootEnv
    $ComposeFiles = @(Get-AllComposeFiles)
    [array]::Reverse($ComposeFiles)
    $Failures = [System.Collections.Generic.List[string]]::new()

    foreach ($ComposeFile in $ComposeFiles) {
        try {
            Invoke-ComposeDown -ComposeFile $ComposeFile
        }
        catch {
            Write-Warning $_.Exception.Message
            $Failures.Add($ComposeFile)
        }
    }

    if ($Failures.Count -gt 0) {
        throw "One or more Compose stacks could not be stopped. Check the Docker output above."
    }

    Write-Log "All PolyLife services are stopped. Persistent volumes were preserved."
}

function Show-Usage {
    Write-Host @"
Usage: .\teams\team2\run.ps1 {team-up|all-up|all-down}
  team-up   Build and start all Team2 services.
  all-up    Build and start Core and every team Compose stack.
  all-down  Stop Core and every team Compose stack (keeps volumes).
"@
}

try {
    if ($Command -eq "help") {
        Show-Usage
        exit 0
    }

    Assert-Docker

    switch ($Command) {
        "team-up" {
            Start-Team2
        }
        "all-up" {
            Start-AllServices
        }
        "all-down" {
            Stop-AllServices
        }
    }
}
catch {
    Write-Error "[PolyLife] ERROR: $($_.Exception.Message)"
    exit 1
}