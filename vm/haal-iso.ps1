# Haalt het nieuwste ISO uit de bouw-VM naar D:\UniverseOS-VMs\iso\ en controleert de SHA-256.
#   vm\haal-iso.ps1                         (uit ~/universe-os/uitvoer)
#   vm\haal-iso.ps1 -Map universe-os-claude (andere bouwkopie in de bouw-VM)
param([string]$Map = 'universe-os')
$ErrorActionPreference = 'Stop'
$vm = 'D:\UniverseOS-VMs'
$doel = Join-Path $vm 'iso'
$opts = @('-o', 'BatchMode=yes', '-o', "UserKnownHostsFile=$vm\known_hosts", '-o', 'StrictHostKeyChecking=accept-new',
          '-i', "$vm\keys\id_ed25519")
New-Item -ItemType Directory -Force $doel | Out-Null

$naam = "$(& ssh @opts -p 2222 bouwer@127.0.0.1 "ls -1t ~/$Map/uitvoer/*.iso | head -1 | xargs -r basename")".Trim()
if (-not $naam) { throw "Geen ISO gevonden in ~/$Map/uitvoer in de bouw-VM." }
Write-Host "ISO ophalen: $naam"
& scp @opts -P 2222 "bouwer@127.0.0.1:$Map/uitvoer/$naam" "bouwer@127.0.0.1:$Map/uitvoer/$naam.sha256" "$doel\"
if ($LASTEXITCODE -ne 0) { throw 'Kopiëren mislukt.' }

$verwacht = ((Get-Content "$doel\$naam.sha256" -Raw) -split '\s+')[0].ToLower()
$echt = (Get-FileHash "$doel\$naam" -Algorithm SHA256).Hash.ToLower()
if ($echt -ne $verwacht) { throw "SHA-256 klopt NIET: verwacht $verwacht, gekregen $echt" }
Write-Host "SHA-256 klopt: $echt"
Write-Host "Opgeslagen: $doel\$naam"
