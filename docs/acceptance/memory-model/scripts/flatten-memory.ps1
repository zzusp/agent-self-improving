param(
    [Parameter(Mandatory = $true)]
    [string]$Root,
    [Parameter(Mandatory = $true)]
    [string]$Validator,
    [switch]$Check,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
if ($Check -eq $Apply) {
    throw "必须且只能指定 -Check 或 -Apply。"
}

$dataRoot = [IO.Path]::GetFullPath($Root)
$memoryPath = [IO.Path]::GetFullPath((Join-Path $dataRoot "memory"))
if (-not $memoryPath.StartsWith($dataRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "memory 路径越出数据根。"
}

$sourceFiles = @(Get-ChildItem -LiteralPath $memoryPath -Recurse -File -Filter "m-*.md")
$duplicates = @($sourceFiles | Group-Object Name | Where-Object Count -gt 1)
$projectsPath = Join-Path $memoryPath "projects"
$scopeFiles = if (Test-Path -LiteralPath $projectsPath) {
    @(Get-ChildItem -LiteralPath $projectsPath -Directory | ForEach-Object {
        Join-Path $_.FullName "scope.json"
    })
} else {
    @()
}
$precheck = [ordered]@{
    status = "ready"
    mode = "check"
    source_entries = $sourceFiles.Count
    duplicate_ids = $duplicates.Count
    scope_files = $scopeFiles.Count
    blockers = @()
}
if ($duplicates.Count -gt 0) {
    $precheck.blockers += "存在重复 memory id。"
}
if ((Test-Path -LiteralPath (Join-Path $memoryPath "current")) -or
    (Test-Path -LiteralPath (Join-Path $memoryPath "archive"))) {
    $precheck.blockers += "统一 memory 目录已经存在。"
}
if ((Get-Item -LiteralPath $memoryPath).LinkType) {
    $precheck.blockers += "memory 目录不能是链接或 junction。"
}
$memoryChildren = @(Get-ChildItem -LiteralPath $memoryPath | Select-Object -ExpandProperty Name)
$unexpectedChildren = @($memoryChildren | Where-Object { $_ -notin @("global", "projects") })
if ($unexpectedChildren.Count -gt 0) {
    $precheck.blockers += "memory 不是待迁移的 global/projects 旧布局。"
}
if ($precheck.blockers.Count -gt 0) {
    $precheck.status = "blocked"
}
if ($Check -or $precheck.status -ne "ready") {
    $precheck | ConvertTo-Json -Depth 4
    if ($precheck.status -ne "ready") { exit 1 }
    exit 0
}

$stage = Join-Path $dataRoot (".memory-unified-" + [guid]::NewGuid().ToString("N"))
$stageFull = [IO.Path]::GetFullPath($stage)
if (-not $stageFull.StartsWith(($dataRoot + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase) -or
    -not (Split-Path $stageFull -Leaf).StartsWith(".memory-unified-")) {
    throw "临时目录不在预期数据根内。"
}

$utf8NoBom = [Text.UTF8Encoding]::new($false)
New-Item -ItemType Directory -Path (Join-Path $stage "memory\current"), (Join-Path $stage "memory\archive") | Out-Null
Copy-Item -LiteralPath (Join-Path $dataRoot "knowledge") -Destination (Join-Path $stage "knowledge") -Recurse
Copy-Item -LiteralPath (Join-Path $dataRoot "recurrence") -Destination (Join-Path $stage "recurrence") -Recurse
foreach ($source in $sourceFiles) {
    $state = Split-Path $source.DirectoryName -Leaf
    if ($state -notin @("current", "archive")) {
        throw "发现未知 memory 状态目录：$($source.FullName)"
    }
    $destination = Join-Path (Join-Path $stage "memory\$state") $source.Name
    $text = [IO.File]::ReadAllText($source.FullName, [Text.Encoding]::UTF8)
    $text = [regex]::Replace($text, '(?m)^scope: repo:[^/\r\n]+/(.+)$', 'scope: $1')
    [IO.File]::WriteAllText($destination, $text, $utf8NoBom)
}

foreach ($index in @(
    @{ Directory = "memory\current"; Name = "MEMORY.md" },
    @{ Directory = "memory\archive"; Name = "INDEX.md" }
)) {
    $directory = Join-Path $stage $index.Directory
    $rendered = @(& python -B $Validator render-index --directory $directory)
    if ($LASTEXITCODE -ne 0) { throw "索引渲染失败：$directory" }
    [IO.File]::WriteAllText((Join-Path $directory $index.Name), (($rendered -join "`n") + "`n"), $utf8NoBom)
}

$stagedResult = @(& python -B $Validator check --root $stage --json)
if ($LASTEXITCODE -ne 0) {
    throw "临时数据根校验失败：$($stagedResult -join [Environment]::NewLine)"
}

$timestamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$backup = Join-Path $dataRoot "legacy\memory-project-buckets-$timestamp"
if (Test-Path -LiteralPath $backup) { throw "备份目录冲突：$backup" }
Move-Item -LiteralPath $memoryPath -Destination $backup
try {
    Move-Item -LiteralPath (Join-Path $stage "memory") -Destination $memoryPath
    $liveResult = @(& python -B $Validator check --root $dataRoot --json)
    if ($LASTEXITCODE -ne 0) {
        throw "安装后数据根校验失败：$($liveResult -join [Environment]::NewLine)"
    }
} catch {
    if (Test-Path -LiteralPath $memoryPath) {
        Move-Item -LiteralPath $memoryPath -Destination (Join-Path $stage "memory")
    }
    if (Test-Path -LiteralPath $backup) {
        Move-Item -LiteralPath $backup -Destination $memoryPath
    }
    throw
}

if (-not $stageFull.StartsWith(($dataRoot + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)) {
    throw "拒绝清理数据根外的临时目录。"
}
Remove-Item -LiteralPath $stageFull -Recurse -Force
$live = ($liveResult -join "`n") | ConvertFrom-Json
[ordered]@{
    status = $live.status
    mode = "apply"
    entries = $live.counts.entries
    failures = $live.counts.failures
    memory_current = $live.counts.directories.'memory/current'
    memory_archive = $live.counts.directories.'memory/archive'
    backup = $backup
} | ConvertTo-Json -Depth 4
