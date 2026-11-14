param([Parameter(Mandatory=$true)][string]$Text, [Parameter(Mandatory=$true)][string]$Out)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToWaveFile($Out, (New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)))
$s.Rate = 0
$s.Speak($Text)
$s.Dispose()
Write-Output ("OK " + (Get-Item $Out).Length)
