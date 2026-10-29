# Zet een nieuwe Universe OS-update online in één keer (zie docs/UPDATES-VOORSTEL.md).
#   vm\publiceer-update.ps1                  bouwen + test + stable + publiceren (standaard)
#   vm\publiceer-update.ps1 -Kanaal test     alleen naar het testkanaal
# Stappen: bouw-VM starten als hij uit staat -> gecommitte code erheen -> pakket bouwen -> wachtwoordzin vragen
# (alleen in de VM, wordt daarna gewist) -> ondertekenen en publiceren -> online controleren.
# Vooraf: versienummer verhoogd in branding/universe.json en alles gecommit.
#   vm\publiceer-update.ps1 -Bestand <pad>   wachtwoordzin uit dat bestand; zonder -Bestand: wachtwoordzin.txt op de
#                                            sleutel-stick (map "sleutel universe os") als die erin zit, anders typen
param([ValidateSet('beide', 'test', 'stable')][string]$Kanaal = 'beide', [string]$Bestand)
$ErrorActionPreference = 'Stop'
# ssh -n (stdin from nothing) for the calls without input: in a terminal tab Windows OpenSSH otherwise waited for
# keyboard input after "true" and the script hung at the first step (12 Oct).
$vm = 'D:\UniverseOS-VMs'
$root = Split-Path $PSScriptRoot -Parent
$opts = @('-o', "UserKnownHostsFile=$vm\known_hosts", '-o', 'StrictHostKeyChecking=accept-new', '-i', "$vm\keys\id_ed25519", '-p', '2222')
$bron = 'https://itsamefork.github.io/universe-os-apt'

function Bereikbaar { & ssh -n @opts -o BatchMode=yes -o ConnectTimeout=5 bouwer@127.0.0.1 true 2>$null; return $LASTEXITCODE -eq 0 }

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
& ssh -n @opts -o BatchMode=yes bouwer@127.0.0.1 "sudo -n date -u -s '$nu' >/dev/null"
if ($LASTEXITCODE -ne 0) { Write-Host 'Let op: klok van de bouw-VM niet gelijkgezet.' -ForegroundColor Yellow }

Write-Host '== Code naar de bouw-VM'
& "$PSScriptRoot\sync-naar-vm.ps1"

Write-Host '== Pakket bouwen'
& ssh -n @opts -o BatchMode=yes bouwer@127.0.0.1 'cd ~/universe-os-claude && sh scripts/build-deb.sh >/tmp/build-deb.log 2>&1 || { tail -20 /tmp/build-deb.log; exit 1; }; tail -1 /tmp/build-deb.log'
if ($LASTEXITCODE -ne 0) { throw 'Pakket bouwen mislukt (zie hierboven).' }

$stappen = switch ($Kanaal) {
    'test'   { 'sh scripts/publiceer-apt.sh test --push' }
    'stable' { "sh scripts/publiceer-apt.sh stable $versie --push" }
    'beide'  { "sh scripts/publiceer-apt.sh test && sh scripts/publiceer-apt.sh stable $versie --push" }
}
Write-Host '== Ondertekenen en publiceren' -ForegroundColor Cyan
# Read locally: terminal paste markers never enter the remote passphrase.
# Preserve password characters; only remove the CR added by Windows pipeline framing.
# 29 Oct: typing it over from wachtwoordzin.txt kept giving 37 characters instead of 36 ("Bad passphrase"); the file
# itself signed fine, so it is read directly when the stick is in.
if (-not $Bestand) {
    $Bestand = Get-PSDrive -PSProvider FileSystem | ForEach-Object { Join-Path $_.Root 'sleutel universe os\wachtwoordzin.txt' } |
        Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if ($Bestand) {
    Write-Host "Wachtwoordzin uit $Bestand"
    # Only the line break at the end goes; gpg --passphrase-file reads the first line the same way.
    $geheim = ConvertTo-SecureString ((Get-Content -LiteralPath $Bestand -Raw -Encoding utf8).TrimEnd("`r", "`n")) -AsPlainText -Force
} else {
    $geheim = Read-Host 'Wachtwoordzin updatesleutel' -AsSecureString
}
$adres = [IntPtr]::Zero
$oudeEncoding = $OutputEncoding
$opdracht = 'set -eu; umask 077; PWFILE=$(mktemp); PROOF=$(mktemp -d); trap ''rm -f "$PWFILE"; rm -rf "$PROOF"'' EXIT; ' +
            'IFS= read -r P; P=$(printf %s "$P" | sed "s/\r$//"); printf %s "$P" > "$PWFILE"; unset P; ' +
            'export UNIVERSE_SLEUTEL_WACHTWOORDBESTAND="$PWFILE"; cd ~/universe-os-claude; ' +
            'FPR=$(cat scripts/apt/vingerafdruk); printf "Universe OS signing check\n" > "$PROOF/input"; ' +
            'gpg --batch --yes --pinentry-mode loopback --passphrase-file "$PWFILE" -u "$FPR" --detach-sign -o "$PROOF/input.sig" "$PROOF/input" || { echo "Ondertekening geweigerd. Updatebron niet aangepast." >&2; exit 1; }; ' +
            'gpg --batch --verify "$PROOF/input.sig" "$PROOF/input"; ' +
            '{ ' + $stappen + '; }'
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $adres = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($geheim)
    [Runtime.InteropServices.Marshal]::PtrToStringBSTR($adres) | & ssh @opts -o BatchMode=yes -T bouwer@127.0.0.1 $opdracht
    if ($LASTEXITCODE -ne 0) { throw 'Publiceren mislukt. Zie de specifieke fout hierboven; er is niets automatisch teruggedraaid.' }
} finally {
    $OutputEncoding = $oudeEncoding
    if ($adres -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adres) }
    $geheim.Dispose()
}

Write-Host '== Online controleren (GitHub Pages kan een paar minuten nodig hebben)'
$kanalen = if ($Kanaal -eq 'beide') { 'test', 'stable' } else { , $Kanaal }
$tot = (Get-Date).AddMinutes(10)
foreach ($k in $kanalen) {
    while ($true) {
        # As text: GitHub Pages serves Packages without a text type, so .Content was bytes and never matched (12 Oct).
        $antwoord = Invoke-WebRequest "$bron/dists/$k/main/binary-amd64/Packages?t=$(Get-Random)" -UseBasicParsing
        $lijst = [Text.Encoding]::UTF8.GetString($antwoord.RawContentStream.ToArray())
        if ($lijst -match "(?m)^Version: $([regex]::Escape($versie))$") { Write-Host "  $k`: $versie staat online" -ForegroundColor Green; break }
        if ((Get-Date) -gt $tot) { Write-Host "  $k`: $versie nog niet zichtbaar; probeer later $bron" -ForegroundColor Yellow; break }
        Start-Sleep 20
    }
}
Write-Host 'Klaar. Universe-computers zien de update bij de volgende controle (Controlecentrum > Updates > Nu controleren).'
