<#
    일일 파이프라인 실행기 — Windows 작업 스케줄러가 새벽에 호출한다.

      .\run_daily.ps1                 정상 실행
      .\run_daily.ps1 -DryRun         조사·검증까지만, 카드 렌더 안 함
      .\run_daily.ps1 -Bypass         권한 허용목록 무시 (허용목록이 막을 때만)
      .\run_daily.ps1 -TimeoutMin 90  기본 75분

    실행 중 시스템이 다시 잠들지 않도록 sleep 을 차단한다.
    (절전에서 깨워 돌리는 구성이라 이게 없으면 작업 도중 다시 잠들 수 있다.)
#>

[CmdletBinding()]
param(
    [switch] $DryRun,
    [switch] $Bypass,
    [int]    $TimeoutMin = 75
)

$ErrorActionPreference = 'Stop'

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Here

$LogDir = Join-Path $Root 'logs'
$OutDir = Join-Path $Root 'output'
$StateDir = Join-Path $Root 'state'
foreach ($d in @($LogDir, $OutDir, $StateDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
}

$Stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$Log = Join-Path $LogDir ((Get-Date -Format 'yyyy-MM-dd') + '.log')

function Write-Log {
    param([string] $Message, [string] $Level = 'INFO')
    $line = '[{0}] {1,-5} {2}' -f (Get-Date -Format 'HH:mm:ss'), $Level, $Message
    Add-Content -Path $Log -Value $line -Encoding utf8
    Write-Host $line
}

# ── 실행 중 절전 차단 ────────────────────────────────────────────────────
$sleepBlocked = $false
try {
    if (-not ('Pwr' -as [type])) {
        Add-Type -Namespace '' -Name 'Pwr' -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
    }
    # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x01)
    # PowerShell 은 0x80000001 을 Int32 로 읽어 음수로 만든다. uint32 로 명시해야 한다.
    [void][Pwr]::SetThreadExecutionState([uint32]2147483649)
    $sleepBlocked = $true
} catch {
    Write-Log "절전 차단 실패 (계속 진행): $($_.Exception.Message)" 'WARN'
}

$claude = $null
$exit = 1
try {
    Write-Log '─────────────────────────────────────────────'
    Write-Log "파이프라인 시작  (DryRun=$DryRun, Bypass=$Bypass, Timeout=${TimeoutMin}m)"

    # ── config.json ─────────────────────────────────────────────────────
    $cfg = $null
    $cfgPath = Join-Path $Here 'config.json'
    if (Test-Path $cfgPath) {
        try { $cfg = Get-Content $cfgPath -Raw -Encoding utf8 | ConvertFrom-Json }
        catch { Write-Log "config.json 파싱 실패, 자동 탐색으로 진행: $($_.Exception.Message)" 'WARN' }
    }
    if ($cfg -and $cfg.schedule -and $cfg.schedule.run_timeout_min -and
        -not $PSBoundParameters.ContainsKey('TimeoutMin')) {
        $TimeoutMin = [int]$cfg.schedule.run_timeout_min
    }

    # ── claude.exe 찾기 ─────────────────────────────────────────────────
    $claudeExe = $env:HCI_CLAUDE_PATH
    if ((-not $claudeExe -or -not (Test-Path $claudeExe)) -and $cfg -and $cfg.claude_path) {
        if (Test-Path $cfg.claude_path) { $claudeExe = $cfg.claude_path }
        else { Write-Log "config.json 의 claude_path 가 없는 경로다 — 자동 탐색으로 넘어간다" 'WARN' }
    }
    if (-not $claudeExe -or -not (Test-Path $claudeExe)) {
        $cand = Get-ChildItem -Path "$env:LOCALAPPDATA\Packages" -Filter 'claude.exe' `
                    -Recurse -Depth 8 -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($cand) { $claudeExe = $cand.FullName }
    }
    if (-not $claudeExe) { $g = Get-Command claude -ErrorAction SilentlyContinue; if ($g) { $claudeExe = $g.Source } }
    if (-not $claudeExe) { throw 'claude.exe 를 찾을 수 없다. HCI_CLAUDE_PATH 환경변수로 지정하라.' }
    Write-Log "claude: $claudeExe"

    # ── codex.exe 확인 (검증 게이트에 필수) ─────────────────────────────
    $codexExe = $env:HCI_CODEX_PATH
    if ((-not $codexExe -or -not (Test-Path $codexExe)) -and $cfg -and $cfg.codex_path) {
        if (Test-Path $cfg.codex_path) { $codexExe = $cfg.codex_path }
        else { Write-Log "config.json 의 codex_path 가 없는 경로다 — 자동 탐색으로 넘어간다" 'WARN' }
    }
    if (-not $codexExe -or -not (Test-Path $codexExe)) {
        $cand = Get-ChildItem -Path "$env:LOCALAPPDATA\OpenAI\Codex\bin" -Filter 'codex.exe' `
                    -Recurse -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($cand) { $codexExe = $cand.FullName }
    }
    if (-not $codexExe) { throw 'codex.exe 를 찾을 수 없다. GPT 검증 게이트 없이는 실행하지 않는다.' }
    $env:HCI_CODEX_PATH = $codexExe
    Write-Log "codex:  $codexExe"

    # ── 인증 ────────────────────────────────────────────────────────────
    # 두 가지 방식을 다 받는다.
    #   (1) claude 대화형 /login  → ~/.claude/.credentials.json 에 저장됨
    #   (2) claude setup-token    → 사용자 환경변수 CLAUDE_CODE_OAUTH_TOKEN
    # setx 로 넣은 사용자 환경변수는 이미 떠 있는 셸에 반영되지 않으므로
    # 레지스트리에서 직접 읽어 자식 프로세스에 넘긴다. 값은 절대 로그에 찍지 않는다.
    if (-not $env:CLAUDE_CODE_OAUTH_TOKEN) {
        $tok = [Environment]::GetEnvironmentVariable('CLAUDE_CODE_OAUTH_TOKEN', 'User')
        if ($tok) { $env:CLAUDE_CODE_OAUTH_TOKEN = $tok }
    }
    $credFile = Join-Path $env:USERPROFILE '.claude\.credentials.json'
    if ($env:CLAUDE_CODE_OAUTH_TOKEN) {
        Write-Log "인증: CLAUDE_CODE_OAUTH_TOKEN (길이 $($env:CLAUDE_CODE_OAUTH_TOKEN.Length))"
    } elseif (Test-Path $credFile) {
        Write-Log '인증: 저장된 자격증명 파일'
    } else {
        throw ('인증 정보가 없다. 프로젝트 폴더에서 claude 를 한 번 실행해 /login 하거나, ' +
               'claude setup-token 으로 받은 토큰을 setx CLAUDE_CODE_OAUTH_TOKEN 으로 넣어라.')
    }

    # 인자로 넘어가므로 줄바꿈 없이 한 줄로 둔다.
    $kick = 'automation/pipeline_prompt.md 를 읽고 그 지시를 처음부터 끝까지 수행하라. ' +
            '사람은 자고 있다. 질문하지 말고, 막히면 STATUS 와 NOTES.md 를 남기고 종료하라.'
    if ($DryRun) {
        $kick += ' [DRY RUN] 4단계 GPT 교차검증까지만 수행하고 5단계 카드 렌더는 하지 마라. STATUS 에 dry_run 이라고 적어라.'
    }

    $cliArgs = @('-p', $kick, '--output-format', 'text')

    # 무인 실행 전용 제약: 인스타 발행 차단 + 파이프라인 자기수정 차단
    $unattended = Join-Path $Here 'unattended_settings.json'
    if (Test-Path $unattended) {
        $cliArgs += @('--settings', $unattended)
    } else {
        Write-Log 'unattended_settings.json 이 없다 — 발행 차단 규칙 없이 실행된다' 'WARN'
    }

    if ($Bypass) {
        $cliArgs += @('--permission-mode', 'bypassPermissions')
        Write-Log '권한 허용목록 우회 모드' 'WARN'
    } else {
        $cliArgs += @('--permission-mode', 'acceptEdits')
    }

    $so = Join-Path $LogDir "run_${Stamp}.out.txt"
    $se = Join-Path $LogDir "run_${Stamp}.err.txt"

    # Start-Process -ArgumentList 는 배열을 공백으로 이어붙일 뿐 따옴표를 붙여주지
    # 않는다. 프로젝트 경로에 공백과 한글이 있어 그대로 넘기면 인자가 토막난다.
    $argLine = ($cliArgs | ForEach-Object {
        if ($_ -eq '') { '""' }
        elseif ($_ -notmatch '[\s"]') { $_ }
        else { '"' + ($_ -replace '"', '\"') + '"' }
    }) -join ' '

    Write-Log 'claude 헤드리스 세션 시작 …'
    $t0 = Get-Date
    $proc = Start-Process -FilePath $claudeExe -ArgumentList $argLine `
                -WorkingDirectory $Root -NoNewWindow -PassThru `
                -RedirectStandardOutput $so -RedirectStandardError $se

    # Handle 를 한 번 만져줘야 .NET 이 프로세스 핸들을 붙잡아 두고,
    # 종료 후에도 ExitCode 를 읽을 수 있다. 안 하면 $null 이 나온다.
    $null = $proc.Handle

    $done = $proc.WaitForExit($TimeoutMin * 60 * 1000)
    if (-not $done) {
        Write-Log "타임아웃 ${TimeoutMin}분 초과 — 세션을 종료한다" 'ERROR'
        try { $proc.Kill($true) } catch { try { $proc.Kill() } catch {} }
        $exit = 124
    } else {
        $proc.WaitForExit()          # ExitCode 를 읽으려면 완전히 끝나야 한다
        $exit = $proc.ExitCode
    }
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    Write-Log "claude 종료  exit=$exit  ${mins}분"

    if (Test-Path $so) {
        $tail = Get-Content $so -Tail 40 -Encoding utf8 -ErrorAction SilentlyContinue
        if ($tail) { Write-Log "── 출력 끝부분 ──`n$($tail -join "`n")" }
    }
    if ((Test-Path $se) -and (Get-Item $se).Length -gt 0) {
        $errTail = Get-Content $se -Tail 25 -Encoding utf8 -ErrorAction SilentlyContinue
        if ($errTail) { Write-Log "stderr:`n$($errTail -join "`n")" 'WARN' }
    }

    # ── 오늘 결과 폴더 확인 ─────────────────────────────────────────────
    $today = Get-Date -Format 'yyyyMMdd'
    $folder = Get-ChildItem $OutDir -Directory -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -like "$today*" } |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1

    $status = 'no_output'
    $pngs = 0
    if ($folder) {
        $sf = Join-Path $folder.FullName 'STATUS'
        if (Test-Path $sf) { $status = (Get-Content $sf -Raw).Trim() }
        $pngs = @(Get-ChildItem $folder.FullName -Filter 'slide_*.png' -ErrorAction SilentlyContinue).Count
        Write-Log "결과: $($folder.Name)  status=$status  PNG=${pngs}장"
    } else {
        Write-Log '오늘 날짜의 결과 폴더가 없다' 'WARN'
    }

    $summary = [ordered]@{
        started_at = $t0.ToString('s')
        minutes    = $mins
        exit_code  = $exit
        status     = $status
        folder     = if ($folder) { $folder.Name } else { $null }
        slides     = $pngs
        dry_run    = [bool]$DryRun
    }
    $summary | ConvertTo-Json | Out-File (Join-Path $StateDir 'last_run.json') -Encoding utf8

    if ($status -ne 'awaiting_human_review' -and -not $DryRun) {
        Write-Log "사람 확인 필요 — status=$status" 'WARN'
    }
    Write-Log '파이프라인 종료'
}
catch {
    Write-Log "치명적 오류: $($_.Exception.Message)" 'ERROR'
    Write-Log $_.ScriptStackTrace 'ERROR'
    $exit = 1
}
finally {
    if ($sleepBlocked) {
        try { [void][Pwr]::SetThreadExecutionState([uint32]2147483648) } catch {}
    }
    # 로그 30일치만 보관
    Get-ChildItem $LogDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

exit $exit
