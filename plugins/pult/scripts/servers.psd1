# The servers started at logon (start-servers.ps1) and watched (watch-servers.ps1).
# Session: the session name. Lead = $true: a background project lead "L: <name>" with the
# dev-kit project-lead skill. Otherwise a Remote Control server; Prefix (optional) starts every
# session name it spawns. Hub = $true: the Pult hub server; it has no Path, the scripts run it in the
# home folder ($env:USERPROFILE). Keep this file saved as UTF-8 with BOM (plugins/dev-kit/claude-facts.md,
# "Windows PowerShell 5.1 misreads Cyrillic in a script saved without a BOM").
@{
    Servers = @(
        @{ Session = 'L: Zhratva'; Lead = $true; Path = 'C:\Users\korov\MyRepositories\Zhratva' }
        @{ Session = 'L: Prishch'; Lead = $true; Path = 'C:\Users\korov\MyRepositories\Prishch' }
        @{ Session = 'L: ClaudeDevKit'; Lead = $true; Path = 'C:\Users\korov\MyRepositories\ClaudeDevKit' }
        @{ Session = 'Pult'; Prefix = 'Pult'; Hub = $true }
    )
}
