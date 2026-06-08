$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$zip = "ffmpeg.zip"
$dest = "bin"

Write-Host "Downloading FFmpeg release essentials..."
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host "Extracting zip package..."
if (Test-Path "temp_ffmpeg") {
    Remove-Item -Recurse -Force "temp_ffmpeg"
}
Expand-Archive -Path $zip -DestinationPath "temp_ffmpeg"

Write-Host "Setting up bin directory..."
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Force -Path $dest
}

Write-Host "Copying binaries..."
Get-ChildItem -Path "temp_ffmpeg" -Filter "ffmpeg.exe" -Recurse | Copy-Item -Destination $dest -Force
Get-ChildItem -Path "temp_ffmpeg" -Filter "ffprobe.exe" -Recurse | Copy-Item -Destination $dest -Force

Write-Host "Cleaning up temporary files..."
if (Test-Path $zip) { Remove-Item -Force $zip }
if (Test-Path "temp_ffmpeg") { Remove-Item -Recurse -Force "temp_ffmpeg" }

Write-Host "FFmpeg successfully installed in bin/"
