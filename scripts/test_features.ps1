# ============================================================================
# Sovereign-Mind Feature Test Script
# Tests: Vault (Encrypted Storage), RAG, and Privacy Guard
# ============================================================================

$baseUrl = "http://localhost:8000"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SOVEREIGN-MIND FEATURE TEST SUITE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ============================================================================
# 1. HEALTH CHECK
# ============================================================================
Write-Host "[1/7] Health Check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/v1/system/health" -Method Get
    Write-Host "  Status: $($health.status)" -ForegroundColor Green
    Write-Host "  Version: $($health.version)"
    Write-Host "  Vault Unlocked: $($health.vault_unlocked)"
    Write-Host "  RAG Docs: $($health.rag_document_count)"
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# 2. VAULT - UNLOCK
# ============================================================================
Write-Host "`n[2/7] Unlocking Vault..." -ForegroundColor Yellow
$passphrase = "test-passphrase-123"
try {
    $unlock = Invoke-RestMethod -Uri "$baseUrl/v1/vault/unlock" -Method Post `
        -Body "passphrase=$passphrase" -ContentType "application/x-www-form-urlencoded"
    Write-Host "  $($unlock.message)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
}

# ============================================================================
# 3. VAULT - CREATE SESSION
# ============================================================================
Write-Host "`n[3/7] Creating Encrypted Session..." -ForegroundColor Yellow
try {
    $session = Invoke-RestMethod -Uri "$baseUrl/v1/vault/sessions" -Method Post
    $sessionId = $session.session_id
    Write-Host "  Session ID: $sessionId" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
    $sessionId = $null
}

# ============================================================================
# 4. VAULT - CHAT WITH ENCRYPTION
# ============================================================================
Write-Host "`n[4/7] Testing Encrypted Chat..." -ForegroundColor Yellow
if ($sessionId) {
    try {
        $body = @{
            messages = @(@{ role = "user"; content = "Remember: my secret code is ALPHA-7749" })
            config = @{ mode = "local"; depth = "fast" }
            session_id = $sessionId
        } | ConvertTo-Json -Depth 3
        
        $chat = Invoke-RestMethod -Uri "$baseUrl/v1/chat/completions" -Method Post `
            -Body $body -ContentType "application/json"
        
        Write-Host "  Intent: $($chat.intent)" -ForegroundColor Green
        Write-Host "  Response: $($chat.choices[0].message.content.Substring(0, [Math]::Min(80, $chat.choices[0].message.content.Length)))..."
        
        # Retrieve messages
        Write-Host "`n  Retrieving encrypted session messages..."
        $messages = Invoke-RestMethod -Uri "$baseUrl/v1/vault/sessions/$sessionId/messages" -Method Get
        Write-Host "  Messages stored: $($messages.messages.Count)" -ForegroundColor Green
    } catch {
        Write-Host "  FAILED: $_" -ForegroundColor Red
    }
}

# ============================================================================
# 5. RAG - DOCUMENT INGESTION
# ============================================================================
Write-Host "`n[5/7] Testing RAG Ingestion..." -ForegroundColor Yellow
try {
    $formData = @{
        content = "Sovereign-Mind uses Argon2id for key derivation, AES-256-GCM for envelope encryption, and SHA-256 for audit logging. The system supports hybrid RAG with ChromaDB dense search, BM25 sparse search, and FlashRank reranking."
        metadata = '{"source": "test-script", "type": "documentation"}'
    }
    
    $ingest = Invoke-RestMethod -Uri "$baseUrl/v1/system/ingest" -Method Post -Form $formData
    Write-Host "  Document ID: $($ingest.document_id)" -ForegroundColor Green
    Write-Host "  Chunks: $($ingest.chunk_count)"
    
    # Check stats
    $stats = Invoke-RestMethod -Uri "$baseUrl/v1/system/collection" -Method Get
    Write-Host "  Total docs in collection: $($stats.document_count)"
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
}

# ============================================================================
# 6. RAG - QUERY
# ============================================================================
Write-Host "`n[6/7] Testing RAG Query..." -ForegroundColor Yellow
try {
    $body = @{
        messages = @(@{ role = "user"; content = "What encryption algorithms does Sovereign-Mind use?" })
        config = @{ mode = "local"; depth = "fast" }
    } | ConvertTo-Json -Depth 3
    
    $ragQuery = Invoke-RestMethod -Uri "$baseUrl/v1/chat/completions" -Method Post `
        -Body $body -ContentType "application/json"
    
    Write-Host "  Intent: $($ragQuery.intent)" -ForegroundColor Green
    $response = $ragQuery.choices[0].message.content
    Write-Host "  Response: $($response.Substring(0, [Math]::Min(150, $response.Length)))..."
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
}

# ============================================================================
# 7. VAULT - LOCK
# ============================================================================
Write-Host "`n[7/7] Locking Vault..." -ForegroundColor Yellow
try {
    $lock = Invoke-RestMethod -Uri "$baseUrl/v1/vault/lock" -Method Post
    Write-Host "  $($lock.message)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
}

# ============================================================================
# CHECK ENCRYPTED FILES
# ============================================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  CHECKING ENCRYPTED DATA FILES" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$dataPath = "d:\New folder (2)\sovereign-mind\data"

Write-Host "Vault (encrypted sessions):" -ForegroundColor Yellow
if (Test-Path "$dataPath\vault") {
    Get-ChildItem "$dataPath\vault" -Recurse | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  (directory not found - may be in Docker volume)"
}

Write-Host "`nAudit logs (hashed entries):" -ForegroundColor Yellow
if (Test-Path "$dataPath\audit") {
    Get-ChildItem "$dataPath\audit" | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  (directory not found - may be in Docker volume)"
}

Write-Host "`nChromaDB (vector store):" -ForegroundColor Yellow
if (Test-Path "$dataPath\chroma") {
    Get-ChildItem "$dataPath\chroma" | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  (directory not found - may be in Docker volume)"
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  TEST SUITE COMPLETE" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
