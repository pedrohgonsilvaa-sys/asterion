param(
    [string]$Root = "assets",
    [int]$Quality = 88,
    [int]$MinBytes = 300000
)

<#
Create JPEG companions for large opaque PNG assets without touching originals.
The catalog prefers .jpg, while the original .png remains available for rollback.
#>

Add-Type -AssemblyName System.Drawing

$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
    Where-Object MimeType -eq "image/jpeg"
$encoderParameters = New-Object System.Drawing.Imaging.EncoderParameters(1)
$encoderParameters.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter(
    [System.Drawing.Imaging.Encoder]::Quality,
    [long]$Quality
)

$converted = 0
$skipped = 0
$savedBytes = [long]0

Get-ChildItem -LiteralPath $Root -Recurse -File -Filter *.png | ForEach-Object {
    if ($_.Length -lt $MinBytes) {
        $skipped++
        return
    }

    $image = $null
    $output = [IO.Path]::ChangeExtension($_.FullName, ".jpg")
    if (Test-Path -LiteralPath $output) {
        $skipped++
        return
    }
    try {
        $image = [System.Drawing.Image]::FromFile($_.FullName)
        $format = $image.PixelFormat.ToString()
        if ($format -match "Argb|PArgb|Alpha") {
            $skipped++
            return
        }
        $image.Save($output, $codec, $encoderParameters)
        $newSize = (Get-Item -LiteralPath $output).Length
        if ($newSize -ge $_.Length) {
            Remove-Item -LiteralPath $output -Force
            $skipped++
            return
        }
        $converted++
        $savedBytes += $_.Length - $newSize
        if ($converted % 100 -eq 0) {
            Write-Output "converted=$converted saved_bytes=$savedBytes"
        }
    }
    finally {
        if ($null -ne $image) {
            $image.Dispose()
        }
    }
}

Write-Output "finished converted=$converted skipped=$skipped saved_bytes=$savedBytes"
