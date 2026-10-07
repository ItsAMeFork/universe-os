# Zet een nieuwe Universe OS-update online in één keer (zie docs/UPDATES-VOORSTEL.md).
#   vm\publiceer-update.ps1                  bouwen + test + stable + publiceren (standaard)
#   vm\publiceer-update.ps1 -Kanaal test     alleen naar het testkanaal
# Stappen: bouw-VM starten als hij uit staat -> gecommitte code erheen -> pakket bouwen -> wachtwoordzin vragen
# (alleen in de VM, wordt daarna gewist) -> ondertekenen en publiceren -> online controleren.
# Vooraf: versienummer verhoogd in branding/universe.json en alles gecommit.
param([ValidateSet('beide', 'test', 'stable')][string]$Kanaal = 'beide')
$ErrorActionPreference = 'Stop'
$vm = 'D:\UniverseOS-VMs'
$root = Split-Path $PSScriptRoot -Parent
$opts = @('-o', "UserKnownHostsFile=$vm\known_hosts", '-o', 'StrictHostKeyChecking=accept-new', '-i', "$vm\keys\id_ed25519", '-p', '2222')
$bron = 'https://itsamefork.github.io/universe-os-apt'

function Bereikbaar { & ssh @opts -o BatchMode=yes -o ConnectTimeout=5 bouwer@127.0.0.1 true 2>$null; return $LASTEXITCODE -eq 0 }

$versie = (Get-Content "$root\branding\universe.json" -Raw | ConvertFrom-Json).version
Write-Host "== Universe OS $versie publiceren (kanaal: $Kanaal)" -ForegroundColor Cyan
if (git -C $root status --porcelain) {
    Write-Host 'Let op: er zijn niet-gecommitte wijzigingen; die gaan NIET mee (alleen de laatste commit).' -ForegroundColor Yellow
}

if (-not (Bereikbaar)) {
    Write-Host '== Bouw-VM starten...'
    & "$PSScriptRoot\start-bouw-vm.ps1" -ZonderVenster | Out-Null
    $tot = (Get-Date).AddMinutes(10)
    while (-not (Bereikbaar)) {
        if ((Get-Date) -gt $tot) { throw 'De bouw-VM is na 10 minuten nog niet bereikbaar.' }
        Start-Sleep 10
    }
}

# Na een slaapstand van de laptop loopt de VM-klok achter; gpg weigert dan een sleutel "uit de toekomst".
$nu = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')
& ssh @opts -o BatchMode=yes bouwer@127.0.0.1 "sudo -n date -u -s '$nu' >/dev/null"
if ($LASTEXITCODE -ne 0) { Write-Host 'Let op: klok van de bouw-VM niet gelijkgezet.' -ForegroundColor Yellow }

Write-Host '== Code naar de bouw-VM'
& "$PSScriptRoot\sync-naar-vm.ps1"

Write-Host '== Pakket bouwen'
& ssh @opts -o BatchMode=yes bouwer@127.0.0.1 'cd ~/universe-os-claude && sh scripts/build-deb.sh >/tmp/build-deb.log 2>&1 || { tail -20 /tmp/build-deb.log; exit 1; }; tail -1 /tmp/build-deb.log'
if ($LASTEXITCODE -ne 0) { throw 'Pakket bouwen mislukt (zie hierboven).' }

$stappen = switch ($Kanaal) {
    'test'   { 'sh scripts/publiceer-apt.sh test --push' }
    'stable' { "sh scripts/publiceer-apt.sh stable $versie --push" }
    'beide'  { "sh scripts/publiceer-apt.sh test && sh scripts/publiceer-apt.sh stable $versie --push" }
}
Write-Host '== Ondertekenen en publiceren. Typ de wachtwoordzin van de updatesleutel (je ziet niet wat je typt).' -ForegroundColor Cyan
$opdracht = 'umask 077; trap "rm -f /tmp/ww" EXIT; read -rs -p "Wachtwoordzin updatesleutel: " P; echo; printf %s "$P" > /tmp/ww; unset P; ' +
            'export UNIVERSE_SLEUTEL_WACHTWOORDBESTAND=/tmp/ww; cd ~/universe-os-claude && ' + $stappen
& ssh @opts -t bouwer@127.0.0.1 $opdracht
if ($LASTEXITCODE -ne 0) { throw 'Publiceren mislukt (verkeerde wachtwoordzin of versie al gepubliceerd? Zie hierboven).' }

Write-Host '== Online controleren (GitHub Pages kan een paar minuten nodig hebben)'
$kanalen = if ($Kanaal -eq 'beide') { 'test', 'stable' } else { , $Kanaal }
$tot = (Get-Date).AddMinutes(10)
foreach ($k in $kanalen) {
    while ($true) {
        $lijst = (Invoke-WebRequest "$bron/dists/$k/main/binary-amd64/Packages?t=$(Get-Random)" -UseBasicParsing).Content
        if ($lijst -match "(?m)^Version: $([regex]::Escape($versie))$") { Write-Host "  $k`: $versie staat online" -ForegroundColor Green; break }
        if ((Get-Date) -gt $tot) { Write-Host "  $k`: $versie nog niet zichtbaar; probeer later $bron" -ForegroundColor Yellow; break }
        Start-Sleep 20
    }
}
Write-Host 'Klaar. Universe-computers zien de update bij de volgende controle (Controlecentrum > Updates > Nu controleren).'
