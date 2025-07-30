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
    if current_date.weekday() >= 5:  # Es Sábado (5) o Domingo (6)
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

    # Asegurarse de que start_datetime sea un día laborable y una hora de trabajo
    # Si la tarea empieza fuera de horas o en día no laborable, avanza al próximo día/hora de trabajo
    while not is_workday(current_datetime.date()) or current_datetime.hour < 0 or current_datetime.hour >= 24: # Asumimos jornada completa por ahora
         current_datetime += timedelta(minutes=1) # Avanzamos minuto a minuto para encontrar el próximo inicio de jornada
         if current_datetime.hour == 0 and current_datetime.minute == 0: # Si pasamos a un nuevo día
             if not is_workday(current_datetime.date()):
                 current_datetime = datetime.combine(current_datetime.date() + timedelta(days=1), datetime.min.time())


    while remaining_minutes > 0:
        current_date = current_datetime.date()

        if is_workday(current_date):
            # Asumimos que la jornada laboral es de 00:00 a 24:00 (WORKDAY_MINUTES es total de minutos laborables al día)
            # Esto simplifica la lógica de jornada continua en el Scheduler.
            # Si tienes horarios de trabajo específicos (ej. 8:00-17:00), necesitaríamos ajustar esto.
            end_of_current_day_work = datetime.combine(current_date, datetime.min.time()) + timedelta(minutes=WORKDAY_MINUTES)

            # Minutos restantes en la jornada actual desde current_datetime hasta end_of_current_day_work
            minutes_left_in_day = (end_of_current_day_work - current_datetime).total_seconds() / 60

            if minutes_left_in_day <= 0: # Ya hemos pasado el tiempo de trabajo de hoy
                next_day = current_date + timedelta(days=1)
                current_datetime = datetime.combine(next_day, datetime.min.time())
                continue # Volver a verificar si el nuevo día es laborable

            if remaining_minutes <= minutes_left_in_day:
                current_datetime += timedelta(minutes=remaining_minutes)
                remaining_minutes = 0
            else:
                remaining_minutes -= minutes_left_in_day
                current_datetime = end_of_current_day_work # Llega al final de la jornada actual
                next_day = current_date + timedelta(days=1)
                current_datetime = datetime.combine(next_day, datetime.min.time())
        else:
            # Si no es día laborable, simplemente salta al siguiente día
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

def get_non_work_plot_bands(start_date, end_date):
    """
    Genera una lista de diccionarios para Highcharts plotBands para marcar
    fines de semana y festivos entre dos fechas.
    """
    plot_bands = []
    current_day = start_date.date()
    one_day = timedelta(days=1)

    while current_day <= end_date.date() + one_day: # Ir un día más allá para asegurar cubrir el último día
        if not is_workday(current_day):
            # Highcharts usa milisegundos desde epoch para las fechas
            from_ms = datetime.combine(current_day, datetime.min.time()).timestamp() * 1000
            to_ms = datetime.combine(current_day + one_day, datetime.min.time()).timestamp() * 1000

            plot_bands.append({
                'from': from_ms,
                'to': to_ms,
                'color': 'rgba(200, 200, 200, 0.2)', # Gris claro transparente
                'label': {
                    'text': 'No laborable',
                    'style': {
                        'color': '#606060'
                    }
                }
            })
        current_day += one_day
    return plot_bands