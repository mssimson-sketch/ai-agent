"""
Мониторинг системы — следит за здоровьем компьютера
"""
import psutil
import threading
import time


class SystemMonitor:
    def __init__(self, alert_callback=None):
        self.alert_callback = alert_callback
        self.monitoring = False
        self.thresholds = {
            "cpu": 90,
            "memory": 85,
            "disk": 95,
            "battery": 15
        }
        self.last_alerts = {}
        self.cooldown = 300  # 5 минут

    def start(self):
        self.monitoring = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        print("📊 Мониторинг запущен")

    def stop(self):
        self.monitoring = False

    def _loop(self):
        while self.monitoring:
            try:
                self._check_all()
            except:
                pass
            time.sleep(30)

    def _alert(self, key: str, msg: str):
        now = time.time()
        if now - self.last_alerts.get(key, 0) > self.cooldown:
            self.last_alerts[key] = now
            if self.alert_callback:
                self.alert_callback(msg)

    def _check_all(self):
        cpu = psutil.cpu_percent(interval=2)
        if cpu > self.thresholds["cpu"]:
            self._alert("cpu", f"Внимание! Процессор загружен на {cpu}%")

        mem = psutil.virtual_memory()
        if mem.percent > self.thresholds["memory"]:
            self._alert("memory", f"Внимание! Память загружена на {mem.percent}%")

        disk = psutil.disk_usage('/')
        if disk.percent > self.thresholds["disk"]:
            self._alert("disk", f"Внимание! Диск заполнен на {disk.percent}%")

        battery = psutil.sensors_battery()
        if battery and not battery.power_plugged and battery.percent < self.thresholds["battery"]:
            self._alert("battery", f"Батарея разряжена: {battery.percent}%! Подключите зарядку!")