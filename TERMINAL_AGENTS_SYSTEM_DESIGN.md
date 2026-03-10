# Системный дизайн запуска терминальных AI-агентов на Windows

## Цель

Этот документ описывает рабочую архитектуру запуска четырех терминальных агентов:

- Codex
- Claude Code
- Gemini CLI
- OpenCode

Цель системы:

- запускать каждого агента в отдельной панели `Windows Terminal`
- поддерживать mixed-layout: один агент на одну панель
- поддерживать homogenous-layout: один агент во всех 4 панелях
- уметь передавать стартовый промпт при запуске
- уметь включать максимально permissive / YOLO-режим
- использовать стабильную схему, пригодную для встраивания в другую программу

---

## Главный вывод

Для Windows нельзя надежно строить длинные inline-команды внутри `wt ... powershell -Command ...`, если там:

- несколько выражений PowerShell
- переменные окружения
- кавычки
- позиционные промпты
- сложные CLI-флаги

Правильная схема:

1. Для каждого агента делать отдельный launch-script `.ps1`
2. Внутри скрипта:
   - задавать переменные окружения
   - собирать аргументы
   - вызывать конкретный CLI
3. В `wt` передавать только:

```powershell
powershell -NoExit -ExecutionPolicy Bypass -File <script.ps1> [-Prompt "..."]
```

Именно эта схема у нас оказалась устойчивой.

---

## Архитектура

### 1. Оркестратор терминала

Роль:

- открывает `Windows Terminal`
- строит layout из панелей
- решает, какой агент должен попасть в какую панель

Инструмент:

- `wt.exe`

### 2. Launch-script агента

Роль:

- нормализует окружение терминала
- включает permissive / YOLO-режим
- принимает стартовый промпт
- запускает конкретный агент

Инструмент:

- PowerShell `.ps1`

### 3. Агентный CLI

Роль:

- непосредственно поднимает TUI/CLI агента

### 4. Вызывающая программа

Это может быть:

- ваша программа на C#, Python, Node.js, Go
- GUI launcher
- backend orchestration service

Она не должна собирать сложную строку запуска агента сама. Она должна вызывать:

- `wt`
- готовые `.ps1` launchers

---

## Нормализация терминала

Во всех launch-script мы задаем:

```powershell
$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
$env:TERM_PROGRAM = 'Windows_Terminal'
```

Зачем:

- часть CLI определяет цвет через `TERM`
- часть через `COLORTERM`
- часть дополнительно смотрит на `TERM_PROGRAM`

Важно:

- это не гарантирует full-color для каждого TUI
- но это правильная и безопасная базовая настройка

---

## Матрица агентов

### Codex

- Исполняемый файл: `C:\Users\Brian\AppData\Roaming\npm\codex.ps1`
- Стартовый промпт: да, позиционный аргумент
- YOLO-режим: `--dangerously-bypass-approvals-and-sandbox`
- Локально подтверждено через `codex --help`

Пример:

```powershell
codex --dangerously-bypass-approvals-and-sandbox "Привет"
```

### Claude Code

- Исполняемый файл: `C:\Users\Brian\.local\bin\claude.exe`
- Стартовый промпт: да, позиционный аргумент
- YOLO-режим: `--dangerously-skip-permissions`
- Локально подтверждено через `claude --help`

Пример:

```powershell
claude --dangerously-skip-permissions "Привет"
```

### Gemini CLI

- Исполняемый файл: `C:\Users\Brian\AppData\Roaming\npm\gemini.ps1`
- Стартовый промпт: да, позиционный аргумент
- YOLO-режим: `--approval-mode=yolo`
- Официально documented

Пример:

```powershell
gemini --approval-mode=yolo "Привет"
```

### OpenCode

- Исполняемый файл: `C:\Users\Brian\AppData\Roaming\npm\opencode.ps1`
- Стартовый промпт: да, через `--prompt`
- Permissive / YOLO-эквивалент: `OPENCODE_CONFIG_CONTENT='{"permission":"allow"}'`
- Локально подтверждено через `opencode --help`

Пример:

```powershell
$env:OPENCODE_CONFIG_CONTENT='{"permission":"allow"}'
opencode --prompt "Привет"
```

---

## Что значит YOLO-режим

В этой системе YOLO означает:

- минимум подтверждений от пользователя
- максимально прямой доступ к инструментам агента
- высокая автономность выполнения команд

Это не единый стандарт. Для каждого агента он реализован по-разному:

- Codex: полный bypass approvals + sandbox
- Claude Code: skip permissions
- Gemini CLI: `approval-mode=yolo`
- OpenCode: permissive-конфиг через env

