# Zet de gecommitte stand van het project in de bouw-VM (git archive, dus geen lokale rommel of geheimen).
#   vm\sync-naar-vm.ps1                       -> ~/universe-os-claude in de bouw-VM
#   vm\sync-naar-vm.ps1 -Map andere-map -Commit spoor-a/A12
# Bouwen daarna in de VM:  cd ~/universe-os-claude && sh scripts/build-iso.sh
param([string]$Map = 'universe-os-claude', [string]$Commit = 'HEAD')
$ErrorActionPreference = 'Stop'
$vm = 'D:\UniverseOS-VMs'
$root = Split-Path $PSScriptRoot -Parent
$sha = (git -C $root rev-parse --short $Commit).Trim()
$tar = Join-Path $env:TEMP "universe-os-$sha.tar"
git -C $root archive --format=tar -o $tar $Commit
if ($LASTEXITCODE -ne 0) { throw 'git archive mislukt.' }

$opts = @('-o', 'BatchMode=yes', '-o', "UserKnownHostsFile=$vm\known_hosts", '-o', 'StrictHostKeyChecking=accept-new',
          '-i', "$vm\keys\id_ed25519")
& scp @opts -P 2222 $tar "bouwer@127.0.0.1:/tmp/universe-os.tar"
if ($LASTEXITCODE -ne 0) { throw 'Kopiëren naar de bouw-VM mislukt.' }
# uitvoer/ en de live-build-cache blijven staan; alle bestanden uit git worden vervangen.
& ssh @opts -p 2222 bouwer@127.0.0.1 "mkdir -p ~/$Map && tar -xf /tmp/universe-os.tar -C ~/$Map && rm /tmp/universe-os.tar && echo $sha > ~/$Map/.commit"
if ($LASTEXITCODE -ne 0) { throw 'Uitpakken in de bouw-VM mislukt.' }
Remove-Item $tar
Write-Host "Commit $sha staat in ~/$Map in de bouw-VM."
