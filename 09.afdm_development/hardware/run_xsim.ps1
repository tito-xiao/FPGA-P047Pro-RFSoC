param(
    [string]$VivadoBin = 'D:\XIAO\Software\Xilinx\Vivado\2023.1\bin',
    [string]$WorkDirectory = ''
)
$ErrorActionPreference = 'Stop'
$taskRepository = Split-Path -Parent $PSScriptRoot
if (!$WorkDirectory) { $WorkDirectory = Join-Path $taskRepository 'artifacts\rtl_sim' }
if (!(Test-Path -LiteralPath (Join-Path $WorkDirectory 'tx_coeff.mem'))) {
    throw 'Generate vector files first: python -m afdm_lab.cli fixedpoint --output artifacts/rtl_sim'
}
$taskSources = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'rtl') -Filter '*.sv' | Select-Object -ExpandProperty FullName
$taskTestbench = Join-Path $PSScriptRoot 'tb\tb_all.sv'
Push-Location -LiteralPath $WorkDirectory
try {
    & (Join-Path $VivadoBin 'xvlog.bat') -sv @taskSources $taskTestbench
    if ($LASTEXITCODE -ne 0) { throw 'RTL compilation failed' }
    & (Join-Path $VivadoBin 'xelab.bat') tb_all -s afdm_tb
    if ($LASTEXITCODE -ne 0) { throw 'RTL elaboration failed' }
    & (Join-Path $VivadoBin 'xsim.bat') afdm_tb -runall -log simulation.log
    if ($LASTEXITCODE -ne 0) { throw 'RTL simulation failed' }
    if (!(Select-String -LiteralPath 'simulation.log' -Pattern 'RTL PASS:' -Quiet)) { throw 'Missing RTL pass marker' }
} finally { Pop-Location }
