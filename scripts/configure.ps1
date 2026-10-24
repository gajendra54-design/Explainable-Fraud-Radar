param([string]$Username = 'admin')
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$configurationPath = Join-Path $projectPath '.env'
if (Test-Path -LiteralPath $configurationPath) { throw '.env already exists; preserve or edit your existing configuration.' }
function New-LocalSecret {
  $bytes = New-Object byte[] 32
  $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
  return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
if ($Username -notmatch '^[a-zA-Z0-9_-]{3,40}$') { throw 'Username must be 3-40 letters, digits, underscores or hyphens.' }
$databaseSecret = New-LocalSecret
$tokenSecret = New-LocalSecret
$loginSecret = New-LocalSecret
$configuration = @"
POSTGRES_PASSWORD=$databaseSecret
JWT_SECRET=$tokenSecret
BOOTSTRAP_USERNAME=$Username
BOOTSTRAP_PASSWORD=$loginSecret
DATABASE_URL=sqlite:///./fraud_radar.db
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5177,http://localhost:8087
UI_PORT=8087
ARTIFACT_DIR=artifacts
"@
[System.IO.File]::WriteAllText($configurationPath, $configuration)
Write-Output 'Created ignored .env with unique local credentials. Read BOOTSTRAP_USERNAME and BOOTSTRAP_PASSWORD from that file to log in. Do not share or commit it.'
