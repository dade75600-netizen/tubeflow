Write-Host "========================================="
Write-Host "AVVIANDO LA PIPELINE AVIATION"
Write-Host "========================================="
$env:YOUTUBE_TOKEN_JSON = Get-Content token_aviation.json -Raw
.\.venv\Scripts\python.exe pipeline.py --channel aviation --force-publish

Write-Host "========================================="
Write-Host "AVVIANDO LA PIPELINE MILITARY"
Write-Host "========================================="
$env:YOUTUBE_TOKEN_JSON = Get-Content nuovo_token_youtube.json -Raw
.\.venv\Scripts\python.exe pipeline.py --channel military --force-publish

Write-Host "========================================="
Write-Host "TUTTE LE PUBBLICAZIONI COMPLETATE"
Write-Host "========================================="
