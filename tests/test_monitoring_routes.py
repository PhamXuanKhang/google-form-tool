import sys
import types


class FakeMetricsCollector:
    def __init__(self):
        self.started = False

    @property
    def is_running(self):
        return self.started

    def start(self):
        self.started = True

    def get_system_status(self):
        return {
            "timestamp": 123.0,
            "cpu": {
                "system_cpu": 12.3,
                "process_cpu": 4.5,
            },
            "memory": {
                "total_memory": 1000,
                "available_memory": 500,
                "used_memory": 500,
                "memory_percent": 50.0,
            },
            "threads": 3,
            "network": {
                "bytes_sent_per_sec": 1.0,
                "bytes_recv_per_sec": 2.0,
            },
        }


def test_system_status_returns_monitoring_shape(client, monkeypatch):
    collector = FakeMetricsCollector()
    fake_module = types.SimpleNamespace(
        MetricsCollector=types.SimpleNamespace(get_instance=lambda: collector)
    )
    monkeypatch.setitem(sys.modules, "app.monitoring.metrics_collector", fake_module)

    response = client.get("/system_status")

    assert response.status_code == 200
    data = response.get_json()
    assert data["cpu"]["system_cpu"] == 12.3
    assert data["memory"]["memory_percent"] == 50.0
    assert data["threads"] == 3
    assert data["network"]["bytes_recv_per_sec"] == 2.0
    assert collector.started is True
