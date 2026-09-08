"""
环境数据模拟器
模拟田间环境传感器数据：温度、空气湿度、光照、土壤含水率
支持手动触发异常状态（高温、高湿、土壤过湿等）
"""
import random
import time
import threading
from typing import Optional

class EnvironmentSimulator:
    def __init__(self, device_id: str = "sim-001", plot_id: str = "plot-1"):
        self.device_id = device_id
        self.plot_id = plot_id
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.interval = 5  # 每5秒生成一条数据
        self.history = []
        self.max_history = 288  # 保留24小时数据（5分钟一条的话是288条）

        # 基础值
        self.base_temp = 26.0
        self.base_humidity = 65.0
        self.base_light = 8000.0
        self.base_soil_moisture = 55.0

        # 噪声幅度
        self.temp_noise = 1.5
        self.humidity_noise = 3.0
        self.light_noise = 1000.0
        self.soil_noise = 2.5

        # 异常状态
        self.anomaly = None  # None, 'high_temp', 'high_humidity', 'soil_wet', 'normal'

    def _generate_reading(self):
        """生成一条环境数据"""
        now = time.time()

        # 基于时间的日周期变化
        hour = (time.localtime(now).tm_hour + time.localtime(now).tm_min / 60)
        # 温度：中午高，凌晨低
        temp_daily = 5 * -((hour - 14) / 6) ** 2
        # 光照：白天强，晚上弱
        light_daily = 8000 * max(0, 1 - abs(hour - 12) / 8)

        temp = self.base_temp + temp_daily + random.uniform(-self.temp_noise, self.temp_noise)
        humidity = self.base_humidity + random.uniform(-self.humidity_noise, self.humidity_noise)
        light = max(0, self.base_light + light_daily + random.uniform(-self.light_noise, self.light_noise))
        soil_moisture = self.base_soil_moisture + random.uniform(-self.soil_noise, self.soil_noise)

        # 应用异常状态
        if self.anomaly == 'high_temp':
            temp += 8
        elif self.anomaly == 'high_humidity':
            humidity += 20
        elif self.anomaly == 'soil_wet':
            soil_moisture += 25
        elif self.anomaly == 'low_light':
            light = max(0, light * 0.3)

        temp = round(max(-10, min(50, temp)), 1)
        humidity = round(max(0, min(100, humidity)), 1)
        light = round(max(0, min(100000, light)), 0)
        soil_moisture = round(max(0, min(100, soil_moisture)), 1)

        return {
            "device_id": self.device_id,
            "plot_id": self.plot_id,
            "timestamp": now,
            "source": "simulator",
            "temperature": temp,
            "humidity": humidity,
            "light": light,
            "soil_moisture": soil_moisture,
        }

    def _loop(self):
        while self.running:
            reading = self._generate_reading()
            self.history.append(reading)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            time.sleep(self.interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def inject_reading(self, device_id: str, plot_id: str, temperature: float,
                       humidity: float, light: float, soil_moisture: float,
                       source: str = "sensor"):
        """接收外部上报的环境数据"""
        reading = {
            "device_id": device_id,
            "plot_id": plot_id,
            "timestamp": time.time(),
            "source": source,
            "temperature": temperature,
            "humidity": humidity,
            "light": light,
            "soil_moisture": soil_moisture,
        }
        self.history.append(reading)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_current(self):
        if self.history:
            return self.history[-1]
        return self._generate_reading()

    def get_series(self, limit: int = 60):
        return self.history[-limit:] if self.history else []

    def set_anomaly(self, anomaly: Optional[str]):
        """设置异常状态: high_temp, high_humidity, soil_wet, low_light, None(恢复正常)"""
        self.anomaly = anomaly

    def set_base_values(self, temp=None, humidity=None, light=None, soil=None):
        if temp is not None:
            self.base_temp = temp
        if humidity is not None:
            self.base_humidity = humidity
        if light is not None:
            self.base_light = light
        if soil is not None:
            self.base_soil_moisture = soil

    def get_status(self):
        return {
            "running": self.running,
            "device_id": self.device_id,
            "plot_id": self.plot_id,
            "interval": self.interval,
            "anomaly": self.anomaly,
            "base_temp": self.base_temp,
            "base_humidity": self.base_humidity,
            "base_light": self.base_light,
            "base_soil_moisture": self.base_soil_moisture,
            "history_count": len(self.history),
        }


# 全局模拟器实例
_simulator: Optional[EnvironmentSimulator] = None

def get_simulator() -> EnvironmentSimulator:
    global _simulator
    if _simulator is None:
        _simulator = EnvironmentSimulator()
        _simulator.start()
    return _simulator
