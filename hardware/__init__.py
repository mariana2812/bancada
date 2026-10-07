"""
Escolhe entre o hardware REAL (Raspberry Pi) e o SIMULADO (computador).
O resto do sistema só chama criar_hardware() e não precisa saber qual é.
"""

import config


def _deve_simular():
    if config.SIMULAR is not None:
        return config.SIMULAR
    try:
        import RPi.GPIO  # noqa: F401  (só testa se existe)
        return False
    except (ImportError, RuntimeError):
        return True


def criar_hardware():
    """Devolve (motor, sensor_altura, celula_carga, emergencia, simulado)."""
    if _deve_simular():
        from . import simulacao
        return (
            simulacao.MotorSimulado(),
            simulacao.SensorAlturaSimulado(),
            simulacao.CelulaCargaSimulada(),
            simulacao.EmergenciaSimulada(),
            True,
        )

    from .motor import Motor
    from .sensor_altura import SensorAltura
    from .celula_carga import CelulaCarga
    from .emergencia import Emergencia

    return Motor(), SensorAltura(), CelulaCarga(), Emergencia(), False
