# calendar_helper.py
from datetime import datetime, date, timedelta

# Calendario Laboral 2025 para Zaragoza (Festivos Nacionales, de Aragón y locales)
HOLIDAYS = {
    date(2025, 1, 1),  # Año Nuevo
    date(2025, 1, 6),  # Epifanía del Señor (Reyes)
    date(2025, 1, 29),  # San Valero (Local Zaragoza)
    date(2025, 3, 5),  # Cincomarzada (Local Zaragoza)
    date(2025, 4, 17),  # Jueves Santo
    date(2025, 4, 18),  # Viernes Santo
    date(2025, 4, 23),  # San Jorge (Día de Aragón)
    date(2025, 5, 1),  # Fiesta del Trabajo
    date(2025, 8, 15),  # Asunción de la Virgen
    date(2025, 10, 13),  # Lunes siguiente a la Fiesta Nacional
    date(2025, 11, 1),  # Todos los Santos
    date(2025, 12, 6),  # Día de la Constitución
    date(2025, 12, 8),  # Inmaculada Concepción
    date(2025, 12, 25),  # Navidad
}


def is_workday(current_date):
    """
    Verifica si una fecha es un día laborable.
    Un día laborable es de lunes a viernes y no es festivo.
    """
    if current_date.weekday() >= 5:  # Es Sábado o Domingo
        return False
    if current_date in HOLIDAYS:  # Es un día festivo
        return False
    return True


def add_work_minutes(start_datetime, minutes_to_add, WORKDAY_MINUTES):
    """
    Calcula la fecha y hora de finalización sumando minutos laborables.
    Salta fines de semana y festivos.
    """
    current_datetime = start_datetime
    remaining_minutes = minutes_to_add

    while remaining_minutes > 0:
        current_date = current_datetime.date()

        if is_workday(current_date):
            end_of_workday = datetime.combine(current_date, datetime.max.time())
            minutes_left_in_day = (
                end_of_workday - current_datetime
            ).total_seconds() / 60
            minutes_in_day = min(minutes_left_in_day, WORKDAY_MINUTES)

            if remaining_minutes <= minutes_in_day:
                current_datetime += timedelta(minutes=remaining_minutes)
                remaining_minutes = 0
            else:
                remaining_minutes -= minutes_in_day
                next_day = current_date + timedelta(days=1)
                current_datetime = datetime.combine(next_day, datetime.min.time())
        else:
            next_day = current_date + timedelta(days=1)
            current_datetime = datetime.combine(next_day, datetime.min.time())

    return current_datetime


def count_workdays(start_datetime, end_datetime):
    """
    Cuenta el número de días laborables entre dos fechas.
    Incluye el día de inicio pero no el de fin, para reflejar duraciones.
    """
    # Si la tarea dura menos de un día, cuenta como 1 día de trabajo si empieza en día laborable
    if start_datetime.date() == end_datetime.date():
        return 1 if is_workday(start_datetime.date()) else 0

    workdays = 0
    current_date = start_datetime.date()
    end_date = end_datetime.date()

    while current_date < end_date:
        if is_workday(current_date):
            workdays += 1
        current_date += timedelta(days=1)

    # Añadir una fracción del último día si la tarea termina a mitad de jornada
    if is_workday(end_date) and end_datetime.time() > datetime.min.time():
        workdays += (
            end_datetime - datetime.combine(end_date, datetime.min.time())
        ).total_seconds() / (24 * 3600)

    return round(workdays, 2) if workdays > 0 else 1
