import os
import time
import subprocess
import datetime
import xml.etree.ElementTree as ET
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

class WifiBackupGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WiFi配置备份工具")
        self.root.geometry("600x400")
        
        # 设置样式
        style = ttk.Style()
        style.configure("Custom.TButton", padding=5)
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="备份WiFi密码", 
                  command=self.backup_wifi, style="Custom.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="恢复WiFi密码", 
                  command=self.restore_wifi, style="Custom.TButton").pack(side=tk.LEFT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="执行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建文本框和滚动条
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(main_frame, length=300, 
                                      mode='determinate', variable=self.progress_var)
        self.progress.pack(pady=10)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.pack(pady=5)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def decode_output(self, byte_output):
        """尝试多种编码方式解码输出"""
        encodings = ['utf-8', 'gbk', 'cp936', 'gb18030']
        for encoding in encodings:
            try:
                return byte_output.decode(encoding)
            except UnicodeDecodeError:
                continue
        return byte_output.decode('utf-8', errors='ignore')

    def get_wifi_profiles(self):
        """获取所有保存的WiFi配置文件名称"""
        try:
            output = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'])
            output_str = self.decode_output(output)
            
            profiles = []
            for line in output_str.splitlines():
                if "所有用户配置文件" in line or "All User Profile" in line:
                    profile = line.split(':', 1)[1].strip()
                    if profile:
                        profiles.append(profile)
            
            return profiles
        except Exception as e:
            self.log(f"获取WiFi配置文件时出错: {e}")
            return []

    def get_wifi_password(self, profile_name):
        """获取指定WiFi配置的密码"""
        try:
            # 修改命令参数的传递方式，移除多余的引号
            command = ['netsh', 'wlan', 'show', 'profile', 'name=' + profile_name, 'key=clear']
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            output, error = process.communicate()
            
            if process.returncode != 0:
                self.log(f"获取密码时出错: {error}")
                return "获取密码失败"
                
            for line in output.splitlines():
                if "关键内容" in line or "Key Content" in line:
                    password = line.split(':', 1)[1].strip()
                    return password
            return "未找到密码"
        except Exception as e:
            self.log(f"获取密码时出错: {e}")
            return "获取密码失败"

    def backup_wifi_thread(self):
        """在新线程中执行备份操作"""
        profiles = self.get_wifi_profiles()
        if not profiles:
            self.log("未找到任何WiFi配置！")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"WiFi_Backup_{timestamp}.txt"
        
        try:
            total = len(profiles)
            with open(backup_file, 'w', encoding='utf-8') as f:
                for i, profile in enumerate(profiles, 1):
                    self.log(f"正在备份: {profile}")
                    password = self.get_wifi_password(profile)
                    f.write(f"WiFi名称: {profile}\n")
                    f.write(f"密码: {password}\n")
                    f.write("-" * 30 + "\n")
                    
                    # 更新进度
                    progress = (i / total) * 100
                    self.progress_var.set(progress)
                    self.status_label.config(text=f"正在备份... {i}/{total}")
            
            self.log(f"\nWiFi配置已备份到文件: {os.path.abspath(backup_file)}")
            messagebox.showinfo("完成", "WiFi配置备份完成！")
        except Exception as e:
            self.log(f"备份过程中出错: {e}")
            messagebox.showerror("错误", f"备份过程中出错: {e}")
        finally:
            self.progress_var.set(0)
            self.status_label.config(text="就绪")

    def backup_wifi(self):
        """启动备份线程"""
        self.log_text.delete(1.0, tk.END)
        threading.Thread(target=self.backup_wifi_thread, daemon=True).start()

    def create_wifi_profile(self, ssid, password):
        """创建WiFi配置文件"""
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', ssid)
        temp_path = f"temp_{safe_filename}.xml"
        
        xml_template = f"""<?xml version="1.0"?>
    <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
        <name>{ssid}</name>
        <SSIDConfig>
            <SSID>
                <name>{ssid}</name>
            </SSID>
        </SSIDConfig>
        <connectionType>ESS</connectionType>
        <connectionMode>auto</connectionMode>
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
                    <keyMaterial>{password}</keyMaterial>
                </sharedKey>
            </security>
        </MSM>
    </WLANProfile>"""

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(xml_template)
            
            abs_path = os.path.abspath(temp_path)
            # 修改命令参数的传递方式
            command = ['netsh', 'wlan', 'add', 'profile', 'filename=' + abs_path]
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            output, error = process.communicate()
            
            if process.returncode != 0:
                self.log(f"添加配置文件失败: {error}")
                return False
                
            os.remove(temp_path)
            return True
        except Exception as e:
            self.log(f"创建WiFi配置文件时出错: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def restore_wifi_thread(self, backup_file):
        """在新线程中执行恢复操作"""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    self.log("备份文件为空！")
                    messagebox.showwarning("警告", "备份文件为空！")
                    return
                    
                # 使用正则表达式匹配WiFi配置
                wifi_configs = []
                matches = re.finditer(r'WiFi名称: (.*?)\n密码: (.*?)(?=\nWiFi名称:|$)', content, re.DOTALL)
                
                # 预处理所有配置
                for match in matches:
                    ssid = match.group(1).strip()
                    password = match.group(2).strip()
                    if ssid and password != "获取密码失败" and password != "未找到密码":
                        wifi_configs.append((ssid, password))
                
                total_configs = len(wifi_configs)
                if total_configs == 0:
                    self.log("未找到有效的WiFi配置！")
                    messagebox.showwarning("警告", "未找到有效的WiFi配置！")
                    return
                    
                restored_count = 0
                failed_count = 0
                
                for index, (ssid, password) in enumerate(wifi_configs, 1):
                    try:
                        self.log(f"正在恢复 ({index}/{total_configs}): {ssid}")
                        
                        # 更新进度条
                        progress = (index / total_configs) * 100
                        self.progress_var.set(progress)
                        self.status_label.config(text=f"正在恢复... {index}/{total_configs}")
                        
                        # 尝试创建WiFi配置
                        if self.create_wifi_profile(ssid, password):
                            self.log(f"✓ 成功恢复: {ssid}")
                            restored_count += 1
                        else:
                            self.log(f"✗ 恢复失败: {ssid}")
                            failed_count += 1
                            
                    except Exception as e:
                        self.log(f"恢复 {ssid} 时出错: {str(e)}")
                        failed_count += 1
                        continue
                        
                    # 添加短暂延时，避免系统负载过高
                    time.sleep(0.1)

            # 完成后的总结
            summary = (f"\nWiFi配置恢复完成！\n"
                    f"总计: {total_configs} 个\n"
                    f"成功: {restored_count} 个\n"
                    f"失败: {failed_count} 个")
            
            self.log(summary)
            messagebox.showinfo("完成", summary)

        except Exception as e:
            error_msg = f"恢复过程中出错: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("错误", error_msg)
            
        finally:
            # 重置UI状态
            self.progress_var.set(0)
            self.status_label.config(text="就绪")

    def restore_wifi(self):
        """启动恢复操作"""
        try:
            backup_file = filedialog.askopenfilename(
                title="选择WiFi备份文件",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialdir=os.path.dirname(os.path.abspath(__file__))  # 默认打开程序所在目录
            )
            
            if not backup_file:
                return
                
            if not os.path.exists(backup_file):
                messagebox.showerror("错误", "所选文件不存在！")
                return
                
            if os.path.getsize(backup_file) == 0:
                messagebox.showerror("错误", "所选文件为空！")
                return
                
            # 清空日志并开始恢复
            self.log_text.delete(1.0, tk.END)
            self.log(f"选择的备份文件: {backup_file}")
            
            # 启动恢复线程
            threading.Thread(
                target=self.restore_wifi_thread,
                args=(backup_file,),
                daemon=True
            ).start()
            
        except Exception as e:
            error_msg = f"启动恢复过程时出错: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("错误", error_msg)

def main():
    root = tk.Tk()
    app = WifiBackupGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
