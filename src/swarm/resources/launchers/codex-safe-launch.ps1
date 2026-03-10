param(
  [string]$Prompt,
  [string]$SessionId,
  [string]$AgentName
)

$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
$env:TERM_PROGRAM = 'Windows_Terminal'

# Записать PID для swarm terminal stop
if ($SessionId -and $AgentName) {
  $pidDir = Join-Path (Get-Location) '.swarm_pids'
  New-Item -ItemType Directory -Path $pidDir -Force | Out-Null
  $PID | Out-File -FilePath (Join-Path $pidDir "${SessionId}_${AgentName}.pid") -NoNewline -Encoding ascii
}

$argsList = @()
if ($Prompt) {
  $argsList += $Prompt
}

& 'codex' @argsList
