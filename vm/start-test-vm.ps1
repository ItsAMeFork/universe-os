# Start de aparte test-VM voor Universe OS: UEFI (OVMF uit QEMU), eigen schijf van 40 GB. Los van de bouw-VM.
#   vm\start-test-vm.ps1 -Iso D:\UniverseOS-VMs\iso\universe-os-0.1.0-amd64.iso -Nieuw   (lege schijf + live-ISO)
#   vm\start-test-vm.ps1                                                                (opstarten zonder ISO)
# Beheerkanaal QMP op 127.0.0.1:4445:  node vm\qmp.mjs 4445 status|scherm|typ|toets
param([string]$Iso, [switch]$Nieuw, [int]$GeheugenMB = 4096, [int]$Cpus = 2, [switch]$SecureBoot, [switch]$ZonderVenster,
      [ValidateSet('gtk', 'sdl')][string]$Venster = 'gtk', [string]$Resolutie = '1920x1080', [switch]$VolledigScherm)
$ErrorActionPreference = 'Stop'
$qemu = 'C:\Program Files\qemu'
$vm = 'D:\UniverseOS-VMs'
$disk = Join-Path $vm 'test-vm.qcow2'
$vars = Join-Path $vm 'test-vm-efivars.fd'

if ($Nieuw) {
    foreach ($f in $disk, $vars) { if (Test-Path $f) { Remove-Item $f } }
}
if (-not (Test-Path $disk)) {
    & "$qemu\qemu-img.exe" create -f qcow2 $disk 40G | Out-Null
    Write-Host 'Nieuwe lege schijf van 40 GB aangemaakt.'
}
# De UEFI-instellingen (opstartvolgorde, Secure Boot-sleutels) horen bij deze VM; QEMU levert alleen een leeg sjabloon.
if (-not (Test-Path $vars)) { Copy-Item "$qemu\share\edk2-i386-vars.fd" $vars }
$code = if ($SecureBoot) { "$qemu\share\edk2-x86_64-secure-code.fd" } else { "$qemu\share\edk2-x86_64-code.fd" }
$machine = if ($SecureBoot) { 'q35,smm=on' } else { 'q35' }

# GTK by default: the SDL window stopped responding twice (and blocked QMP with it).
$display = if ($ZonderVenster) { 'none' } elseif ($Venster -eq 'gtk') { 'gtk,zoom-to-fit=on' } else { $Venster }
$qargs = @(
    '-name', '"Universe OS test"',
    '-accel', 'whpx', '-machine', $machine, '-smp', "$Cpus", '-m', "$GeheugenMB",
    # Quoted: Start-Process joins arguments with spaces, and the firmware lives under "C:\Program Files".
    '-drive', "`"if=pflash,format=raw,unit=0,readonly=on,file=$code`"",
    '-drive', "if=pflash,format=raw,unit=1,file=$vars",
    '-drive', "file=$disk,if=none,id=schijf,discard=unmap", '-device', 'virtio-blk-pci,drive=schijf,bootindex=1',
    # SSH alleen vanaf deze pc (127.0.0.1:2223). In de test-VM staat ontwikkeltoegang voor `tester` (sleutel uit keys\).
    '-nic', 'user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2223-:22',
    # Fixed screen size (default: the Windows screen, 1920x1080) for greeter and session alike. Standard VGA with EDID does
    # not follow the window size (virtio-gpu did: the session fell back to 640x480); GTK scales the picture to the window.
    '-display', $display, '-vga', 'none', '-device', "VGA,edid=on,vgamem_mb=64,xres=$(($Resolutie -split 'x')[0]),yres=$(($Resolutie -split 'x')[1])",
    # usb-tablet: absolute muispositie, nodig om via QMP precies te klikken.
    '-device', 'qemu-xhci', '-device', 'usb-tablet',
    '-audiodev', 'none,id=geluid', '-device', 'ich9-intel-hda', '-device', 'hda-duplex,audiodev=geluid',
    '-serial', "file:$vm\test-vm-serial.log",
    '-qmp', 'tcp:127.0.0.1:4445,server,nowait'
)
if ($VolledigScherm -and -not $ZonderVenster) { $qargs += @('-full-screen') }
if ($SecureBoot) { $qargs += @('-global', 'driver=cfi.pflash01,property=secure,value=on') }
if ($Iso) {
    if (-not (Test-Path $Iso)) { throw "ISO niet gevonden: $Iso" }
    $qargs += @('-drive', "file=$Iso,if=none,id=cd,media=cdrom,readonly=on", '-device', 'ide-cd,drive=cd,bootindex=0')
}
$p = Start-Process "$qemu\qemu-system-x86_64.exe" -ArgumentList $qargs -PassThru
$met = if ($Iso) { "met ISO $(Split-Path $Iso -Leaf)" } else { 'zonder ISO' }
Write-Host "Test-VM gestart $met (proces $($p.Id)). QMP: 127.0.0.1:4445."
