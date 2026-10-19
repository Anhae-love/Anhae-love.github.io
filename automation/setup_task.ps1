<#
    Windows 작업 스케줄러 등록기.

      .\setup_task.ps1                등록 / 갱신 (매일 03:00 + 최대 2시간 랜덤 지연)
      .\setup_task.ps1 -Show          현재 등록 상태와 다음 실행 시각
      .\setup_task.ps1 -RunNow        지금 한 번 실행
      .\setup_task.ps1 -Remove        등록 해제
      .\setup_task.ps1 -At 02:30 -WindowHours 3

    '매일 새벽 3~5시 사이'는 03:00 고정 시작 + 최대 2시간 랜덤 지연으로 만든다.
    따라서 실제 시작 시각은 날마다 다르다.
#>

[CmdletBinding()]
param(
    [string] $TaskName = 'HCI 인스타 일일 콘텐츠',
    [string] $At = '03:00',
    [int]    $WindowHours = 2,
    [switch] $Show,
    [switch] $RunNow,
    [switch] $Remove
)

$ErrorActionPreference = 'Stop'

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Here 'run_daily.ps1'
if (-not (Test-Path $Runner)) { throw "run_daily.ps1 이 없다: $Runner" }

function Show-Task {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { Write-Host "등록되어 있지 않다: '$TaskName'"; return }
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    $trg = $t.Triggers[0]
    Write-Host ''
    Write-Host "작업       : $TaskName"
    Write-Host "상태       : $($t.State)"
    Write-Host "시작 시각  : $($trg.StartBoundary)"
    Write-Host "랜덤 지연  : $($trg.RandomDelay)"
    Write-Host "깨워서 실행: $($t.Settings.WakeToRun)"
    Write-Host "다음 실행  : $($i.NextRunTime)"
    Write-Host "마지막 실행: $($i.LastRunTime)  (결과 $($i.LastTaskResult))"
    Write-Host ''
}

if ($Show)   { Show-Task; return }

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "등록 해제했다: '$TaskName'"
    return
}

if ($RunNow) {
    if (-not (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
        throw "등록되어 있지 않다. 먼저 .\setup_task.ps1 을 실행하라."
    }
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "실행 요청했다. 진행 상황은 logs\$(Get-Date -Format 'yyyy-MM-dd').log 에서 확인."
    return
}

# ── 등록 ────────────────────────────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}"' -f $Runner) `
    -WorkingDirectory (Split-Path -Parent $Here)

$trigger = New-ScheduledTaskTrigger -Daily -At $At
# 작업 스케줄러 XML은 ISO 8601 기간 문자열만 받는다. TimeSpan 을 넣으면 "02:00:00" 으로
# 직렬화되어 등록이 거부된다.
$trigger.RandomDelay = 'PT{0}H' -f $WindowHours

$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 20)

# 유휴 상태가 아니어도 실행되게 한다 (새벽엔 유휴지만, 조건으로 걸면 취소될 수 있다)
$settings.RunOnlyIfIdle = $false
$settings.IdleSettings.StopOnIdleEnd = $false
$settings.DisallowStartIfOnBatteries = $false

# 사용자가 로그온해 있을 때만 실행 — 비밀번호 저장 불필요,
# 그리고 claude/codex 의 로그인 자격을 그대로 쓸 수 있다.
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

# Register-ScheduledTask 는 XML 거부를 비종료 오류로 뱉는다. 실제로 등록됐는지 확인한다.
if (-not (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
    throw "등록에 실패했다. 위의 오류 메시지를 확인하라."
}

$from = [datetime]::Parse($At)
Write-Host ''
Write-Host "등록 완료: '$TaskName'"
Write-Host ("  실행 창  : {0} ~ {1} 사이 랜덤" -f $from.ToString('HH:mm'), $from.AddHours($WindowHours).ToString('HH:mm'))
Write-Host "  절전 상태면 깨워서 실행한다 (사용자가 로그온되어 있어야 함)"
Write-Host "  놓친 실행은 다음에 PC가 켜졌을 때 따라 실행한다"
Show-Task
Write-Host "지금 한 번 테스트: .\setup_task.ps1 -RunNow"
Write-Host ''
