param(
    [Parameter(Mandatory = $false)]
    [string]$WebUiUrl = "http://localhost:3030",

    [Parameter(Mandatory = $false)]
    [string]$ApiKey = $env:OPENWEBUI_API_KEY,

    [Parameter(Mandatory = $false)]
    [string]$KnowledgeName = "global-attachments",

    [Parameter(Mandatory = $false)]
    [string]$KnowledgeDescription = "Auto-managed knowledge base for persistent file retrieval across chats.",

    [Parameter(Mandatory = $true)]
    [string]$Path,

    [Parameter(Mandatory = $false)]
    [switch]$Recurse,

    [Parameter(Mandatory = $false)]
    [int]$ProcessTimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"

function Invoke-CurlJson {
    param(
        [string]$Method,
        [string]$Url,
        [string]$Token,
        [string]$JsonBody
    )

    $args = @(
        "-sS",
        "-X", $Method,
        "-H", "Authorization: Bearer $Token",
        "-H", "Content-Type: application/json"
    )

    if ($JsonBody) {
        $args += @("--data", $JsonBody)
    }

    $args += $Url
    $resp = & curl.exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed for $Method $Url"
    }

    if ([string]::IsNullOrWhiteSpace($resp)) {
        return $null
    }

    return ($resp | ConvertFrom-Json)
}

function Get-AllKnowledgeBases {
    param(
        [string]$BaseUrl,
        [string]$Token
    )

    $all = @()
    $page = 1

    while ($true) {
        $url = "$BaseUrl/api/v1/knowledge?page=$page"
        $resp = Invoke-CurlJson -Method "GET" -Url $url -Token $Token

        if (-not $resp -or -not $resp.items) {
            break
        }

        $items = @($resp.items)
        if ($items.Count -eq 0) {
            break
        }

        $all += $items

        if (-not $resp.total -or $all.Count -ge [int]$resp.total) {
            break
        }

        $page += 1
    }

    return ,$all
}

function Get-OrCreateKnowledgeBase {
    param(
        [string]$BaseUrl,
        [string]$Token,
        [string]$Name,
        [string]$Description
    )

    $kbs = Get-AllKnowledgeBases -BaseUrl $BaseUrl -Token $Token
    $existing = $kbs | Where-Object { $_.name -eq $Name } | Select-Object -First 1

    if ($existing) {
        Write-Host "Using existing knowledge base: $($existing.name) ($($existing.id))" -ForegroundColor Cyan
        return $existing
    }

    Write-Host "Creating knowledge base: $Name" -ForegroundColor Cyan
    $payload = @{ 
        name = $Name
        description = $Description
        access_grants = @()
    } | ConvertTo-Json -Depth 5 -Compress

    $created = Invoke-CurlJson -Method "POST" -Url "$BaseUrl/api/v1/knowledge/create" -Token $Token -JsonBody $payload
    if (-not $created -or -not $created.id) {
        throw "Failed to create knowledge base '$Name'."
    }

    return $created
}

function Upload-FileAndAutoLink {
    param(
        [string]$BaseUrl,
        [string]$Token,
        [string]$FilePath,
        [string]$KnowledgeId
    )

    $metadata = @{ knowledge_id = $KnowledgeId } | ConvertTo-Json -Compress

    $args = @(
        "-sS",
        "-X", "POST",
        "-H", "Authorization: Bearer $Token",
        "-F", "file=@$FilePath",
        "--form-string", "metadata=$metadata",
        "$BaseUrl/api/v1/files/"
    )

    $resp = & curl.exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "Upload failed for '$FilePath'."
    }

    $obj = $resp | ConvertFrom-Json
    if (-not $obj.id) {
        throw "Upload succeeded but no file id returned for '$FilePath'."
    }

    return $obj.id
}

function Wait-ForFileProcessing {
    param(
        [string]$BaseUrl,
        [string]$Token,
        [string]$FileId,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        $statusResp = Invoke-CurlJson -Method "GET" -Url "$BaseUrl/api/v1/files/$FileId/process/status" -Token $Token
        $status = $statusResp.status

        if ($status -eq "completed") {
            return
        }

        if ($status -eq "failed") {
            $err = $statusResp.error
            throw "File processing failed for '$FileId': $err"
        }

        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for file '$FileId' processing after $TimeoutSeconds seconds."
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "OPENWEBUI_API_KEY is not set. Pass -ApiKey or set OPENWEBUI_API_KEY in your environment."
}

if (-not (Test-Path $Path)) {
    throw "Path not found: $Path"
}

$item = Get-Item $Path
$files = @()

if ($item.PSIsContainer) {
    $files = Get-ChildItem -Path $item.FullName -File -Recurse:$Recurse
} else {
    $files = @($item)
}

if ($files.Count -eq 0) {
    throw "No files found at path: $Path"
}

Write-Host "Target Open WebUI: $WebUiUrl" -ForegroundColor Green
Write-Host "Files to process: $($files.Count)" -ForegroundColor Green

$kb = Get-OrCreateKnowledgeBase -BaseUrl $WebUiUrl -Token $ApiKey -Name $KnowledgeName -Description $KnowledgeDescription
$knowledgeId = $kb.id

$ok = 0
$failed = 0

foreach ($f in $files) {
    try {
        Write-Host "Uploading: $($f.FullName)" -ForegroundColor Yellow
        $fileId = Upload-FileAndAutoLink -BaseUrl $WebUiUrl -Token $ApiKey -FilePath $f.FullName -KnowledgeId $knowledgeId
        Wait-ForFileProcessing -BaseUrl $WebUiUrl -Token $ApiKey -FileId $fileId -TimeoutSeconds $ProcessTimeoutSeconds
        Write-Host "Processed: $($f.Name) (file_id=$fileId)" -ForegroundColor Green
        $ok += 1
    }
    catch {
        Write-Host "Failed: $($f.FullName) -> $($_.Exception.Message)" -ForegroundColor Red
        $failed += 1
    }
}

Write-Host "Done. Success=$ok Failed=$failed KnowledgeId=$knowledgeId" -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}
