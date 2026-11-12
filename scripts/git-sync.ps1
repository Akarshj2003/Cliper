<#
.SYNOPSIS
Professional Git Automation Script for ClipViral
#>

param(
    [Parameter(Position=0)]
    [string]$Message = "",

    [Parameter(Position=1)]
    [ValidateSet("commit", "push", "status", "test", "release")]
    [string]$Action = "push"
)

$git = "C:\Users\akars\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"

function Run-Tests {
    Write-Host "[1/3] Running Backend Tests..." -ForegroundColor Cyan
    cd C:\Stu\Cliper\backend
    python -m pytest tests -v
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Tests failed! Aborting Git operation."
        exit 1
    }
    cd C:\Stu\Cliper
    Write-Host "Tests passed successfully!" -ForegroundColor Green
}

switch ($Action) {
    "status" {
        & $git status
    }
    "test" {
        Run-Tests
    }
    "commit" {
        if (-not $Message) {
            Write-Error "Please provide a commit message. Example: .\scripts\git-sync.ps1 'feat: add upload endpoint' commit"
            exit 1
        }
        Run-Tests
        & $git add .
        & $git commit -m $Message
    }
    "push" {
        if ($Message) {
            Run-Tests
            Write-Host "[2/3] Staging and Committing..." -ForegroundColor Cyan
            & $git add .
            & $git commit -m $Message
        }
        Write-Host "[3/3] Pushing to origin main..." -ForegroundColor Cyan
        & $git push origin main
        Write-Host "Successfully synced with GitHub!" -ForegroundColor Green
    }
    "release" {
        if (-not $Message) {
            Write-Error "Please provide release tag/version. Example: .\scripts\git-sync.ps1 'v0.1.0' release"
            exit 1
        }
        & $git tag -a $Message -m "Release $Message"
        & $git push origin $Message
        Write-Host "Release tag $Message pushed to GitHub!" -ForegroundColor Green
    }
}
