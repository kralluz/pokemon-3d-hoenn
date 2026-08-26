<#
.SYNOPSIS
    Compacta os discos virtuais do WSL/Docker para devolver espaco ao Windows.

.DESCRIPTION
    Depois de um "docker system prune", o espaco fica livre DENTRO do disco
    virtual, mas o arquivo .vhdx nao encolhe sozinho -- continua ocupando o
    mesmo tamanho no disco. Este script desliga o WSL e roda o "compact vdisk"
    do diskpart em cada .vhdx encontrado.

    NAO apaga dados: compactar so devolve o espaco ja marcado como livre.
    Precisa de administrador -- o script se auto-eleva.

    Tudo e gravado em tools\compact-log.txt, entao mesmo que a janela feche
    da para ver o que aconteceu.

.PARAMETER Force
    Nao pergunta antes de compactar.

.PARAMETER MinimumGB
    Ignora arquivos menores que isso (padrao: 1 GB).

.PARAMETER Elevated
    Uso interno: marca que ja estamos na instancia elevada.

.EXAMPLE
    .\Compact-Vhdx.ps1
    .\Compact-Vhdx.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [double]$MinimumGB = 1,
    [switch]$Elevated
)

# Deliberadamente NAO usamos ErrorActionPreference='Stop' global: chamadas a
# executaveis nativos (wsl.exe, diskpart.exe) podem virar erro no PowerShell 5.1
# e derrubar o script no meio. Os erros sao tratados caso a caso.
$ErrorActionPreference = 'Continue'

$logPath = Join-Path $PSScriptRoot 'compact-log.txt'

function Write-Log {
    param([string]$Message, [string]$Color = 'Gray')
    $line = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $Message
    Write-Host $line -ForegroundColor $Color
    try { Add-Content -Path $logPath -Value $line -Encoding UTF8 } catch { }
}

function Pause-Exit {
    param([int]$Code = 0)
    Write-Host ""
    Write-Host "Log completo: $logPath" -ForegroundColor DarkGray
    Write-Host "Pressione Enter para fechar..." -ForegroundColor DarkGray
    try { [void](Read-Host) } catch { Start-Sleep -Seconds 30 }
    exit $Code
}

# tudo daqui pra baixo protegido: qualquer excecao vira mensagem + pausa,
# em vez de a janela sumir sem explicacao
try {

"=== nova execucao {0:yyyy-MM-dd HH:mm:ss} ===" -f (Get-Date) |
    Add-Content -Path $logPath -Encoding UTF8 -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- elevacao

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Log "administrador = $isAdmin | elevated = $Elevated"

if (-not $isAdmin) {
    if ($Elevated) {
        Write-Log "Ja tentei elevar e ainda nao sou admin. Abortando." 'Red'
        Write-Host ""
        Write-Host "Sua conta pode nao ter direito de administrador." -ForegroundColor Yellow
        Pause-Exit 1
    }

    Write-Log "Sem privilegio -- pedindo elevacao (UAC)..." 'Yellow'

    $argList = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $PSCommandPath),
        '-Elevated'
    )
    if ($Force) { $argList += '-Force' }
    $argList += @('-MinimumGB', $MinimumGB.ToString([System.Globalization.CultureInfo]::InvariantCulture))

    Write-Log ("argumentos: " + ($argList -join ' '))

    try {
        Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList -ErrorAction Stop
        Write-Log "Janela elevada aberta. Continue por la." 'Green'
        Start-Sleep -Seconds 2
        exit 0
    } catch {
        Write-Log ("Elevacao recusada ou falhou: " + $_.Exception.Message) 'Red'
        Pause-Exit 1
    }
}

function Get-FreeGB { [math]::Round((Get-PSDrive C).Free / 1GB, 2) }

$freeBefore = Get-FreeGB
Write-Log "Espaco livre em C: $freeBefore GB" 'Green'

# ---------------------------------------------------------------- localiza os VHDX

Write-Log "Procurando discos virtuais..." 'Cyan'

$searchRoots = @(
    (Join-Path $env:LOCALAPPDATA 'Docker'),
    (Join-Path $env:LOCALAPPDATA 'wsl'),
    (Join-Path $env:LOCALAPPDATA 'Packages')
) | Where-Object { Test-Path $_ }

Write-Log ("procurando em: " + ($searchRoots -join ' ; '))

$vhdxFiles = @()
foreach ($root in $searchRoots) {
    $found = Get-ChildItem -Path $root -Filter '*.vhdx' -Recurse -File -ErrorAction SilentlyContinue
    if ($found) { $vhdxFiles += $found }
}

# swap.vhdx e recriado a cada boot do WSL: compactar nao adianta
$vhdxFiles = @($vhdxFiles |
    Where-Object { $_.Name -ne 'swap.vhdx' -and ($_.Length / 1GB) -ge $MinimumGB } |
    Sort-Object Length -Descending)

Write-Log "encontrados: $($vhdxFiles.Count) arquivo(s) acima de $MinimumGB GB"

if ($vhdxFiles.Count -eq 0) {
    Write-Log "Nada a compactar." 'Yellow'
    Pause-Exit 0
}

$totalGB = [math]::Round(($vhdxFiles | Measure-Object -Property Length -Sum).Sum / 1GB, 2)
Write-Host ""
foreach ($f in $vhdxFiles) {
    Write-Log ("{0,8:N2} GB  {1}" -f ($f.Length / 1GB), $f.FullName)
}
Write-Log "total: $totalGB GB" 'Cyan'