Важно:

- это опасный режим
- его нельзя включать без доверия к окружению и задаче
- в продовой программе он должен быть явной опцией, а не default

---

## Рабочие launch-scripts

### Codex

Файл: [codex-yolo-launch.ps1](C:\Users\Brian\codex-yolo-launch.ps1)

```powershell
param(
  [string]$Prompt
)

$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
$env:TERM_PROGRAM = 'Windows_Terminal'

$argsList = @('--dangerously-bypass-approvals-and-sandbox')

if ($Prompt) {
  $argsList += $Prompt
}

& 'C:\Users\Brian\AppData\Roaming\npm\codex.ps1' @argsList
```

### Claude Code

Файл: [claude-yolo-launch.ps1](C:\Users\Brian\claude-yolo-launch.ps1)

```powershell
param(
  [string]$Prompt
)

$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
$env:TERM_PROGRAM = 'Windows_Terminal'

$argsList = @('--dangerously-skip-permissions')

if ($Prompt) {
  $argsList += $Prompt
}

& 'C:\Users\Brian\.local\bin\claude.exe' @argsList
```

### Gemini

Файл: [gemini-yolo-launch.ps1](C:\Users\Brian\gemini-yolo-launch.ps1)

```powershell
param(
  [string]$Prompt
)

$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
$env:TERM_PROGRAM = 'Windows_Terminal'

$argsList = @('--approval-mode=yolo')

if ($Prompt) {
  $argsList += $Prompt
}

& 'C:\Users\Brian\AppData\Roaming\npm\gemini.ps1' @argsList
```

### OpenCode

Файл: [opencode-yolo-launch.ps1](C:\Users\Brian\opencode-yolo-launch.ps1)

```powershell
param(
  [string]$Prompt
)

$env:TERM = 'xterm-256color'
$env:COLORTERM = 'truecolor'
$env:TERM_PROGRAM = 'Windows_Terminal'
$env:OPENCODE_CONFIG_CONTENT = '{"permission":"allow"}'

$argsList = @()

if ($Prompt) {
  $argsList += '--prompt'
  $argsList += $Prompt
}

& 'C:\Users\Brian\AppData\Roaming\npm\opencode.ps1' @argsList
```

---

## Почему launch-script лучше inline-команды

Мы подтвердили это практически.

Проблемы inline-подхода:

- `wt` может неверно разбирать PowerShell-выражения
- куски `$env:...` могут интерпретироваться как отдельные команды
- ломается quoting
- сложнее передавать Unicode-промпты
- сложнее чинить различия между агентами

Преимущества launch-script:

- один агент = один контракт запуска
- легко передавать `-Prompt`
- легко менять env и флаги
- удобно переиспользовать из другой программы

---

## Layout recipes для Windows Terminal

### 1. Один агент в 4 панелях 2x2

Паттерн:

- старт первой панели
- `split-pane -V`
- `move-focus left`
- `split-pane -H`
- `move-focus right`
- `split-pane -H`

Это дает:

- слева сверху
- справа сверху
- слева снизу
- справа снизу

### 2. Mixed window 2x2

По одному агенту на панель:

- LT: Codex
- RT: Claude Code
- LB: Gemini
- RB: OpenCode

### 3. Один агент = одно окно

Можно поднимать:

- отдельное окно только с Codex 2x2
- отдельное окно только с Claude Code 2x2
- отдельное окно только с Gemini 2x2
- отдельное окно только с OpenCode 2x2

### 4. 4 отдельных окна

Каждое окно содержит свою 2x2 сетку одного агента.

### 5. Сколько панелей можно открыть

Практически:

- это ограничение не PowerShell
- это ограничение `Windows Terminal` и удобства интерфейса
- фиксированного малого лимита вроде `4` или `8` нет

Реальный предел определяется:

- размером экрана
- читаемостью TUI
- производительностью машины
- количеством одновременно работающих агентов

Практический рекомендуемый режим:

- `2-4` панели в одном окне для активной работы
- большее количество лучше раскладывать по нескольким окнам

---

## Готовые шаблоны запуска

### Mixed window 2x2 без промпта

```powershell
Start-Process wt -WorkingDirectory 'C:\Users\Brian' -ArgumentList @(
  '-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\codex-yolo-launch.ps1',
  ';',
  'split-pane','-V','-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\claude-yolo-launch.ps1',
  ';',
  'move-focus','left',
  ';',
  'split-pane','-H','-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\gemini-yolo-launch.ps1',
  ';',
  'move-focus','right',
  ';',
  'split-pane','-H','-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\opencode-yolo-launch.ps1'
)
```

