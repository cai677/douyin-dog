$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$pythonPath = Join-Path $projectRoot '.venv-voxcpm\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Python environment not found.' }
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.Form
$dialog.Text = 'Doubao API Key'
$dialog.Width = 530
$dialog.Height = 180
$dialog.StartPosition = 'CenterScreen'
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Paste your API key below (Ctrl+V), then click OK.'
$label.SetBounds(15,15,485,25)
$inputBox = New-Object System.Windows.Forms.TextBox
$inputBox.SetBounds(15,45,485,25)
$inputBox.UseSystemPasswordChar = $true
$button = New-Object System.Windows.Forms.Button
$button.Text = 'OK'
$button.SetBounds(400,85,100,30)
$button.DialogResult = [System.Windows.Forms.DialogResult]::OK
$dialog.Controls.AddRange(@($label,$inputBox,$button))
$dialog.AcceptButton = $button
$dialog.Add_Shown({$inputBox.Focus()})
if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { $dialog.Dispose(); return }
$previousKey = [Environment]::GetEnvironmentVariable('DOUBAO_TTS_API_KEY','Process')
$previousRate = [Environment]::GetEnvironmentVariable('DOUBAO_TTS_SPEECH_RATE','Process')
$previousSpeaker = [Environment]::GetEnvironmentVariable('DOUBAO_TTS_SPEAKER','Process')
try {
 [Environment]::SetEnvironmentVariable('DOUBAO_TTS_SPEAKER','zh_male_xionger_mars_bigtts','Process')
 [Environment]::SetEnvironmentVariable('DOUBAO_TTS_SPEECH_RATE','50','Process')
 Write-Host 'Generating Xionger voice with speech_rate=50. Previous voices are preserved.'
 [Environment]::SetEnvironmentVariable('DOUBAO_TTS_API_KEY',$inputBox.Text.Trim(),'Process')
 $inputBox.Clear()
 $dialog.Dispose()
 & $pythonPath (Join-Path $PSScriptRoot 'generate_doubao.py')
 if ($LASTEXITCODE -ne 0) { Write-Host 'Generation failed. Diagnostic details are saved in last-error.json.' -ForegroundColor Yellow }
} finally {
 [Environment]::SetEnvironmentVariable('DOUBAO_TTS_SPEAKER',$previousSpeaker,'Process')
 [Environment]::SetEnvironmentVariable('DOUBAO_TTS_API_KEY',$previousKey,'Process')
 [Environment]::SetEnvironmentVariable('DOUBAO_TTS_SPEECH_RATE',$previousRate,'Process')
}

