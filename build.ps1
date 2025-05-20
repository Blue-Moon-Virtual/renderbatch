# Build script for RenderBatch
Write-Host "Starting RenderBatch build process..." -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/"
    exit 1
}

# Check if required packages are installed
Write-Host "Checking required packages..." -ForegroundColor Cyan
$requiredPackages = @("pyinstaller", "tkinterdnd2")

foreach ($package in $requiredPackages) {
    try {
        python -c "import $package" 2>$null
        Write-Host "$package is installed" -ForegroundColor Green
    } catch {
        Write-Host "$package is not installed. Installing..." -ForegroundColor Yellow
        pip install $package
    }
}

# Clean previous build
Write-Host "Cleaning previous build..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
}
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
}

# Build the executable
Write-Host "Building executable..." -ForegroundColor Cyan
pyinstaller RenderBatch.spec

# Check if build was successful
if (Test-Path "dist/RenderBatch.exe") {
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Executable location: $((Get-Item "dist/RenderBatch.exe").FullName)" -ForegroundColor Green
    
    # Get file size
    $fileSize = (Get-Item "dist/RenderBatch.exe").Length / 1MB
    Write-Host "Executable size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Build process completed!" -ForegroundColor Cyan 