[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$apiRoot = Join-Path $repoRoot 'apps\api'
$webRoot = Join-Path $repoRoot 'apps\web'
$runRoot = Join-Path $repoRoot 'out\local-run'
$appUrl = 'http://localhost:3000/setup'
$pythonCandidates = @(
    (Join-Path $apiRoot '.venv\Scripts\python.exe'),
    ([IO.Path]::GetFullPath((Join-Path $repoRoot '..\..\work\classguard-api-clean\Scripts\python.exe')))
)

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Program $($Arguments -join ' ')"
    }
}

function Get-PortBindings {
    param([int]$Port)
    # Some Windows builds expose transient/incorrect State values for bound
    # sockets. A server binding has no remote port; ownership and HTTP health
    # are checked separately before reusing or restarting it.
    return @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.RemotePort -eq 0 })
}

function Get-ProjectListener {
    param([int]$Port, [ValidateSet('api', 'web')][string]$Service)
    $listeners = @(Get-PortBindings -Port $Port)
    if ($listeners.Count -eq 0) { return $null }
    $processIds = @($listeners.OwningProcess | Sort-Object -Unique)
    if ($processIds.Count -ne 1) {
        throw "Port $Port has multiple listeners. No processes were changed. Close the conflicting service and try again."
    }
    $listener = Get-CimInstance Win32_Process -Filter "ProcessId = $($processIds[0])"
    if (-not $listener) { throw "Cannot inspect the listener on port $Port. Try again." }
    $owned = $false
    $currentProcess = $listener
    for ($depth = 0; $depth -lt 6 -and $currentProcess; $depth++) {
        $command = [string]$currentProcess.CommandLine
        if ($Service -eq 'api') {
            $pythonMatches = @($pythonCandidates | Where-Object {
                $command.IndexOf($_, [StringComparison]::OrdinalIgnoreCase) -ge 0
            }).Count -gt 0
            $owned = $command.Contains('classguard.main:app') -and (
                $pythonMatches -or $command.IndexOf($apiRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
            )
        } else {
            $owned = $command.IndexOf($webRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
                $command -match '(?i)next(?:[\\/]|\s|\.)'
        }
        if ($owned) { break }
        if (-not $currentProcess.ParentProcessId -or $currentProcess.ParentProcessId -eq $PID) { break }
        $currentProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($currentProcess.ParentProcessId)"
    }
    if (-not $owned) {
        throw "Port $Port is used by another or unrecognized process (PID $($listener.ProcessId)). No processes were changed."
    }
    return $listener
}

function Test-Api {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 3
        return $health.service -eq 'classguard-api' -and $health.status -eq 'ok'
    } catch { return $false }
}

function Test-Web {
    try {
        $page = Invoke-WebRequest $appUrl -UseBasicParsing -TimeoutSec 3
        return $page.StatusCode -eq 200 -and $page.Content.Contains('ClassGuard')
    } catch { return $false }
}

function Get-NewestInput {
    param([string]$Root, [string[]]$Directories, [string[]]$Patterns)
    $files = @(
        foreach ($directory in $Directories) {
            $path = Join-Path $Root $directory
            if (Test-Path -LiteralPath $path) {
                Get-ChildItem -LiteralPath $path -Recurse -File |
                    Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' }
            }
        }
        foreach ($pattern in $Patterns) {
            Get-ChildItem -LiteralPath $Root -Filter $pattern -File
        }
    )
    return ($files | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1).LastWriteTimeUtc
}

function Stop-ProjectListener {
    param([int]$Port, [string]$Service, $Expected)
    $current = Get-ProjectListener -Port $Port -Service $Service
    if (-not $current) { return }
    if ($current.ProcessId -ne $Expected.ProcessId -or $current.CreationDate -ne $Expected.CreationDate) {
        throw "The process on port $Port changed during startup. Nothing was stopped; try again."
    }
    Stop-Process -Id $current.ProcessId -ErrorAction Stop
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        if (-not (Get-PortBindings -Port $Port)) { return }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Port $Port did not close after stopping its ClassGuard process."
}

function Start-HiddenService {
    param([string]$Program, [string[]]$Arguments, [string]$Directory, [string]$Service)
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $stdout = Join-Path $runRoot "$Service-$stamp.stdout.log"
    $stderr = Join-Path $runRoot "$Service-$stamp.stderr.log"
    # Windows filenames cannot contain double quotes. Quote each argument so paths
    # containing spaces stay intact when Start-Process constructs the command line.
    $quotedArguments = @($Arguments | ForEach-Object { '"' + $_ + '"' })
    $process = Start-Process -FilePath $Program -ArgumentList $quotedArguments -WorkingDirectory $Directory `
        -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Write-Host "Started $Service (PID $($process.Id)). Logs: $runRoot"
    return $process
}

function Wait-Ready {
    param([ValidateSet('api', 'web')][string]$Service, [Diagnostics.Process]$StartedProcess, [int]$Seconds = 45)
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        if ($StartedProcess) {
            $StartedProcess.Refresh()
            if ($StartedProcess.HasExited) { throw "$Service exited during startup. Inspect its latest stderr log in $runRoot." }
        }
        if (($Service -eq 'api' -and (Test-Api)) -or ($Service -eq 'web' -and (Test-Web))) { return }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "$Service did not become ready. Inspect its latest stderr log in $runRoot."
}

$startupMutex = $null
$mutexAcquired = $false
try {
    if (-not $CheckOnly) {
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $rootHash = [BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($repoRoot))).Replace('-', '') }
        finally { $hasher.Dispose() }
        $startupMutex = New-Object Threading.Mutex($false, "Local\ClassGuard-$rootHash")
        try { $mutexAcquired = $startupMutex.WaitOne(0) }
        catch [Threading.AbandonedMutexException] { $mutexAcquired = $true }
        if (-not $mutexAcquired) { throw 'ClassGuard startup is already running. Wait for that launch to finish.' }
    }

    # Inspect both ports before installing, building or changing any service.
    $apiListener = Get-ProjectListener -Port 8000 -Service api
    $webListener = Get-ProjectListener -Port 3000 -Service web
    $apiInputTime = Get-NewestInput -Root $apiRoot -Directories @('classguard') -Patterns @('.env', 'requirements*.txt', 'pyproject.toml')
    $webInputTime = Get-NewestInput -Root $webRoot -Directories @('src', 'public') -Patterns @('.env*', 'package*.json', 'next.config.*', 'tsconfig.json')
    $buildId = Join-Path $webRoot '.next\BUILD_ID'
    $needsBuild = -not (Test-Path -LiteralPath $buildId)
    if (-not $needsBuild) {
        $needsBuild = $webInputTime -gt (Get-Item -LiteralPath $buildId).LastWriteTimeUtc -or
            -not (Test-Path -LiteralPath (Join-Path $webRoot '.next\prerender-manifest.json')) -or
            -not (Test-Path -LiteralPath (Join-Path $webRoot '.next\build-manifest.json'))
    }
    $apiStale = $apiListener -and $apiInputTime -gt $apiListener.CreationDate.ToUniversalTime()
    $webStale = $webListener -and ((Get-Item -LiteralPath $buildId -ErrorAction SilentlyContinue).LastWriteTimeUtc -gt $webListener.CreationDate.ToUniversalTime())

    if ($CheckOnly) {
        [pscustomobject]@{
            Project = $repoRoot
            ApiEnvironmentPresent = Test-Path -LiteralPath (Join-Path $apiRoot '.env')
            WebEnvironmentPresent = Test-Path -LiteralPath (Join-Path $webRoot '.env.local')
            ApiReady = Test-Api
            WebReady = Test-Web
            ApiRestartNeeded = [bool]$apiStale
            WebBuildNeeded = [bool]$needsBuild
            WebRestartNeeded = [bool]($webStale -or $needsBuild)
            PythonEnvironmentPresent = @($pythonCandidates | Where-Object { Test-Path -LiteralPath $_ }).Count -gt 0
            NextInstalled = Test-Path -LiteralPath (Join-Path $webRoot 'node_modules\next\dist\bin\next')
        } | Format-List
        return
    }

    $node = (Get-Command node.exe -ErrorAction Stop).Source
    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    $nodeVersion = [version]((& $node --version).TrimStart('v'))
    if ($nodeVersion -lt [version]'20.9.0') { throw 'Install Node.js 20.9 or newer before starting ClassGuard.' }
    foreach ($environment in @(@($apiRoot, '.env'), @($webRoot, '.env.local'))) {
        $target = Join-Path $environment[0] $environment[1]
        if (-not (Test-Path -LiteralPath $target)) {
            Copy-Item -LiteralPath (Join-Path $environment[0] '.env.example') -Destination $target
            if ($environment[1] -eq '.env.local') { $needsBuild = $true }
            elseif ($apiListener) { $apiStale = $true }
            Write-Warning "Created $target from its example. Configure Supabase before signing in."
        }
    }
    New-Item -ItemType Directory -Path $runRoot -Force | Out-Null

    $python = $null
    foreach ($candidate in $pythonCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            try {
                & $candidate -c 'import sys, fastapi, uvicorn, sqlalchemy, pydantic_settings, jwt; assert sys.version_info >= (3, 11)' 2>$null
                if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
            } catch { continue }
        }
    }
    if (-not $python) {
        $python = $pythonCandidates[0]
        if (-not (Test-Path -LiteralPath $python)) {
            $pythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
            if ($pythonLauncher) { Invoke-Checked $pythonLauncher.Source @('-3', '-m', 'venv', (Join-Path $apiRoot '.venv')) }
            else { Invoke-Checked (Get-Command python.exe -ErrorAction Stop).Source @('-m', 'venv', (Join-Path $apiRoot '.venv')) }
        }
        Invoke-Checked $python @('-c', 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"')
        Invoke-Checked $python @('-m', 'pip', 'install', '-r', (Join-Path $apiRoot 'requirements.txt'))
    }

    if ($apiListener -and ($apiStale -or -not (Test-Api))) {
        Write-Host 'Restarting the existing ClassGuard API to load its current configuration.'
        Stop-ProjectListener -Port 8000 -Service api -Expected $apiListener
        $apiListener = $null
    }
    $apiStarted = $null
    if (-not $apiListener) {
        Push-Location $apiRoot
        try { Invoke-Checked $python @('-m', 'classguard.cli', 'init-db') }
        finally { Pop-Location }
        $apiStarted = Start-HiddenService -Program $python -Arguments @('-m', 'uvicorn', 'classguard.main:app', '--app-dir', $apiRoot, '--host', '127.0.0.1', '--port', '8000', '--no-proxy-headers') -Directory $apiRoot -Service api
    }
    Wait-Ready -Service api -StartedProcess $apiStarted

    if ($webListener -and ($needsBuild -or $webStale -or -not (Test-Web))) {
        Write-Host 'Restarting the existing ClassGuard web app to load its current build.'
        Stop-ProjectListener -Port 3000 -Service web -Expected $webListener
        $webListener = $null
    }
    Push-Location $webRoot
    try {
        if (-not (Test-Path -LiteralPath 'node_modules\next\dist\bin\next')) {
            Invoke-Checked $npm @('ci')
            $needsBuild = $true
        }
        if ($needsBuild) { Invoke-Checked $npm @('run', 'build') }
    } finally { Pop-Location }
    $webStarted = $null
    if (-not $webListener) {
        $webStarted = Start-HiddenService -Program $node -Arguments @((Join-Path $webRoot 'node_modules\next\dist\bin\next'), 'start', '--hostname', '127.0.0.1', '--port', '3000') -Directory $webRoot -Service web
    }
    Wait-Ready -Service web -StartedProcess $webStarted
    $capabilities = Invoke-RestMethod 'http://127.0.0.1:8000/v1/capabilities' -TimeoutSec 5
    Write-Host "ClassGuard is ready: $appUrl" -ForegroundColor Green
    if (-not $capabilities.authentication_configured) { Write-Warning 'Supabase sign-in still needs configuration in the API and web environment files.' }
    Write-Host 'The services continue running in the background until Windows closes them or you restart your computer.'
    if (-not $NoBrowser) { Start-Process $appUrl }
} catch {
    Write-Host "ClassGuard startup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($mutexAcquired) { $startupMutex.ReleaseMutex() }
    if ($startupMutex) { $startupMutex.Dispose() }
}
