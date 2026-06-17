"""
agents/system_agent.py
Agente de sistema: monitora CPU, RAM, status dos serviços e logs.
Responsabilidade única: informações sobre o estado do sistema.
"""
from __future__ import annotations

import platform
from typing import Any

from logs.logger import get_module_logger

log = get_module_logger(__name__)


class SystemAgent:
    """
    Agente que inspeciona e reporta o estado do sistema.
    Não executa comandos arbitrários — apenas lê métricas seguras.
    """

    def get_system_info(self) -> dict[str, Any]:
        """Retorna informações básicas do sistema."""
        info: dict[str, Any] = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }
        try:
            import psutil
            info.update({
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_total_gb": round(psutil.virtual_memory().total / 1e9, 1),
                "memory_used_gb": round(psutil.virtual_memory().used / 1e9, 1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_total_gb": round(psutil.disk_usage("/").total / 1e9, 1),
                "disk_used_percent": psutil.disk_usage("/").percent,
            })
        except ImportError:
            info["psutil"] = "not installed"
        return info

    def get_service_status(self, services: dict[str, Any]) -> dict[str, str]:
        """
        Verifica status dos serviços configurados.

        Args:
            services: Dicionário {nome: instancia_ou_None}

        Returns:
            Dicionário {nome: "ok" | "offline" | "not_configured"}
        """
        status: dict[str, str] = {}
        for name, service in services.items():
            if service is None:
                status[name] = "not_configured"
            else:
                status[name] = "ok"
        return status

    def get_stats_summary(self, stats: dict[str, Any]) -> str:
        """Formata estatísticas para exibição no terminal."""
        lines = [
            f"Sistema: {platform.system()} {platform.release()}",
            f"Python: {platform.python_version()}",
        ]
        if "cpu_percent" in stats:
            lines.append(f"CPU: {stats['cpu_percent']}%")
        if "memory_percent" in stats:
            lines.append(f"RAM: {stats['memory_percent']}%")
        for k, v in stats.items():
            if k not in ("cpu_percent", "memory_percent", "platform", "python_version",
                         "platform_version", "architecture", "disk_total_gb",
                         "memory_total_gb", "memory_used_gb"):
                lines.append(f"{k}: {v}")
        return "\n".join(lines)
