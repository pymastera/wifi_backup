Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 创建主窗体
$form = New-Object System.Windows.Forms.Form
$form.Text = "WiFi配置备份工具"
$form.Size = New-Object System.Drawing.Size(600,400)
$form.StartPosition = "CenterScreen"

# 创建按钮面板
$buttonPanel = New-Object System.Windows.Forms.Panel
$buttonPanel.Dock = [System.Windows.Forms.DockStyle]::Top
$buttonPanel.Height = 40

# 备份按钮
$backupButton = New-Object System.Windows.Forms.Button
$backupButton.Text = "备份WiFi密码"
$backupButton.Location = New-Object System.Drawing.Point(10,10)
$backupButton.Size = New-Object System.Drawing.Size(120,25)

# 恢复按钮
$restoreButton = New-Object System.Windows.Forms.Button
$restoreButton.Text = "恢复WiFi密码"
$restoreButton.Location = New-Object System.Drawing.Point(160,10)
$restoreButton.Size = New-Object System.Drawing.Size(120,25)

# 日志文本框
$logBox = New-Object System.Windows.Forms.RichTextBox
$logBox.Location = New-Object System.Drawing.Point(10,50)
$logBox.Size = New-Object System.Drawing.Size(565,250)
$logBox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right -bor [System.Windows.Forms.AnchorStyles]::Bottom

# 进度条
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(10,310)
$progressBar.Size = New-Object System.Drawing.Size(565,23)
$progressBar.Style = "Continuous"

# 状态标签
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(10,335)
$statusLabel.Size = New-Object System.Drawing.Size(565,20)
$statusLabel.Text = "就绪"

# 添加控件到窗体
$buttonPanel.Controls.Add($backupButton)
$buttonPanel.Controls.Add($restoreButton)
$form.Controls.Add($buttonPanel)
$form.Controls.Add($logBox)
$form.Controls.Add($progressBar)
$form.Controls.Add($statusLabel)

# 日志函数
function Write-Log {
    param([string]$message)
    $logBox.AppendText("$message`r`n")
    $logBox.ScrollToCaret()
    [System.Windows.Forms.Application]::DoEvents()
}

# 获取WiFi配置文件列表
function Get-WifiProfiles {
    try {
        $profiles = netsh wlan show profiles | Select-String "所有用户配置文件\s+:\s(.+)" | 
                   ForEach-Object { $_.Matches.Groups[1].Value.Trim() }
        return $profiles
    }
    catch {
        Write-Log "获取WiFi配置文件时出错: $_"
        return @()
    }
}

# 获取指定WiFi的密码
function Get-WifiPassword {
    param([string]$profileName)
    try {
        $output = netsh wlan show profile name="$profileName" key=clear
        $password = $output | Select-String "关键内容\s+:\s(.+)" | 
                   ForEach-Object { $_.Matches.Groups[1].Value.Trim() }
        return $password
    }
    catch {
        Write-Log "获取密码时出错: $_"
        return "获取密码失败"
    }
}

# 备份WiFi配置
function Backup-WifiProfiles {
    $profiles = Get-WifiProfiles
    if ($profiles.Count -eq 0) {
        Write-Log "未找到任何WiFi配置！"
        return
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "WiFi_Backup_$timestamp.txt"
    
    try {
        $total = $profiles.Count
        $i = 0
        
        foreach ($profile in $profiles) {
            $i++
            Write-Log "正在备份: $profile"
            $password = Get-WifiPassword $profile
            
            Add-Content -Path $backupFile -Value "WiFi名称: $profile"
            Add-Content -Path $backupFile -Value "密码: $password"
            Add-Content -Path $backupFile -Value ("-" * 30)
            
            $progress = ($i / $total) * 100
            $progressBar.Value = $progress
            $statusLabel.Text = "正在备份... $i/$total"
        }
        
        Write-Log "`nWiFi配置已备份到文件: $((Get-Item $backupFile).FullName)"
        [System.Windows.Forms.MessageBox]::Show("WiFi配置备份完成！", "完成")
    }
    catch {
        Write-Log "备份过程中出错: $_"
        [System.Windows.Forms.MessageBox]::Show("备份过程中出错: $_", "错误")
    }
    finally {
        $progressBar.Value = 0
        $statusLabel.Text = "就绪"
    }
}

# 恢复WiFi配置
# 恢复WiFi配置
function Restore-WifiProfiles {
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Filter = "Text files (*.txt)|*.txt|All files (*.*)|*.*"
    $openFileDialog.InitialDirectory = $PSScriptRoot
    
    if ($openFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $backupFile = $openFileDialog.FileName
        
        if (-not (Test-Path $backupFile)) {
            [System.Windows.Forms.MessageBox]::Show("所选文件不存在！", "错误")
            return
        }
        
        if ((Get-Item $backupFile).Length -eq 0) {
            [System.Windows.Forms.MessageBox]::Show("所选文件为空！", "错误")
            return
        }
        
        $logBox.Clear()
        Write-Log "选择的备份文件: $backupFile"
        
        try {
            $content = Get-Content $backupFile -Raw
            $wifiConfigs = [regex]::Matches($content, "WiFi名称: (.*?)`r?`n密码: (.*?)(?=`r?`n-{30}|$)")
            
            $total = $wifiConfigs.Count
            $restored = 0
            $failed = 0
            
            for ($i = 0; $i -lt $total; $i++) {
                $ssid = $wifiConfigs[$i].Groups[1].Value.Trim()
                $password = $wifiConfigs[$i].Groups[2].Value.Trim()
                
                Write-Log "正在恢复 ($($i+1)/$total): $ssid"
                $progressBar.Value = (($i + 1) / $total) * 100
                $statusLabel.Text = "正在恢复... $($i+1)/$total"
                
                try {
                    

                    $xmlPath = Join-Path $env:TEMP "temp_$($ssid -replace '[<>:"/\\|?*]', '_').xml"
                    
                    # 使用更完整的XML配置
                    $xml = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>$ssid</name>
    <SSIDConfig>
        <SSID>
            <hex>$([System.BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($ssid)).Replace("-",""))</hex>
            <name>$ssid</name>
        </SSID>
        <nonBroadcast>false</nonBroadcast>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <autoSwitch>false</autoSwitch>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>$password</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
    <MacRandomization xmlns="http://www.microsoft.com/networking/WLAN/profile/v3">
        <enableRandomization>false</enableRandomization>
    </MacRandomization>
</WLANProfile>
"@
                    # 保存XML文件
                    $xml | Out-File -FilePath $xmlPath -Encoding UTF8 -Force
                    
                    # 添加配置文件
                    $result = netsh wlan add profile filename="$xmlPath" user=all
                    
                    
                }
                catch {
                    Write-Log "恢复 $ssid 时出错: $_"
                    $failed++
                }
                finally {
                    # 清理临时文件
                    if (Test-Path $xmlPath) {
                        Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
                    }
                }
                
            }
            
            $summary = @"
WiFi配置恢复完成！
总计: $total 个
成功: $restored 个
失败: $failed 个
"@
            Write-Log "`n$summary"
            [System.Windows.Forms.MessageBox]::Show($summary, "完成")
        }
        catch {
            Write-Log "恢复过程中出错: $_"
            [System.Windows.Forms.MessageBox]::Show("恢复过程中出错: $_", "错误")
        }
        finally {
            $progressBar.Value = 0
            $statusLabel.Text = "就绪"
        }
    }
}


# 绑定按钮事件
$backupButton.Add_Click({ Backup-WifiProfiles })
$restoreButton.Add_Click({ Restore-WifiProfiles })

# 显示窗体
$form.ShowDialog()
