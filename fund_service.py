"""
基金查看系统 - Windows服务
用于将基金服务注册为Windows服务，实现开机自启
"""
import sys
import os

# 确保服务可以找到用户安装的包
site_packages = r"C:\Users\84972\AppData\Roaming\Python\Python312\site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

# 添加 pywin32 相关的 DLL 路径到环境变量
pywin32_system32 = os.path.join(site_packages, "pywin32_system32")
win32 = os.path.join(site_packages, "win32")
win32_lib = os.path.join(site_packages, "win32", "lib")
pythonwin = os.path.join(site_packages, "Pythonwin")

os.environ["PATH"] = f"{pywin32_system32};{win32};{win32_lib};{pythonwin};{os.environ.get('PATH', '')}"

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import threading
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class FundService(win32serviceutil.ServiceFramework):
    """基金服务类"""
    _svc_name_ = "FundService"
    _svc_display_name_ = "基金查看系统服务"
    _svc_description_ = "提供基金实时数据查询服务，基于天天基金网API"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = False
        self.flask_thread = None

    def SvcStop(self):
        """停止服务"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        if self.flask_thread:
            self.flask_thread.join(timeout=10)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        """运行服务"""
        # 切换工作目录到脚本所在目录
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(current_dir)
            
            # 重定向输出到日志文件，以便调试
            sys.stdout = open(os.path.join(current_dir, 'service_stdout.log'), 'a', encoding='utf-8')
            sys.stderr = open(os.path.join(current_dir, 'service_stderr.log'), 'a', encoding='utf-8')
        except:
            pass
            
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.is_running = True
        self.flask_thread = threading.Thread(target=self.run_flask)
        self.flask_thread.daemon = True
        self.flask_thread.start()
        
        # 等待停止信号
        while self.is_running:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break

    def run_flask(self):
        """运行Flask应用"""
        try:
            # 导入并运行Flask应用
            from app import app
            app.run(debug=False, host='0.0.0.0', port=5000)
        except Exception as e:
            servicemanager.LogMsg(servicemanager.EVENTLOG_ERROR_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, f'启动失败: {str(e)}'))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FundService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FundService)