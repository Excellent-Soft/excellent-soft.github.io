<#
  EyeRest.ps1 - eye rest reminder for Windows (PowerShell 5.1, no install needed)

  Every N minutes a full screen window with a green village picture appears
  and asks you to look away from the screen for a while.

  Test now:     powershell -ExecutionPolicy Bypass -File EyeRest.ps1 -Now
  Install:      powershell -ExecutionPolicy Bypass -File EyeRest.ps1 -Install
  Uninstall:    powershell -ExecutionPolicy Bypass -File EyeRest.ps1 -Uninstall
  Options:      -IntervalMinutes 20  -RestSeconds 30  -Windowed (smaller window instead of full screen)
  Log file:     %LOCALAPPDATA%\EyeRest\run.log (timings), error.log (errors)

  This file is ASCII only on purpose: Bengali text is stored as \uXXXX escapes
  so it works no matter how the file was saved.
#>
param(
    [int]$IntervalMinutes = 20,
    [int]$RestSeconds = 30,
    [switch]$Now,
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Windowed
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# run quietly in the background so it can never slow down other programs
try { [System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch {}

# ---------------------------------------------------------------- text
function Tx([string]$s) { return [regex]::Unescape($s) }

function BN([int]$n) {
    $out = ''
    foreach ($c in $n.ToString().ToCharArray()) { $out += [char](0x09E6 + [int][string]$c) }
    return $out
}

$TxtTitle    = Tx '\u099A\u09CB\u0996\u09C7\u09B0 \u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE\u09C7\u09B0 \u09B8\u09AE\u09AF\u09BC!'
$TxtMsg      = Tx '\u0995\u09AE\u09CD\u09AA\u09BF\u0989\u099F\u09BE\u09B0\u09C7\u09B0 \u09B8\u09CD\u0995\u09CD\u09B0\u09BF\u09A8 \u09A5\u09C7\u0995\u09C7 \u099A\u09CB\u0996 \u09B8\u09B0\u09BE\u09A8\u0964 \u09A6\u09C2\u09B0\u09C7\u09B0 \u09B8\u09AC\u09C1\u099C \u0997\u09BE\u099B\u09AA\u09BE\u09B2\u09BE\u09B0 \u09A6\u09BF\u0995\u09C7 \u09A4\u09BE\u0995\u09BE\u09A8, \u0985\u09A5\u09AC\u09BE \u099A\u09CB\u0996 \u09AC\u09A8\u09CD\u09A7 \u0995\u09B0\u09C7 \u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE \u09A8\u09BF\u09A8\u0964'
$TxtHint     = Tx '(Esc \u099A\u09BE\u09AA\u09B2\u09C7 \u09AF\u09C7\u0995\u09CB\u09A8\u09CB \u09B8\u09AE\u09AF\u09BC \u09AC\u09A8\u09CD\u09A7 \u0995\u09B0\u09BE \u09AF\u09BE\u09AC\u09C7)'
$TxtDone     = Tx '\u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE \u09B6\u09C7\u09B7\u0964 \u098F\u09AC\u09BE\u09B0 \u0995\u09BE\u099C\u09C7 \u09AB\u09BF\u09B0\u09A4\u09C7 \u09AA\u09BE\u09B0\u09C7\u09A8\u0964'
$TxtPressKey = Tx '(\u09A8\u09BF\u099C\u09C7 \u09A5\u09C7\u0995\u09C7\u0987 \u09AC\u09A8\u09CD\u09A7 \u09B9\u09AC\u09C7, \u099A\u09BE\u0987\u09B2\u09C7 \u0995\u09CD\u09B2\u09BF\u0995 \u0995\u09B0\u09C1\u09A8)'
$TxtCountPre = Tx '\u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE \u09AC\u09BE\u0995\u09BF: '
$TxtCountSuf = Tx ' \u09B8\u09C7\u0995\u09C7\u09A8\u09CD\u09A1'
$TxtTray     = Tx '\u099A\u09CB\u0996\u09C7\u09B0 \u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE\u09C7\u09B0 \u09B0\u09BF\u09AE\u09BE\u0987\u09A8\u09CD\u09A1\u09BE\u09B0'
$TxtMenuNow  = Tx '\u098F\u0996\u09A8\u0987 \u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE \u09A8\u09BF\u09A8'
$TxtMenuExit = Tx '\u09AC\u09A8\u09CD\u09A7 \u0995\u09B0\u09C1\u09A8'
$TxtBalTitle = Tx '\u09B0\u09BF\u09AE\u09BE\u0987\u09A8\u09CD\u09A1\u09BE\u09B0 \u099A\u09BE\u09B2\u09C1 \u09B9\u09AF\u09BC\u09C7\u099B\u09C7'
$TxtBalPre   = Tx '\u09AA\u09CD\u09B0\u09A4\u09BF '
$TxtBalSuf   = Tx ' \u09AE\u09BF\u09A8\u09BF\u099F \u09AA\u09B0 \u099A\u09CB\u0996\u09C7\u09B0 \u09AC\u09BF\u09B6\u09CD\u09B0\u09BE\u09AE\u09C7\u09B0 \u0995\u09A5\u09BE \u09AE\u09A8\u09C7 \u0995\u09B0\u09BE\u09A8\u09CB \u09B9\u09AC\u09C7\u0964'

function Count-Text([int]$n) { return ($TxtCountPre + (BN $n) + $TxtCountSuf) }

# ---------------------------------------------------------------- install / uninstall
$AppDir       = Join-Path $env:LOCALAPPDATA 'EyeRest'
$TargetScript = Join-Path $AppDir 'EyeRest.ps1'
$LnkPath      = Join-Path ([Environment]::GetFolderPath('Startup')) 'EyeRest.lnk'
$PsExe        = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Stop-Existing {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like '*EyeRest.ps1*' -and $_.ProcessId -ne $PID } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Write-Log([string]$msg) {
    try {
        New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
        $log = Join-Path $AppDir 'run.log'
        if ((Test-Path $log) -and ((Get-Item $log).Length -gt 200KB)) { Remove-Item $log -Force }
        Add-Content -Path $log -Value ((Get-Date).ToString('yyyy-MM-dd HH:mm:ss.fff') + '  ' + $msg)
    } catch {}
}

if ($Install) {
    Stop-Existing
    New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
    if ($PSCommandPath -ne $TargetScript) {
        Copy-Item -LiteralPath $PSCommandPath -Destination $TargetScript -Force
    }
    $ArgLine = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$TargetScript`" -IntervalMinutes $IntervalMinutes -RestSeconds $RestSeconds"
    if ($Windowed) { $ArgLine += ' -Windowed' }
    $ws  = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($LnkPath)
    $lnk.TargetPath       = $PsExe
    $lnk.Arguments        = $ArgLine
    $lnk.WorkingDirectory = $AppDir
    $lnk.WindowStyle      = 7
    $lnk.Save()
    Start-Process -FilePath $PsExe -ArgumentList $ArgLine -WindowStyle Hidden
    Write-Host "Installed. Reminder every $IntervalMinutes minutes, rest $RestSeconds seconds."
    Write-Host "It starts automatically when you sign in to Windows. Look for the tray icon near the clock."
    exit
}

if ($Uninstall) {
    Stop-Existing
    if (Test-Path $LnkPath) { Remove-Item $LnkPath -Force }
    Write-Host "Removed from startup and stopped. You may delete the folder: $AppDir"
    exit
}

# ---------------------------------------------------------------- drawing helpers
$script:BrushCache = @{}
function Br([int]$r, [int]$gr, [int]$b, [int]$a = 255) {
    $k = "$r,$gr,$b,$a"
    if (-not $script:BrushCache.ContainsKey($k)) {
        $script:BrushCache[$k] = New-Object System.Drawing.SolidBrush -ArgumentList ([System.Drawing.Color]::FromArgb($a, $r, $gr, $b))
    }
    return $script:BrushCache[$k]
}
$script:BirdPen = New-Object System.Drawing.Pen -ArgumentList ([System.Drawing.Color]::FromArgb(70, 80, 90)), ([single]2)

function Rect($g, $br, $x, $y, $w, $h) { $g.FillRectangle($br, [single]$x, [single]$y, [single]$w, [single]$h) }
function Oval($g, $br, $x, $y, $w, $h) { $g.FillEllipse($br, [single]$x, [single]$y, [single]$w, [single]$h) }
function Pt($x, $y) { return (New-Object System.Drawing.PointF -ArgumentList ([single]$x), ([single]$y)) }
function Poly($g, $br, $pts) { $g.FillPolygon($br, [System.Drawing.PointF[]]$pts) }

function Draw-Cloud($g, [double]$x, [double]$y, [double]$s) {
    $c = Br 255 255 255 225
    Oval $g $c $x $y ($s * 2.2) ($s * 0.9)
    Oval $g $c ($x + $s * 0.5) ($y - $s * 0.45) ($s * 1.2) ($s * 1.0)
    Oval $g $c ($x + $s * 1.2) ($y - $s * 0.2) ($s * 1.3) ($s * 0.9)
}

function Draw-Tree($g, [double]$x, [double]$y, [double]$s) {
    Rect $g (Br 112 78 46) ($x - $s * 0.04) ($y - $s * 0.50) ($s * 0.08) ($s * 0.50)
    Oval $g (Br 46 120 66) ($x - $s * 0.32) ($y - $s * 0.95) ($s * 0.64) ($s * 0.55)
    Oval $g (Br 62 148 78) ($x - $s * 0.40) ($y - $s * 0.80) ($s * 0.45) ($s * 0.40)
    Oval $g (Br 62 148 78) ($x - $s * 0.05) ($y - $s * 0.80) ($s * 0.45) ($s * 0.40)
    Oval $g (Br 84 168 92) ($x - $s * 0.20) ($y - $s * 1.05) ($s * 0.40) ($s * 0.40)
}

function Draw-Bird($g, [double]$x, [double]$y, [double]$s) {
    $g.DrawLine($script:BirdPen, [single]($x - $s), [single]$y, [single]$x, [single]($y + $s * 0.45))
    $g.DrawLine($script:BirdPen, [single]$x, [single]($y + $s * 0.45), [single]($x + $s), [single]$y)
}

function Draw-Scene($g, [int]$w, [int]$h) {
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $horizon = $h * 0.56

    # sky
    $skyRect = New-Object System.Drawing.Rectangle -ArgumentList 0, 0, $w, ([int]($horizon + 2))
    $sky = New-Object System.Drawing.Drawing2D.LinearGradientBrush -ArgumentList $skyRect, ([System.Drawing.Color]::FromArgb(110, 185, 235)), ([System.Drawing.Color]::FromArgb(230, 246, 232)), ([System.Drawing.Drawing2D.LinearGradientMode]::Vertical)
    $g.FillRectangle($sky, $skyRect)
    $sky.Dispose()

    # sun
    $sx = $w * 0.82; $sy = $h * 0.15; $sr = $h * 0.06
    Oval $g (Br 255 244 190 70)  ($sx - $sr * 2.0) ($sy - $sr * 2.0) ($sr * 4.0) ($sr * 4.0)
    Oval $g (Br 255 236 150 120) ($sx - $sr * 1.5) ($sy - $sr * 1.5) ($sr * 3.0) ($sr * 3.0)
    Oval $g (Br 255 223 100)     ($sx - $sr)       ($sy - $sr)       ($sr * 2.0) ($sr * 2.0)

    # clouds and birds
    Draw-Cloud $g ($w * 0.06) ($h * 0.50) ($h * 0.040)
    Draw-Cloud $g ($w * 0.40) ($h * 0.47) ($h * 0.035)
    Draw-Cloud $g ($w * 0.62) ($h * 0.50) ($h * 0.030)
    Draw-Bird $g ($w * 0.30) ($h * 0.50) ($h * 0.014)
    Draw-Bird $g ($w * 0.33) ($h * 0.53) ($h * 0.010)
    Draw-Bird $g ($w * 0.70) ($h * 0.47) ($h * 0.012)

    # far hills
    Oval $g (Br 121 181 126) (-$w * 0.10) ($horizon - $h * 0.10) ($w * 0.70) ($h * 0.22)
    Oval $g (Br 104 168 116) ($w * 0.35)  ($horizon - $h * 0.07) ($w * 0.80) ($h * 0.18)

    # fields: base colour then perspective stripes
    Rect $g (Br 126 196 92) 0 $horizon $w ($h - $horizon + 1)
    $n = 9
    for ($i = 0; $i -lt $n; $i++) {
        $y0 = $horizon + ($h - $horizon) * [math]::Pow($i / $n, 1.6)
        $y1 = $horizon + ($h - $horizon) * [math]::Pow(($i + 1) / $n, 1.6)
        if ($i % 2 -eq 0) { $col = Br 118 190 84 } else { $col = Br 142 209 106 }
        Rect $g $col 0 $y0 $w ($y1 - $y0 + 1)
    }

    # tree line on the horizon
    for ($i = 0; $i -lt 14; $i++) {
        $tx = $w * ($i / 13.0)
        Oval $g (Br 66 138 82) ($tx - $h * 0.05) ($horizon - $h * 0.035) ($h * 0.10) ($h * 0.07)
    }

    # pond
    Oval $g (Br 108 172 198) ($w * 0.14) ($h * 0.785) ($w * 0.30) ($h * 0.105)
    Oval $g (Br 140 202 228) ($w * 0.15) ($h * 0.790) ($w * 0.28) ($h * 0.092)
    Oval $g (Br 255 255 255 120) ($w * 0.20) ($h * 0.805) ($w * 0.06) ($h * 0.014)

    # dirt path
    Poly $g (Br 214 186 136) @((Pt ($w * 0.655) ($h * 0.66)), (Pt ($w * 0.685) ($h * 0.66)), (Pt ($w * 0.82) $h), (Pt ($w * 0.52) $h))

    # village hut
    $hx = $w * 0.67; $hy = $h * 0.66; $hs = $h * 0.17
    Rect $g (Br 214 170 120) ($hx - $hs * 0.70) ($hy - $hs * 0.55) ($hs * 1.40) ($hs * 0.55)
    Poly $g (Br 170 120 55) @((Pt ($hx - $hs * 0.95) ($hy - $hs * 0.52)), (Pt $hx ($hy - $hs * 1.30)), (Pt ($hx + $hs * 0.95) ($hy - $hs * 0.52)))
    Rect $g (Br 95 60 35) ($hx - $hs * 0.12) ($hy - $hs * 0.36) ($hs * 0.24) ($hs * 0.36)

    # trees
    Draw-Tree $g ($w * 0.08) ($h * 0.74) ($h * 0.34)
    Draw-Tree $g ($w * 0.90) ($h * 0.70) ($h * 0.30)
    Draw-Tree $g ($w * 0.80) ($h * 0.63) ($h * 0.20)
    Draw-Tree $g ($w * 0.47) ($h * 0.62) ($h * 0.16)

    # translucent panel behind the text
    Rect $g (Br 18 45 32 165) ($w * 0.12) ($h * 0.045) ($w * 0.76) ($h * 0.40)
}

# ---------------------------------------------------------------- reminder window
$script:Showing = $false
$script:Done = $false
$script:Remaining = 0
$script:CloseIn = 0
$script:SceneBmp = $null
$script:W = 0
$script:H = 0

function New-Label([string]$text, [double]$px, [bool]$bold, $color, [double]$top, [double]$height) {
    $l = New-Object System.Windows.Forms.Label
    $style = [System.Drawing.FontStyle]::Regular
    if ($bold) { $style = [System.Drawing.FontStyle]::Bold }
    $l.Font = New-Object System.Drawing.Font -ArgumentList 'Nirmala UI', ([single]$px), $style, ([System.Drawing.GraphicsUnit]::Pixel)
    $l.ForeColor = $color
    $l.BackColor = [System.Drawing.Color]::Transparent
    $l.AutoSize = $false
    $l.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    $l.Text = $text
    $l.SetBounds([int]($script:W * 0.14), [int]$top, [int]($script:W * 0.72), [int]$height)
    $l.Add_Click({ if ($script:Done) { $script:Form.Close() } })
    return $l
}

function Show-Reminder {
    if ($script:Showing) { return }
    $script:Showing = $true
    $script:Timer.Stop()
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Log 'reminder start'
    try {
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        if ($Windowed) {
            $ww = [int]($screen.Width * 0.7)
            $wh = [int]($screen.Height * 0.7)
            $wx = $screen.X + [int](($screen.Width - $ww) / 2)
            $wy = $screen.Y + [int](($screen.Height - $wh) / 2)
            $bounds = New-Object System.Drawing.Rectangle -ArgumentList $wx, $wy, $ww, $wh
        } else {
            $bounds = $screen
        }
        $script:W = $bounds.Width
        $script:H = $bounds.Height
        $h = $script:H
        $script:Remaining = $RestSeconds
        $script:Done = $false

        $form = New-Object System.Windows.Forms.Form
        $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
        $form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
        $form.Bounds = $bounds
        $form.TopMost = $true
        $form.ShowInTaskbar = $false
        $form.KeyPreview = $true
        $form.BackColor = [System.Drawing.Color]::FromArgb(126, 196, 92)
        [System.Windows.Forms.Form].GetProperty('DoubleBuffered', [System.Reflection.BindingFlags]'Instance,NonPublic').SetValue($form, $true, $null)
        $script:Form = $form

        $white  = [System.Drawing.Color]::White
        $cream  = [System.Drawing.Color]::FromArgb(255, 240, 170)
        $soft   = [System.Drawing.Color]::FromArgb(205, 225, 205)
        $form.Controls.Add((New-Label $TxtTitle ($h * 0.065) $true $white ($h * 0.060) ($h * 0.095)))
        $form.Controls.Add((New-Label $TxtMsg ($h * 0.030) $false $white ($h * 0.160) ($h * 0.120)))
        $script:LblCount = New-Label (Count-Text $script:Remaining) ($h * 0.050) $true $cream ($h * 0.290) ($h * 0.075)
        $form.Controls.Add($script:LblCount)
        $script:LblHint = New-Label $TxtHint ($h * 0.024) $false $soft ($h * 0.375) ($h * 0.050)
        $form.Controls.Add($script:LblHint)

        # draw the picture once into a bitmap; repaints only copy the bitmap (fast)
        $script:SceneBmp = New-Object System.Drawing.Bitmap -ArgumentList $script:W, $script:H
        $sg = [System.Drawing.Graphics]::FromImage($script:SceneBmp)
        Draw-Scene $sg $script:W $script:H
        $sg.Dispose()
        Write-Log ('scene drawn after ' + $sw.ElapsedMilliseconds + ' ms')

        $form.Add_Paint({ param($sender, $e) $e.Graphics.DrawImageUnscaled($script:SceneBmp, 0, 0) })
        $form.Add_MouseClick({ param($sender, $e) if ($script:Done) { $sender.Close() } })
        $form.Add_KeyDown({ param($sender, $e)
            if ($e.KeyCode -eq [System.Windows.Forms.Keys]::Escape -or $script:Done) { $sender.Close() }
        })
        $form.Add_Shown({ param($sender, $e) $sender.Activate() })

        $script:CountTimer = New-Object System.Windows.Forms.Timer
        $script:CountTimer.Interval = 1000
        $script:CountTimer.Add_Tick({
            if (-not $script:Done) {
                $script:Remaining--
                if ($script:Remaining -le 0) {
                    $script:Done = $true
                    $script:CloseIn = 4
                    $script:LblCount.Text = $TxtDone
                    $script:LblHint.Text = $TxtPressKey
                    [System.Media.SystemSounds]::Asterisk.Play()
                } else {
                    $script:LblCount.Text = (Count-Text $script:Remaining)
                }
            } else {
                # the window closes itself, so it can never get stuck on screen
                $script:CloseIn--
                if ($script:CloseIn -le 0) { $script:Form.Close() }
            }
        })

        [System.Media.SystemSounds]::Exclamation.Play()
        $script:CountTimer.Start()
        Write-Log ('showing after ' + $sw.ElapsedMilliseconds + ' ms')
        [void]$form.ShowDialog()
    }
    catch {
        $log = Join-Path $AppDir 'error.log'
        New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
        Add-Content -Path $log -Value ((Get-Date).ToString() + "`r`n" + ($_ | Out-String))
        Write-Host ($_ | Out-String)
    }
    finally {
        if ($script:CountTimer) { $script:CountTimer.Stop(); $script:CountTimer.Dispose(); $script:CountTimer = $null }
        if ($script:Form) { $script:Form.Dispose(); $script:Form = $null }
        if ($script:SceneBmp) { $script:SceneBmp.Dispose(); $script:SceneBmp = $null }
        $script:Showing = $false
        $script:Timer.Start()
        $mem = [math]::Round([System.Diagnostics.Process]::GetCurrentProcess().WorkingSet64 / 1MB)
        Write-Log ('closed after ' + $sw.ElapsedMilliseconds + ' ms, memory ' + $mem + ' MB')
    }
}

# ---------------------------------------------------------------- main
$script:Timer = New-Object System.Windows.Forms.Timer
$script:Timer.Interval = [int]([math]::Max(1, $IntervalMinutes) * 60 * 1000)
$script:Timer.Add_Tick({ Show-Reminder })

if ($Now) {
    Show-Reminder
    exit
}

$mutex = New-Object System.Threading.Mutex -ArgumentList $false, 'Local\EyeRestReminderBn'
if (-not $mutex.WaitOne(0)) { exit }
Write-Log ('started, pid ' + $PID + ', every ' + $IntervalMinutes + ' min, rest ' + $RestSeconds + ' s')

$script:Notify = New-Object System.Windows.Forms.NotifyIcon
$script:Notify.Icon = [System.Drawing.SystemIcons]::Information
$script:Notify.Text = $TxtTray
$menu = New-Object System.Windows.Forms.ContextMenuStrip
$miNow  = $menu.Items.Add($TxtMenuNow)
$miExit = $menu.Items.Add($TxtMenuExit)
$miNow.Add_Click({ Show-Reminder })
$miExit.Add_Click({
    $script:Timer.Stop()
    $script:Notify.Visible = $false
    [System.Windows.Forms.Application]::Exit()
})
$script:Notify.ContextMenuStrip = $menu
$script:Notify.Visible = $true
$script:Notify.ShowBalloonTip(4000, $TxtBalTitle, ($TxtBalPre + (BN $IntervalMinutes) + $TxtBalSuf), [System.Windows.Forms.ToolTipIcon]::Info)

$script:Timer.Start()
[System.Windows.Forms.Application]::Run()
