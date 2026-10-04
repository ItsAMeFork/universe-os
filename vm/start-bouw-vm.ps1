# Start de Universe OS bouwomgeving (Debian 13 in QEMU). Opent een venster met de console.
# SSH vanaf Windows:  ssh -p 2222 -i D:\UniverseOS-VMs\keys\id_ed25519 bouwer@127.0.0.1
param([int]$GeheugenMB = 6144, [int]$Cpus = 4, [switch]$ZonderVenster)
$ErrorActionPreference = 'Stop'
$qemu = 'C:\Program Files\qemu'
$vm = 'D:\UniverseOS-VMs'
$disk = Join-Path $vm 'bouw-vm.qcow2'
if (-not (Test-Path $disk)) {
    Write-Host 'Eerste start: virtuele schijf aanmaken uit het Debian 13 image...'
    & "$qemu\qemu-img.exe" convert -O qcow2 (Join-Path $vm 'images\debian-13-generic-amd64.qcow2') $disk
    & "$qemu\qemu-img.exe" resize $disk 80G
}
# cloud-init leest bij ELKE start de instellingen via een kleine webserver op de host. Zonder die server blijft het
# opstarten minutenlang hangen voordat het inlogscherm verschijnt. Daarom draait hij altijd mee.
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'seed-server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
$seed = Start-Process node -ArgumentList "`"$PSScriptRoot\seed-server.mjs`" `"$vm\seed`" 8123" -PassThru -WindowStyle Hidden
$display = if ($ZonderVenster) { 'none' } else { 'sdl' }
$qargs = @(
    '-name', '"Universe OS bouwomgeving"',
    '-accel', 'whpx', '-machine', 'q35', '-smp', "$Cpus", '-m', "$GeheugenMB",
    '-drive', "file=$disk,if=virtio,discard=unmap",
    '-nic', 'user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22',
    '-smbios', 'type=1,serial=ds=nocloud;s=http://10.0.2.2:8123/',
    '-display', $display, '-vga', 'virtio',
    '-serial', "file:$vm\bouw-vm-serial.log",
    # Beheerkanaal (alleen lokaal): de VM besturen als SSH niet werkt (toetsen sturen, schermafbeelding).
    '-qmp', 'tcp:127.0.0.1:4444,server,nowait'
)
$p = Start-Process "$qemu\qemu-system-x86_64.exe" -ArgumentList $qargs -PassThru
Write-Host "Bouwomgeving gestart (proces $($p.Id))."
Write-Host 'De instellingenserver voor cloud-init draait mee zolang de VM aan staat.'
# Stop de seed-server automatisch zodra de VM wordt afgesloten (los van dit venster).
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command `"Wait-Process -Id $($p.Id); Stop-Process -Id $($seed.Id) -ErrorAction SilentlyContinue`""
