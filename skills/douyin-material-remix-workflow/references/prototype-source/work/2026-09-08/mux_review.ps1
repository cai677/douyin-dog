param([string]$Video,[string]$Audio,[string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Storage.StorageFolder,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Media.Editing.MediaComposition,Windows.Media.Editing,ContentType=WindowsRuntime]
$null=[Windows.Media.MediaProperties.MediaEncodingProfile,Windows.Media,ContentType=WindowsRuntime]
function Await($op,[Type]$resultType) {
 $m=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1} | Select-Object -First 1
 $task=$m.MakeGenericMethod($resultType).Invoke($null,@($op)); $task.Wait(); return $task.Result
}
$vf=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Video)) ([Windows.Storage.StorageFile])
$af=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Audio)) ([Windows.Storage.StorageFile])
$clip=Await ([Windows.Media.Editing.MediaClip]::CreateFromFileAsync($vf)) ([Windows.Media.Editing.MediaClip])
$track=Await ([Windows.Media.Editing.BackgroundAudioTrack]::CreateFromFileAsync($af)) ([Windows.Media.Editing.BackgroundAudioTrack])
$comp=New-Object Windows.Media.Editing.MediaComposition
$clip.Volume=0; [System.Collections.Generic.ICollection[Windows.Media.Editing.MediaClip]].GetMethod("Add").Invoke($comp.Clips,@($clip)); [System.Collections.Generic.ICollection[Windows.Media.Editing.BackgroundAudioTrack]].GetMethod("Add").Invoke($comp.BackgroundAudioTracks,@($track))
$folder=Await ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync([IO.Path]::GetDirectoryName($Output))) ([Windows.Storage.StorageFolder])
$out=Await ($folder.CreateFileAsync([IO.Path]::GetFileName($Output),[Windows.Storage.CreationCollisionOption]::FailIfExists)) ([Windows.Storage.StorageFile])
$profile=[Windows.Media.MediaProperties.MediaEncodingProfile]::CreateMp4([Windows.Media.MediaProperties.VideoEncodingQuality]::HD1080p)
$profile.Video.Width=1080; $profile.Video.Height=1920; $profile.Video.FrameRate.Numerator=60; $profile.Video.FrameRate.Denominator=1; $profile.Video.Bitrate=10000000
$profile.Audio.SampleRate=44100; $profile.Audio.Bitrate=192000
$op=$comp.RenderToFileAsync($out,[Windows.Media.Editing.MediaTrimmingPreference]::Precise,$profile)
$m=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 2 -and $_.GetParameters().Count -eq 1} | Select-Object -First 1
$task=$m.MakeGenericMethod([Windows.Media.Transcoding.TranscodeFailureReason],[double]).Invoke($null,@($op))
$task.Wait(); if($task.Result -ne 'None'){throw "Render failed: $($task.Result)"}
Write-Output "MUX_OK $($comp.Duration.TotalSeconds) seconds"