if (-not $Force) {
    Write-Host ""
    Write-Host "Isso vai DESLIGAR o Docker Desktop e o WSL (reversivel: e so reabrir)." -ForegroundColor Yellow
    Write-Host "Compactar NAO apaga dados -- so devolve o espaco ja livre por dentro." -ForegroundColor Yellow
    $answer = Read-Host "`nContinuar? [s/N]"
    if ($answer -notmatch '^[sSyY]') {
        Write-Log "Cancelado pelo usuario." 'Yellow'
        Pause-Exit 0
    }
}

# ---------------------------------------------------------------- desliga WSL/Docker

Write-Log "Desligando Docker Desktop e WSL..." 'Cyan'

foreach ($procName in @('Docker Desktop', 'com.docker.backend', 'com.docker.build', 'vpnkit', 'wslservice')) {
    $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        Write-Log "  parando $($p.Name) (pid $($p.Id))"
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
}

Start-Sleep -Seconds 3

# sem 2>&1: no PowerShell 5.1 isso transforma a saida de erro de um exe nativo
# em ErrorRecord e pode derrubar o script
$null = & wsl.exe --shutdown
Start-Sleep -Seconds 6
Write-Log "  WSL desligado."

# ---------------------------------------------------------------- compacta

function Test-FileUnlocked {
    param([string]$Path)
    try {
        $stream = [System.IO.File]::Open($Path, 'Open', 'ReadWrite', 'None')
        $stream.Close()
        $stream.Dispose()
        return $true
    } catch {
        return $false
    }
}

$results = @()

foreach ($vhdx in $vhdxFiles) {
    $sizeBefore = [math]::Round($vhdx.Length / 1GB, 2)
    Write-Host ""
    Write-Log "Compactando ($sizeBefore GB): $($vhdx.Name)" 'Cyan'
    Write-Log "  $($vhdx.FullName)"

    $unlocked = $false
    for ($try = 1; $try -le 15; $try++) {
        if (Test-FileUnlocked -Path $vhdx.FullName) { $unlocked = $true; break }
        Write-Log "  aguardando liberar (tentativa $try/15)..."
        Start-Sleep -Seconds 2
    }
    if (-not $unlocked) {
        Write-Log "  PULADO: arquivo continua em uso." 'Red'
        $results += [PSCustomObject]@{ Arquivo = $vhdx.Name; AntesGB = $sizeBefore; DepoisGB = $sizeBefore; Status = 'em uso' }
        continue
    }

    $script = @"
select vdisk file="$($vhdx.FullName)"
attach vdisk readonly
compact vdisk
detach vdisk
exit
"@
    $scriptPath = Join-Path $env:TEMP ("compact_{0}.txt" -f [guid]::NewGuid())
    # diskpart nao aceita UTF-8 com BOM (o padrao do PowerShell) -- precisa ser ASCII
    [System.IO.File]::WriteAllText($scriptPath, $script, [System.Text.Encoding]::ASCII)
    Write-Log "  rodando diskpart (isso pode levar varios minutos, sem barra de progresso)..."

    $sw = [Diagnostics.Stopwatch]::StartNew()
    $outFile = Join-Path $env:TEMP ("compact_out_{0}.txt" -f [guid]::NewGuid())
    try {
        $proc = Start-Process -FilePath 'diskpart.exe' -ArgumentList '/s', ('"{0}"' -f $scriptPath) `
            -NoNewWindow -Wait -PassThru -RedirectStandardOutput $outFile
        $exitCode = $proc.ExitCode
    } catch {
        Write-Log ("  ERRO ao chamar diskpart: " + $_.Exception.Message) 'Red'
        $exitCode = -1
    }
    $sw.Stop()

    $output = @()
    if (Test-Path $outFile) {
        $output = Get-Content $outFile -ErrorAction SilentlyContinue
        Remove-Item $outFile -ErrorAction SilentlyContinue
    }
    Remove-Item $scriptPath -ErrorAction SilentlyContinue

    $sizeAfter = [math]::Round((Get-Item $vhdx.FullName -ErrorAction SilentlyContinue).Length / 1GB, 2)
    $saved = [math]::Round($sizeBefore - $sizeAfter, 2)

    if ($exitCode -eq 0) {
        Write-Log ("  OK em {0:N0}s: {1} GB -> {2} GB (liberou {3} GB)" -f `
            $sw.Elapsed.TotalSeconds, $sizeBefore, $sizeAfter, $saved) 'Green'
        $status = 'ok'
    } else {
        Write-Log "  FALHOU (codigo $exitCode)" 'Red'
        foreach ($line in ($output | Select-Object -Last 10)) { Write-Log "    $line" }
        $status = "erro $exitCode"
    }

    $results += [PSCustomObject]@{
        Arquivo = $vhdx.Name; AntesGB = $sizeBefore; DepoisGB = $sizeAfter; Status = $status
    }
}

# ---------------------------------------------------------------- resumo

Write-Host ""
Write-Log "Resumo:" 'Cyan'
$results | Format-Table -AutoSize | Out-String | Write-Host

$freeAfter = Get-FreeGB
$gained = [math]::Round($freeAfter - $freeBefore, 2)

Write-Log ("Espaco livre em C: {0} GB -> {1} GB" -f $freeBefore, $freeAfter) 'Green'
if ($gained -gt 0) {
    Write-Log ("Ganho: {0} GB" -f $gained) 'Green'
} else {
    Write-Log "Sem ganho -- os discos ja estavam compactos." 'Yellow'
}
Write-Host ""
Write-Host "O Docker Desktop volta ao normal na proxima vez que voce abrir." -ForegroundColor DarkGray

Pause-Exit 0

} catch {
    Write-Log "ERRO INESPERADO:" 'Red'
    Write-Log ("  " + $_.Exception.Message) 'Red'
    Write-Log ("  em: " + $_.InvocationInfo.PositionMessage) 'Red'
    Pause-Exit 1
}