### Mixed window 2x2 с промптом `Привет`

```powershell
Start-Process wt -WorkingDirectory 'C:\Users\Brian' -ArgumentList @(
  '-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\codex-yolo-launch.ps1','-Prompt','Привет',
  ';',
  'split-pane','-V','-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\claude-yolo-launch.ps1','-Prompt','Привет',
  ';',
  'move-focus','left',
  ';',
  'split-pane','-H','-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\gemini-yolo-launch.ps1','-Prompt','Привет',
  ';',
  'move-focus','right',
  ';',
  'split-pane','-H','-d','C:\Users\Brian','powershell','-NoExit','-ExecutionPolicy','Bypass','-File','C:\Users\Brian\opencode-yolo-launch.ps1','-Prompt','Привет'
)
```

### 4 окна, по одному агенту на окно

Принцип:

- каждый `Start-Process wt ...` создает отдельное окно
- внутри каждого окна строится своя 2x2 сетка

---

## Ограничения Windows Terminal / PowerShell

### Практические ограничения

- `PowerShell` в окружении пользователя не поддерживает `&&`
- для объединения нужно использовать `;` или отдельные вызовы
- heredoc в bash на Windows лучше не использовать
- длинные inline-команды внутри `wt` ненадежны

### Практические выводы

- аргументы для `wt` лучше передавать массивом
- логика запуска агента не должна жить внутри `wt`
- логика агента должна жить в отдельном `.ps1`

---

## Случай OpenCode: что сломалось и как чинить

Мы зафиксировали реальную проблему:

- `OpenCode` был установлен частично/битым образом
- вместо нормальных:
  - `opencode.ps1`
  - `opencode.cmd`
- были временные файлы вида:
  - `.opencode.ps1-*`
  - `.opencode.cmd-*`

Симптом:

- launcher не мог найти `opencode.ps1`

Решение:

```powershell
npm install -g opencode-ai
```

После этого восстановились:

- `C:\Users\Brian\AppData\Roaming\npm\opencode`
- `C:\Users\Brian\AppData\Roaming\npm\opencode.cmd`
- `C:\Users\Brian\AppData\Roaming\npm\opencode.ps1`

Для production-реализации это значит:

- перед запуском желательно делать preflight-check исполняемого файла
- если shim отсутствует, нужно выполнять repair/install flow

---

## Рекомендуемый API для другой программы

Если вы будете реализовывать это в другой программе, удобный контракт такой:

### Сущности

- `AgentType`: `codex | claude | gemini | opencode`
- `LaunchMode`: `single | grid4 | mixed4`
- `Prompt`: nullable string
- `WorkingDirectory`: absolute path
- `ApprovalMode`: `safe | yolo`

### Правила

- `grid4 + single agent` => одно окно, 4 панели, один и тот же launcher
- `mixed4` => одно окно, 4 панели, 4 разных launcher
- `Prompt != null` => передавать через `-Prompt`
- `ApprovalMode=yolo` => использовать соответствующий launcher

### Preflight-check

Перед запуском проверить:

- существует ли launcher `.ps1`
- существует ли основной CLI binary/script
- существует ли `wt.exe`
- существует ли рабочая директория

### Recovery-check

Если `OpenCode` не найден:

- предложить repair: `npm install -g opencode-ai`

---

## Что реально протестировано

Практически проверено на этой машине:

- Codex 2x2
- Claude Code 2x2
- Gemini 2x2
- OpenCode 2x2
- mixed-window 2x2
- передача стартового промпта `Привет`
- работа launch-script через `powershell -File`
- восстановление OpenCode после битого shim

---

## Источники

Официальные и первичные источники:

- OpenAI Codex CLI: точные флаги подтверждены локально через `codex --help`; общий продуктовый контекст Codex: https://developers.openai.com/codex
- Claude Code CLI help и permissions: https://docs.anthropic.com/en/docs/claude-code/overview
- Gemini CLI reference: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/cli-reference.md
- Gemini CLI repository: https://github.com/google-gemini/gemini-cli
- OpenCode repository / project: https://github.com/sst/opencode

Важно:

- Для Codex и OpenCode точный синтаксис запуска в этом документе опирается прежде всего на локально подтвержденный `--help` и на фактические успешные прогоны на этой машине.
- Для Gemini часть утверждений о `approval-mode=yolo` взята из официального CLI reference.
- Для Claude Code флаг `--dangerously-skip-permissions` подтвержден локально и соответствует официальной документации Anthropic.
