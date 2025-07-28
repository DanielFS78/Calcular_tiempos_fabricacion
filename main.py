# --- 1. LIBRERÍAS ESTÁNDAR DE PYTHON ---
import configparser
import gc
import logging
import os
import shutil
import sys
from tkinter import messagebox, filedialog

import customtkinter as ctk
import pandas as pd
import plotly.express as px
import requests
from tkcalendar import DateEntry

from calendar_helper import count_workdays, is_workday
from simulation_engine import Scheduler, Task, ResourceManager


def resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller."""
    try:
        # noinspection PyUnresolvedReferences,PyProtectedMember
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def create_gantt_chart(planned_tasks, units):
    """
    Toma una lista de tareas ya planificadas y genera un Gráfico Gantt con Plotly.

    """
    if not planned_tasks:
        return None

    df = pd.DataFrame(planned_tasks)

    # Crear la plantilla del tooltip con HTML [cite: 49]
    hovertemplate = (
            "<b>%{customdata[0]}</b><br>" +
            "Departamento: %{customdata[1]}<br>" +
            "Asignado a: %{customdata[2]} (Tipo %{customdata[3]})<br>" +
            "Inicio: %{x|%d-%m-%Y %H:%M}<br>" +
            "Fin: %{customdata[4]|%d-%m-%Y %H:%M}<br>" +
            "Duración: %{customdata[5]:.2f} min<br>" +
            "<hr>" +
            "<em><span style='color: #00BFFF;'>%{customdata[6]}</span></em>" +
            "<extra></extra>"
    )

    fig = px.timeline(
        df,
        x_start="Inicio",
        x_end="Fin",
        y="Trabajador Asignado",
        color="Departamento",
        # Pasamos los datos adicionales para el tooltip [cite: 35]
        custom_data=[
            'Tarea',
            'Departamento',
            'Trabajador Asignado',
            'Tipo Trabajador',
            'Fin',
            'Duracion (min)',
            'Motivo Inicio'
        ],
        title=f"Plan de Fabricación Detallado para {units} unidades",
    )

    fig.update_traces(hovertemplate=hovertemplate)  # Aplicamos la plantilla
    fig.update_yaxes(autorange="reversed", title="Recursos Asignados")

    return fig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
)
# Ejemplo de uso
logging.info("El programa ha iniciado.")
from database_manager import DatabaseManager

# --- Configuración de la Apariencia ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# =================================================================================
# CLASE PARA LA PANTALLA DE INICIO (Conectada a la API)
# =================================================================================
class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Obtenemos la frase desde la API
        quote, author = self.get_quote_from_api()

        # Crear los widgets para la frase
        welcome_label = ctk.CTkLabel(self, text="Bienvenido a la Calculadora de Tiempos", font=ctk.CTkFont(size=28, weight="bold"))
        welcome_label.grid(row=0, column=0, padx=30, pady=(30, 10))

        quote_frame = ctk.CTkFrame(self, corner_radius=15)
        quote_frame.grid(row=1, column=0, padx=30, pady=30, sticky="nsew")
        quote_frame.grid_columnconfigure(0, weight=1)

        quote_text = ctk.CTkLabel(quote_frame, text=f"« {quote} »", font=ctk.CTkFont(size=20, slant="italic"), wraplength=700)
        quote_text.pack(expand=True, padx=40, pady=(40, 10))

        author_text = ctk.CTkLabel(quote_frame, text=f"— {author}", font=ctk.CTkFont(size=16, weight="bold"))
        author_text.pack(expand=True, anchor="e", padx=40, pady=(0, 40))

    @staticmethod
    def get_quote_from_api():
        """Obtiene una frase del día desde la API web."""
        try:
            logging.info("Intentando obtener frase desde la API: https://frasedeldia.azurewebsites.net/api/phrase")
            response = requests.get("https://frasedeldia.azurewebsites.net/api/phrase", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("phrase", "No se pudo cargar la frase."), data.get("author", "Sistema")
        except requests.exceptions.RequestException as e:
            logging.warning(f"No se pudo contactar la API de frases. Error: {e}")
            return "La única forma de hacer un gran trabajo es amar lo que haces.", "Steve Jobs"

# =================================================================================
# CLASE PARA LA VENTANA EMERGENTE DE SUBFABRICACIONES
# =================================================================================
class SubfabricacionesWindow(ctk.CTkToplevel):
    def __init__(self, parent, existing_subfabricaciones=None):
        super().__init__(parent)
        self.title("Añadir/Editar Subfabricaciones")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()

        self.subfabricaciones = (
            existing_subfabricaciones if existing_subfabricaciones else []
        )

        # --- Widgets ---
        self.label = ctk.CTkLabel(
            self,
            text="Añadir Partes de la Fabricación",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.label.pack(pady=10)

        self.entry_frame = ctk.CTkFrame(self)
        self.entry_frame.pack(pady=10, padx=20, fill="x")

        self.desc_label = ctk.CTkLabel(self.entry_frame, text="Descripción:")
        self.desc_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.desc_entry = ctk.CTkEntry(self.entry_frame, width=250)
        self.desc_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.tiempo_label = ctk.CTkLabel(self.entry_frame, text="Tiempo (min):")
        self.tiempo_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tiempo_entry = ctk.CTkEntry(self.entry_frame)
        self.tiempo_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.worker_label = ctk.CTkLabel(self.entry_frame, text="Trabajador:")
        self.worker_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.worker_menu = ctk.CTkOptionMenu(
            self.entry_frame, values=["Tipo 1", "Tipo 2", "Tipo 3"]
        )
        self.worker_menu.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.add_button = ctk.CTkButton(
            self.entry_frame, text="Añadir Parte", command=self.add_subfabricacion
        )
        self.add_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.list_label = ctk.CTkLabel(self.list_frame, text="Partes Añadidas:")
        self.list_label.pack(pady=5)

        self.sub_textbox = ctk.CTkTextbox(
            self.list_frame, state="disabled", font=("Consolas", 12)
        )
        self.sub_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(pady=10, fill="x")
        self.save_button = ctk.CTkButton(
            self.button_frame, text="Guardar y Cerrar", command=self.save_and_close
        )
        self.save_button.pack(side="right", padx=20)

        self.update_textbox()

    def add_subfabricacion(self):
        desc = self.desc_entry.get()
        tiempo_str = self.tiempo_entry.get()
        worker_str = self.worker_menu.get()

        if not desc or not tiempo_str or not worker_str:
            messagebox.showerror(
                "Error", "Todos los campos son obligatorios.", parent=self
            )
            return

        try:
            tiempo = float(tiempo_str.replace(",", "."))
        except ValueError:
            messagebox.showerror("Error", "El tiempo debe ser un número.", parent=self)
            return

        worker_type = int(worker_str.split(" ")[1])
        new_sub = {
            "descripcion": desc,
            "tiempo": tiempo,
            "tipo_trabajador": worker_type,
        }
        self.subfabricaciones.append(new_sub)

        self.update_textbox()
        self.desc_entry.delete(0, "end")
        self.tiempo_entry.delete(0, "end")
        self.worker_menu.set("Tipo 1")

    def update_textbox(self):
        self.sub_textbox.configure(state="normal")
        self.sub_textbox.delete("1.0", "end")
        total_time = 0
        for i, sub in enumerate(self.subfabricaciones):
            self.sub_textbox.insert(
                "end",
                f"{i+1}. {sub['descripcion']} - {sub['tiempo']} min (Trabajador Tipo {sub['tipo_trabajador']})\n",
            )
            total_time += sub["tiempo"]
        self.sub_textbox.insert(
            "end", f"\n--- TIEMPO TOTAL: {total_time:.2f} minutos ---"
        )
        self.sub_textbox.configure(state="disabled")

    def save_and_close(self):
        self.destroy()


# =================================================================================
# CLASE PARA LA PANTALLA "AÑADIR PRODUCTO"
# =================================================================================
class AddProductFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.subfabricaciones_data = []

        self.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self, text="Añadir Nuevo Producto", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=20)

        ctk.CTkLabel(self, text="Código Producto:").grid(
            row=1, column=0, padx=20, pady=10, sticky="w"
        )
        self.codigo_entry = ctk.CTkEntry(self, placeholder_text="Ej: CPU-01")
        self.codigo_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Descripción:").grid(
            row=2, column=0, padx=20, pady=10, sticky="w"
        )
        self.descripcion_entry = ctk.CTkEntry(
            self, placeholder_text="Ej: Unidad de Control Principal"
        )
        self.descripcion_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Departamento:").grid(
            row=3, column=0, padx=20, pady=10, sticky="w"
        )
        self.departamento_menu = ctk.CTkOptionMenu(
            self, values=["Mecánica", "Electrónica", "Montaje"]
        )
        self.departamento_menu.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Tipo de Trabajador (si no tiene sub-partes):").grid(
            row=4, column=0, padx=20, pady=10, sticky="w"
        )
        self.trabajador_menu = ctk.CTkOptionMenu(
            self, values=["Tipo 1", "Tipo 2", "Tipo 3"]
        )
        self.trabajador_menu.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Dónde se encuentra/ubica:").grid(
            row=5, column=0, padx=20, pady=10, sticky="nw"
        )
        self.donde_textbox = ctk.CTkTextbox(self, height=100)
        self.donde_textbox.grid(row=5, column=1, padx=20, pady=10, sticky="ew")

        self.sub_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sub_frame.grid(
            row=6, column=0, columnspan=2, padx=20, pady=10, sticky="ew"
        )
        self.sub_frame.grid_columnconfigure(1, weight=1)

        self.tiene_sub_var = ctk.IntVar(value=0)
        self.sub_switch = ctk.CTkSwitch(
            self.sub_frame,
            text="¿Tiene subfabricaciones?",
            variable=self.tiene_sub_var,
            command=self.toggle_sub_mode,
        )
        self.sub_switch.grid(row=0, column=0, padx=10)

        self.tiempo_optimo_label = ctk.CTkLabel(
            self.sub_frame, text="Tiempo Óptimo (min):"
        )
        self.tiempo_optimo_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.tiempo_optimo_entry = ctk.CTkEntry(self.sub_frame)
        self.tiempo_optimo_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        self.add_sub_button = ctk.CTkButton(
            self.sub_frame,
            text="Añadir/Editar Subfabricaciones",
            command=self.open_sub_window,
        )
        self.sub_info_label = ctk.CTkLabel(
            self.sub_frame,
            text="No se han añadido subfabricaciones.",
            text_color="gray",
        )
        self.sub_info_label.grid(row=2, column=1, padx=10, sticky="w")

        self.toggle_sub_mode()

        self.save_button = ctk.CTkButton(
            self, text="Guardar Producto", command=self.save_product
        )
        self.save_button.grid(row=7, column=1, padx=20, pady=20, sticky="e")

    # Reemplaza este método en la clase AddProductFrame
    def toggle_sub_mode(self):
        if self.tiene_sub_var.get() == 0:  # Si NO tiene subfabricaciones
            self.tiempo_optimo_label.grid()
            self.tiempo_optimo_entry.grid()
            self.trabajador_menu.configure(state="normal")
            self.add_sub_button.grid_remove()
            self.sub_info_label.grid_remove()
        else:  # Si SÍ tiene subfabricaciones
            self.tiempo_optimo_label.grid_remove()
            self.tiempo_optimo_entry.grid_remove()
            self.trabajador_menu.configure(state="disabled")
            self.add_sub_button.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
            self.sub_info_label.grid()

            # --- LÓGICA AÑADIDA AQUÍ ---
            # Actualizamos el texto de la etiqueta para dar feedback visual
            count = len(self.subfabricaciones_data)
            total_time = sum(s["tiempo"] for s in self.subfabricaciones_data)
            if count > 0:
                self.sub_info_label.configure(
                    text=f"{count} parte(s) añadidas. Tiempo total: {total_time:.2f} min."
                )
            else:
                self.sub_info_label.configure(
                    text="No se han añadido subfabricaciones."
                )

    def open_sub_window(self):
        # Pasamos la lista de datos actual a la ventana emergente
        sub_window = SubfabricacionesWindow(
            self, existing_subfabricaciones=self.subfabricaciones_data
        )

        # Esta línea es la clave: el código se detiene aquí hasta que la ventana emergente se cierre
        self.wait_window(sub_window)

        # Una vez cerrada, recogemos los datos actualizados
        self.subfabricaciones_data = sub_window.subfabricaciones
        self.toggle_sub_mode()  # Actualizamos la info en la pantalla principal

    def save_product(self):
        data = {
            "codigo": self.codigo_entry.get().strip(),
            "descripcion": self.descripcion_entry.get().strip(),
            "departamento": self.departamento_menu.get(),
            "donde": self.donde_textbox.get("1.0", "end-1c").strip(),
            "tiene_subfabricaciones": self.tiene_sub_var.get(),
        }

        logging.info(f"Intentando guardar producto con código: {data['codigo']}")

        if not data["codigo"] or not data["descripcion"]:
            logging.warning(
                f"Validación fallida al guardar producto: código o descripción vacíos."
            )
            messagebox.showerror(
                "Error de Validación", "El código y la descripción son obligatorios."
            )
            return

        if data["tiene_subfabricaciones"] == 0:
            try:
                data["tiempo_optimo"] = float(
                    self.tiempo_optimo_entry.get().replace(",", ".")
                )
                data["tipo_trabajador"] = int(self.trabajador_menu.get().split(" ")[1])
                sub_data = None
            except (ValueError, IndexError):
                logging.warning(
                    f"Validación fallida para producto {data['codigo']}: Tiempo o tipo de trabajador inválido."
                )
                messagebox.showerror(
                    "Error de Validación",
                    "El tiempo óptimo y el tipo de trabajador deben ser válidos.",
                )
                return
        else:
            if not self.subfabricaciones_data:
                logging.warning(
                    f"Validación fallida para producto {data['codigo']}: No se añadieron subfabricaciones."
                )
                messagebox.showerror(
                    "Error de Validación",
                    "Si marca 'Tiene subfabricaciones', debe añadir al menos una parte.",
                )
                return
            data["tiempo_optimo"] = sum(s["tiempo"] for s in self.subfabricaciones_data)
            data["tipo_trabajador"] = min(
                s["tipo_trabajador"] for s in self.subfabricaciones_data
            )
            sub_data = self.subfabricaciones_data

        if self.db_manager.add_product(data, sub_data):
            logging.info(
                f"Producto '{data['codigo']}' guardado con éxito en la base de datos."
            )
            messagebox.showinfo(
                "Éxito", f"Producto '{data['codigo']}' guardado correctamente."
            )
            self.codigo_entry.delete(0, "end")
            self.descripcion_entry.delete(0, "end")
            self.donde_textbox.delete("1.0", "end")
            self.tiempo_optimo_entry.delete(0, "end")
            self.subfabricaciones_data = []
            self.toggle_sub_mode()
        else:
            logging.error(
                f"Fallo al guardar producto en la BD. Código duplicado o error de BD para: {data['codigo']}"
            )
            messagebox.showerror(
                "Error de Base de Datos",
                f"No se pudo guardar el producto. ¿Quizás el código '{data['codigo']}' ya existe?",
            )


# =================================================================================
# CLASE PARA LA PANTALLA "CREAR FABRICACIÓN"
# =================================================================================
class CreateFabricacionFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.contenido_actual = []
        self.selected_product_code = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Crear Nueva Fabricación", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))

        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.top_frame, text="Código Fabricación:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.fab_codigo_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Ej: KIT-01")
        self.fab_codigo_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.top_frame, text="Descripción:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.fab_desc_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Ej: Kit de Montaje Final PC")
        self.fab_desc_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.top_frame, text="─" * 80).grid(row=2, column=0, columnspan=2, pady=5)

        ctk.CTkLabel(self.top_frame, text="Buscar Producto:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.search_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Escriba código o descripción del producto...")
        self.search_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.update_search_results)

        self.search_results_frame = ctk.CTkScrollableFrame(self.top_frame, label_text="Resultados de Búsqueda")
        self.search_results_frame.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.top_frame, text="Cantidad:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.cantidad_entry = ctk.CTkEntry(self.top_frame, placeholder_text="1")
        self.cantidad_entry.grid(row=5, column=1, padx=(10, 150), pady=5, sticky="ew")

        self.add_product_button = ctk.CTkButton(self.top_frame, text="Añadir Producto a la Lista", command=self.add_product_to_list)
        self.add_product_button.grid(row=6, column=1, padx=10, pady=10, sticky="e")

        self.content_list_frame = ctk.CTkFrame(self)
        self.content_list_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

        self.content_textbox = ctk.CTkTextbox(self.content_list_frame, state="disabled", font=("Consolas", 12))
        self.content_textbox.pack(expand=True, fill="both", padx=10, pady=10)

        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        self.clear_button = ctk.CTkButton(self.bottom_frame, text="Limpiar Lista", command=self.clear_list, fg_color="#D35400", hover_color="#E67E22")
        self.clear_button.pack(side="left", padx=10, pady=10)
        self.save_button = ctk.CTkButton(self.bottom_frame, text="Guardar Fabricación", command=self.save_fabricacion)
        self.save_button.pack(side="right", padx=10, pady=10)

        self.update_content_textbox()

    def update_search_results(self, _event=None):
        query = self.search_entry.get()
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()
        self.selected_product_code = None
        if len(query) < 2:
            return
        results = self.db_manager.search_products(query)
        for codigo, descripcion in results:
            text = f"{codigo} - {descripcion}"
            label = ctk.CTkLabel(self.search_results_frame, text=text, cursor="hand2", anchor="w")
            label.pack(fill="x", padx=5)
            label.bind("<Button-1>", lambda e, c=codigo, t=text: self.select_product(c, t))

    def select_product(self, codigo, text):
        self.selected_product_code = codigo
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, text)
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

    def add_product_to_list(self):
        if not self.selected_product_code:
            messagebox.showerror("Error", "Debe seleccionar un producto de la lista de búsqueda.")
            return
        try:
            cantidad = int(self.cantidad_entry.get() or 1)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número entero positivo.")
            return

        for item in self.contenido_actual:
            if item["producto_codigo"] == self.selected_product_code:
                item["cantidad"] += cantidad
                break
        else:
            self.contenido_actual.append({
                "producto_codigo": self.selected_product_code,
                "producto_texto": self.search_entry.get(),
                "cantidad": cantidad,
            })

        self.update_content_textbox()
        self.search_entry.delete(0, "end")
        self.cantidad_entry.delete(0, "end")
        self.selected_product_code = None

    def update_content_textbox(self):
        self.content_textbox.configure(state="normal")
        self.content_textbox.delete("1.0", "end")
        if not self.contenido_actual:
            self.content_textbox.insert("1.0", "Añada productos para verlos aquí...")
        else:
            for item in self.contenido_actual:
                line = f"CANT: {item['cantidad']:<5} | {item['producto_texto']}\n"
                self.content_textbox.insert("end", line)
        self.content_textbox.configure(state="disabled")

    def clear_list(self):
        if messagebox.askyesno("Confirmar", "¿Está seguro de que desea limpiar la lista de productos?"):
            self.contenido_actual.clear()
            self.update_content_textbox()

    def save_fabricacion(self):
        fab_codigo = self.fab_codigo_entry.get().strip()
        fab_desc = self.fab_desc_entry.get().strip()
        logging.info(f"Intentando guardar fabricación con código: {fab_codigo}")

        if not fab_codigo or not fab_desc:
            logging.warning(f"Validación fallida al guardar fabricación: código o descripción vacíos.")
            messagebox.showerror("Error", "El código y la descripción de la fabricación son obligatorios.")
            return

        if not self.contenido_actual:
            logging.warning(f"Validación fallida para fabricación {fab_codigo}: No se añadieron productos.")
            messagebox.showerror("Error", "La fabricación debe contener al menos un producto.")
            return

        if self.db_manager.add_fabricacion(fab_codigo, fab_desc, self.contenido_actual):
            logging.info(f"Fabricación '{fab_codigo}' guardada con éxito en la base de datos.")
            messagebox.showinfo("Éxito", f"Fabricación '{fab_codigo}' guardada correctamente.")
            self.clear_form()
        else:
            logging.error(f"Fallo al guardar fabricación en la BD. Código duplicado o error de BD para: {fab_codigo}")
            messagebox.showerror("Error de Base de Datos", f"No se pudo guardar la fabricación. ¿Quizás el código '{fab_codigo}' ya existe?")

    def clear_form(self):
        self.fab_codigo_entry.delete(0, "end")
        self.fab_desc_entry.delete(0, "end")
        self.search_entry.delete(0, "end")
        self.cantidad_entry.delete(0, "end")
        self.contenido_actual.clear()
        self.update_content_textbox()

# =================================================================================
# CLASE PARA LA PANTALLA "EDITAR / VISUALIZAR" (TOTALMENTE REESTRUCTURADA)
# =================================================================================
class EditFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.subfabricaciones_data = []
        self.contenido_actual = []
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        search_frame = ctk.CTkFrame(self); search_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        search_frame.grid_columnconfigure(1, weight=1)
        self.search_type_var = ctk.StringVar(value="Productos")
        ctk.CTkSegmentedButton(search_frame, values=["Productos", "Fabricaciones"], variable=self.search_type_var, command=self.clear_search).grid(row=0, column=0, padx=10, pady=10)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Buscar por código o descripción...")
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.update_search_results)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=2, uniform="group1"); self.content_frame.grid_columnconfigure(1, weight=3, uniform="group1"); self.content_frame.grid_rowconfigure(0, weight=1)
        self.results_frame = ctk.CTkScrollableFrame(self.content_frame, label_text="Resultados")
        self.results_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.edit_area_frame = ctk.CTkFrame(self.content_frame)

    def clear_search(self, _value=None):
        self.search_entry.delete(0, "end")
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.edit_area_frame.grid_forget()

    def update_search_results(self, _event=None):
        query = self.search_entry.get()
        search_type = self.search_type_var.get()
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.edit_area_frame.grid_forget()
        if len(query) < 2: return
        results = self.db_manager.search_products(query) if search_type == "Productos" else self.db_manager.search_fabricaciones(query)
        for codigo, descripcion in results:
            text = f"{codigo} | {descripcion}"
            label = ctk.CTkLabel(self.results_frame, text=text, cursor="hand2", anchor="w")
            label.pack(fill="x", padx=5, pady=2)
            label.bind("<Button-1>", lambda e, c=codigo: self.load_item_for_edit(c))

    def load_item_for_edit(self, codigo):
        search_type = self.search_type_var.get()
        for widget in self.edit_area_frame.winfo_children():
            widget.destroy()
        if search_type == "Productos":
            self.create_product_edit_form(codigo)
        else:
            self.create_fabricacion_edit_form(codigo)
        self.edit_area_frame.grid(row=0, column=1, padx=(20, 0), pady=0, sticky="nsew")

    def create_product_edit_form(self, codigo):
        product_data, sub_data_raw = self.db_manager.get_product_details(codigo)
        if not product_data: return
        data = {"codigo": product_data[0], "descripcion": product_data[1], "departamento": product_data[2], "tipo_trabajador": product_data[3], "donde": product_data[4], "tiene_subfabricaciones": product_data[5], "tiempo_optimo": product_data[6]}
        self.subfabricaciones_data = [{"descripcion": s[2], "tiempo": s[3], "tipo_trabajador": s[4]} for s in sub_data_raw]
        form = self.edit_area_frame; form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Editando Producto", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        ctk.CTkLabel(form, text="Código:").grid(row=1, column=0, padx=10, pady=5, sticky="w"); self.p_codigo_entry = ctk.CTkEntry(form)
        self.p_codigo_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew"); self.p_codigo_entry.insert(0, data["codigo"])
        ctk.CTkLabel(form, text="Descripción:").grid(row=2, column=0, padx=10, pady=5, sticky="w"); self.p_desc_entry = ctk.CTkEntry(form)
        self.p_desc_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew"); self.p_desc_entry.insert(0, data["descripcion"])
        ctk.CTkLabel(form, text="Departamento:").grid(row=3, column=0, padx=10, pady=5, sticky="w"); self.p_departamento_menu = ctk.CTkOptionMenu(form, values=["Mecánica", "Electrónica", "Montaje"])
        self.p_departamento_menu.set(data["departamento"]); self.p_departamento_menu.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(form, text="Dónde se ubica:").grid(row=5, column=0, padx=10, pady=5, sticky="nw"); self.p_donde_textbox = ctk.CTkTextbox(form, height=80)
        self.p_donde_textbox.grid(row=5, column=1, padx=10, pady=5, sticky="ew"); self.p_donde_textbox.insert("1.0", data["donde"] or "")
        self.p_sub_frame = ctk.CTkFrame(form, fg_color="transparent"); self.p_sub_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.p_sub_frame.grid_columnconfigure(1, weight=1); self.p_tiene_sub_var = ctk.IntVar(value=data["tiene_subfabricaciones"])
        self.p_sub_switch = ctk.CTkSwitch(self.p_sub_frame, text="¿Tiene subfabricaciones?", variable=self.p_tiene_sub_var, command=self._p_toggle_sub_mode)
        self.p_sub_switch.grid(row=0, column=0, padx=10); self.p_tiempo_optimo_label = ctk.CTkLabel(self.p_sub_frame, text="Tiempo Óptimo (min):")
        self.p_tiempo_optimo_entry = ctk.CTkEntry(self.p_sub_frame); self.p_tiempo_optimo_entry.insert(0, str(data["tiempo_optimo"]))
        self.p_trabajador_menu = ctk.CTkOptionMenu(self.p_sub_frame, values=["Tipo 1", "Tipo 2", "Tipo 3"]); self.p_trabajador_menu.set(f"Tipo {data['tipo_trabajador']}")
        self.p_add_sub_button = ctk.CTkButton(self.p_sub_frame, text="Añadir/Editar Subfabricaciones", command=self._p_open_sub_window)
        self.p_sub_info_label = ctk.CTkLabel(self.p_sub_frame, text="", text_color="gray"); self._p_toggle_sub_mode()
        btn_frame = ctk.CTkFrame(form, fg_color="transparent"); btn_frame.grid(row=10, column=0, columnspan=2, pady=20, sticky="e")
        ctk.CTkButton(btn_frame, text="Guardar Cambios", command=lambda: self.save_product_changes(codigo)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Eliminar", fg_color="#E74C3C", hover_color="#C0392B", command=lambda: self.delete_product(codigo)).pack(side="left", padx=5)

    def _p_toggle_sub_mode(self):
        if self.p_tiene_sub_var.get() == 0:
            self.p_tiempo_optimo_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
            self.p_tiempo_optimo_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
            self.p_trabajador_menu.configure(state="normal"); self.p_add_sub_button.grid_remove(); self.p_sub_info_label.grid_remove()
        else:
            self.p_tiempo_optimo_label.grid_remove(); self.p_tiempo_optimo_entry.grid_remove()
            self.p_trabajador_menu.configure(state="disabled"); self.p_add_sub_button.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
            self.p_sub_info_label.grid(row=2, column=1, padx=10, sticky="w")
            count = len(self.subfabricaciones_data); total_time = sum(s["tiempo"] for s in self.subfabricaciones_data)
            self.p_sub_info_label.configure(text=f"{count} parte(s). Tiempo total: {total_time:.2f} min.")

    def _p_open_sub_window(self):
        sub_window = SubfabricacionesWindow(self, existing_subfabricaciones=self.subfabricaciones_data)
        self.wait_window(sub_window); self.subfabricaciones_data = sub_window.subfabricaciones; self._p_toggle_sub_mode()

    def save_product_changes(self, original_codigo):
        new_data = {"codigo": self.p_codigo_entry.get().strip(), "descripcion": self.p_desc_entry.get().strip(), "departamento": self.p_departamento_menu.get(),
                    "donde": self.p_donde_textbox.get("1.0", "end-1c").strip(), "tiene_subfabricaciones": self.p_tiene_sub_var.get()}
        if not new_data["codigo"] or not new_data["descripcion"]: messagebox.showerror("Error de Validación", "El código y la descripción son obligatorios."); return
        if new_data["tiene_subfabricaciones"] == 0:
            try:
                new_data["tiempo_optimo"] = float(self.p_tiempo_optimo_entry.get().replace(",", ".")); new_data["tipo_trabajador"] = int(self.p_trabajador_menu.get().split(" ")[1])
            except (ValueError, IndexError): messagebox.showerror("Error de Validación", "El tiempo óptimo debe ser un número válido."); return
        else:
            if not self.subfabricaciones_data: messagebox.showerror("Error de Validación", "Si marca 'Tiene subfabricaciones', debe añadir al menos una parte."); return
            new_data["tiempo_optimo"] = sum(s["tiempo"] for s in self.subfabricaciones_data); new_data["tipo_trabajador"] = min(s["tipo_trabajador"] for s in self.subfabricaciones_data)
        if self.db_manager.update_product(original_codigo, new_data, self.subfabricaciones_data):
            messagebox.showinfo("Éxito", "Producto actualizado correctamente."); self.clear_search()
        else: messagebox.showerror("Error", "No se pudo actualizar el producto.")

    def delete_product(self, codigo):
        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar el producto '{codigo}'?\nEsta acción no se puede deshacer.", icon="warning"):
            if self.db_manager.delete_product(codigo): messagebox.showinfo("Éxito", "Producto eliminado correctamente."); self.clear_search()
            else: messagebox.showerror("Error", "No se pudo eliminar el producto.")

    def create_fabricacion_edit_form(self, codigo):
        fab_data, contenido_raw = self.db_manager.get_fabricacion_details(codigo)
        if not fab_data: return
        data = {"codigo": fab_data[0], "descripcion": fab_data[1]}
        self.contenido_actual = [{"producto_codigo": c[0], "producto_texto": f"{c[0]} - {c[1]}", "cantidad": c[2]} for c in contenido_raw]
        form = self.edit_area_frame; form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Editando Fabricación", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        ctk.CTkLabel(form, text="Código:").grid(row=1, column=0, padx=10, pady=5, sticky="w"); self.f_codigo_entry = ctk.CTkEntry(form)
        self.f_codigo_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew"); self.f_codigo_entry.insert(0, data["codigo"])
        ctk.CTkLabel(form, text="Descripción:").grid(row=2, column=0, padx=10, pady=5, sticky="w"); self.f_desc_entry = ctk.CTkEntry(form)
        self.f_desc_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew"); self.f_desc_entry.insert(0, data["descripcion"])
        ctk.CTkLabel(form, text="Contenido:").grid(row=3, column=0, padx=10, pady=5, sticky="nw"); self.f_content_textbox = ctk.CTkTextbox(form, height=200)
        self.f_content_textbox.grid(row=3, column=1, padx=10, pady=5, sticky="ew"); self.update_fab_content_textbox()
        btn_frame = ctk.CTkFrame(form, fg_color="transparent"); btn_frame.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")
        ctk.CTkButton(btn_frame, text="Guardar Cambios", command=lambda: self.save_fabricacion_changes(codigo)).pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="Eliminar", fg_color="#E74C3C", hover_color="#C0392B", command=lambda: self.delete_fabricacion(codigo)).pack(side="right", padx=10)

    def update_fab_content_textbox(self):
        self.f_content_textbox.configure(state="normal"); self.f_content_textbox.delete("1.0", "end")
        for item in self.contenido_actual: self.f_content_textbox.insert("end", f"CANT: {item['cantidad']:<5} | {item['producto_texto']}\n")
        self.f_content_textbox.configure(state="disabled")

    def save_fabricacion_changes(self, original_codigo):
        new_data = {"codigo": self.f_codigo_entry.get().strip(), "descripcion": self.f_desc_entry.get().strip()}
        if self.db_manager.update_fabricacion(original_codigo, new_data, self.contenido_actual):
            messagebox.showinfo("Éxito", "Fabricación actualizada correctamente."); self.clear_search()
        else: messagebox.showerror("Error", "No se pudo actualizar la fabricación.")

    def delete_fabricacion(self, codigo):
        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar la fabricación '{codigo}'?", icon="warning"):
            if self.db_manager.delete_fabricacion(codigo): messagebox.showinfo("Éxito", "Fabricación eliminada."); self.clear_search()
            else: messagebox.showerror("Error", "No se pudo eliminar la fabricación.")

# =================================================================================
# CLASE PARA LA VENTANA EMERGENTE DE PLANIFICACIÓN (VERSIÓN FINAL CON CALENDARIO)
# =================================================================================
class DepartmentPlanningWindow(ctk.CTkToplevel):
    def __init__(self, parent, department_name, tasks, units):
        super().__init__(parent)
        self.title(f"Planificación de {department_name}")
        self.geometry("700x600")
        self.transient(parent)

        self.department_name = department_name
        self.tasks = tasks
        self.units = units
        self.plan = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Ajustar para la nueva fila

        # --- Marco de Configuración de Recursos y Fecha de Inicio ---
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        config_frame.grid_columnconfigure([0, 1, 2], weight=1)

        self.worker_entries = {}
        for i in range(1, 4):
            worker_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
            worker_frame.grid(row=0, column=i - 1, padx=5)
            ctk.CTkLabel(worker_frame, text=f"Trabajadores T{i}:").pack(
                side="left", padx=(0, 5)
            )
            entry = ctk.CTkEntry(worker_frame, placeholder_text="0", width=60)
            entry.pack(side="left")
            entry.insert(0, "0")
            self.worker_entries[i] = entry

        # --- NUEVO: Selector de Fecha de Inicio para esta fase ---
        date_frame = ctk.CTkFrame(self)
        date_frame.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkLabel(date_frame, text="Fecha de Inicio de esta Fase:").pack(
            side="left", padx=(0, 10)
        )
        self.start_date_entry = DateEntry(
            date_frame, date_pattern="dd/mm/yyyy", locale="es_ES"
        )
        self.start_date_entry.pack(side="left")

        # --- Marco para Ordenar Tareas ---
        self.task_order_frame = ctk.CTkScrollableFrame(
            self, label_text="Orden de Ejecución de Tareas"
        )
        self.task_order_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.task_widgets = []
        self.display_tasks()

        # --- Botones de Acción ---
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=10, sticky="e")
        ctk.CTkButton(button_frame, text="Cancelar", command=self.destroy).pack(
            side="left", padx=10
        )
        ctk.CTkButton(button_frame, text="Guardar Plan", command=self.save_plan).pack(
            side="left", padx=10
        )

    def display_tasks(self):
        for widget_info in self.task_widgets:
            widget_info["frame"].destroy()
        self.task_widgets.clear()

        for i, task in enumerate(self.tasks):
            task_frame = ctk.CTkFrame(self.task_order_frame)
            task_frame.pack(fill="x", pady=2, padx=5)
            task_frame.grid_columnconfigure(1, weight=1)
            task_duration = task["tiempo_optimo"] * 1.20 * self.units
            worker_type_req = task.get("tipo_trabajador", "N/A")
            label_text = (
                f"T{worker_type_req} | {task['codigo']} ({task_duration:.2f} min tot)"
            )
            ctk.CTkLabel(task_frame, text=label_text, anchor="w").grid(
                row=0, column=1, padx=5, sticky="ew"
            )
            up_button = ctk.CTkButton(
                task_frame,
                text="▲",
                width=30,
                command=lambda index=i: self.move_task(index, -1),
            )
            up_button.grid(row=0, column=0, padx=5)
            if i == 0:
                up_button.configure(state="disabled")
            down_button = ctk.CTkButton(
                task_frame,
                text="▼",
                width=30,
                command=lambda index=i: self.move_task(index, 1),
            )
            down_button.grid(row=0, column=2, padx=5)
            if i == len(self.tasks) - 1:
                down_button.configure(state="disabled")
            self.task_widgets.append({"frame": task_frame, "task_data": task})

    def move_task(self, index, direction):
        new_index = index + direction
        self.tasks[index], self.tasks[new_index] = (
            self.tasks[new_index],
            self.tasks[index],
        )
        self.display_tasks()

    def save_plan(self):
        try:
            workers_by_type = {
                1: int(self.worker_entries[1].get()),
                2: int(self.worker_entries[2].get()),
                3: int(self.worker_entries[3].get()),
            }
            if any(w < 0 for w in workers_by_type.values()):
                raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror(
                "Error",
                "El número de trabajadores debe ser un entero positivo (o 0).",
                parent=self,
            )
            return

        start_date = self.start_date_entry.get_date()
        if not is_workday(start_date):
            messagebox.showwarning(
                "Fecha Inválida",
                "La fecha de inicio seleccionada es un fin de semana o festivo.",
                parent=self,
            )
            return

        self.plan = {
            "workers": workers_by_type,
            "task_order": self.tasks,
            "start_date": start_date,  # <-- Guardamos la fecha de inicio
        }
        self.destroy()


class CalculateTimesFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.WORKDAY_MINUTES = 465
        self.calculation_data = None
        self.department_plans = {}
        self.final_planned_tasks = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Marco de Selección de Fabricación ---
        self.selection_frame = ctk.CTkFrame(self)
        self.selection_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.selection_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.selection_frame, text="Fabricación:").grid(row=0, column=0, padx=10, pady=10)
        self.fab_search_entry = ctk.CTkEntry(self.selection_frame, placeholder_text="Buscar fabricación a calcular...")
        self.fab_search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.fab_search_entry.bind("<KeyRelease>", self.update_fab_search_results)
        self.selected_fab_code = None
        self.fab_search_results_frame = ctk.CTkFrame(self.selection_frame)
        self.fab_search_results_frame.grid(row=1, column=1, padx=10, sticky="ew")
        ctk.CTkLabel(self.selection_frame, text="Unidades a Fabricar:").grid(row=2, column=0, padx=10, pady=10)
        self.units_entry = ctk.CTkEntry(self.selection_frame, placeholder_text="1")
        self.units_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.units_entry.insert(0, "1")

        # --- Marco de Planificación (botones lanzadores) ---
        self.planning_frame = ctk.CTkFrame(self)
        self.planning_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.planning_frame.grid_columnconfigure([0, 1, 2], weight=1)
        self.planning_buttons = {}
        departments = ["Electrónica", "Mecánica", "Montaje"]
        for i, dept in enumerate(departments):
            btn = ctk.CTkButton(self.planning_frame, text=f"Planificar {dept}",
                                command=lambda d=dept: self.open_department_planner(d))
            btn.grid(row=0, column=i, padx=10, pady=10, sticky="ew")
            self.planning_buttons[dept] = btn

        # --- Marco de Configuración de Transferencia de Recursos ---
        self.transfer_frame = ctk.CTkFrame(self)
        self.transfer_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.transfer_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.transfer_frame, text="Reasignación de Recursos (Opcional)",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 0))
        self.transfer_enabled_var = ctk.IntVar(value=0)
        self.transfer_checkbox = ctk.CTkCheckBox(self.transfer_frame,
                                                 text="Al finalizar 'Mecánica', transferir trabajadores a 'Montaje'",
                                                 variable=self.transfer_enabled_var,
                                                 command=self.toggle_transfer_entries)
        self.transfer_checkbox.grid(row=1, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="w")
        self.transfer_entries = {}
        for i in range(1, 4):
            frame = ctk.CTkFrame(self.transfer_frame)
            frame.grid(row=2, column=i - 1, padx=5, pady=5, sticky="ew")
            ctk.CTkLabel(frame, text=f"T{i}:").pack(side="left", padx=(10, 2))
            entry = ctk.CTkEntry(frame, placeholder_text="0", width=80)
            entry.pack(side="left", padx=(2, 10), expand=True, fill="x")
            self.transfer_entries[i] = entry
        self.toggle_transfer_entries()

        # --- Marco de Resultados y Acciones Finales ---
        self.results_frame = ctk.CTkFrame(self)
        self.results_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.results_textbox = ctk.CTkTextbox(self.results_frame, state="disabled", font=("Consolas", 14))
        self.results_textbox.pack(expand=True, fill="both", padx=10, pady=10)
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=4, column=0, padx=20, pady=10, sticky="e")
        self.gantt_button = ctk.CTkButton(self.action_frame, text="Generar Plan Completo",
                                          command=self.generate_full_plan)
        self.gantt_button.pack(side="left", padx=10)
        self.export_button = ctk.CTkButton(self.action_frame, text="Exportar a Excel", command=self.export_to_excel,
                                           state="disabled")
        self.export_button.pack(side="left", padx=10)

    def toggle_transfer_entries(self):
        state = "normal" if self.transfer_enabled_var.get() == 1 else "disabled"
        for entry in self.transfer_entries.values():
            entry.configure(state=state)
            if state == "disabled":
                entry.delete(0, "end")

    def update_fab_search_results(self, _event=None):
        query = self.fab_search_entry.get()
        for widget in self.fab_search_results_frame.winfo_children():
            widget.destroy()
        if len(query) < 1: return
        results = self.db_manager.search_fabricaciones(query)
        for codigo, descripcion in results:
            text = f"{codigo} - {descripcion}"
            label = ctk.CTkLabel(self.fab_search_results_frame, text=text, cursor="hand2", anchor="w")
            label.pack(fill="x", padx=5)
            label.bind("<Button-1>", lambda e, c=codigo, t=text: self.select_fabricacion(c, t))

    def select_fabricacion(self, codigo, texto):
        self.selected_fab_code = codigo
        self.fab_search_entry.delete(0, "end")
        self.fab_search_entry.insert(0, texto)
        for widget in self.fab_search_results_frame.winfo_children():
            widget.destroy()
        self.results_textbox.configure(state="normal")
        self.results_textbox.delete("1.0", "end")
        self.results_textbox.configure(state="disabled")
        self.calculation_data = None
        self.department_plans = {}
        self.final_planned_tasks = None
        self.export_button.configure(state="disabled")
        for btn in self.planning_buttons.values():
            btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

    def _validate_and_load_data(self):
        if not self.selected_fab_code:
            messagebox.showerror("Error", "Primero debe seleccionar una fabricación.")
            return None, None
        try:
            units = int(self.units_entry.get())
            if units <= 0: raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("Error", "El número de unidades debe ser un entero positivo.")
            return None, None
        self.calculation_data = self.db_manager.get_data_for_calculation(self.selected_fab_code)
        if not self.calculation_data:
            messagebox.showerror("Error", "No se pudieron cargar los datos para esta fabricación.")
            return None, None
        return units, self.calculation_data

    def open_department_planner(self, department_name):
        units, calc_data = self._validate_and_load_data()
        if not units: return
        tasks_for_dept = [task for task in calc_data if task["departamento"] == department_name]
        if not tasks_for_dept:
            messagebox.showinfo("Información", f"No hay tareas de '{department_name}' en esta fabricación.")
            return
        planner_window = DepartmentPlanningWindow(self, department_name, tasks_for_dept, units)
        self.wait_window(planner_window)
        if planner_window.plan:
            self.department_plans[department_name] = planner_window.plan
            logging.info(f"Plan guardado para el departamento: {department_name}")
            self.planning_buttons[department_name].configure(fg_color="green")

    def generate_full_plan(self):
        self.final_planned_tasks = None
        gc.collect()

        logging.info("Botón 'Generar Plan Completo' pulsado.")
        units, calc_data = self._validate_and_load_data()
        if not units: return

        required_departments = {task['departamento'] for task in calc_data}
        if not all(dept in self.department_plans for dept in required_departments):
            messagebox.showwarning("Aviso",
                                   "Debe planificar todos los departamentos que tienen tareas en esta fabricación antes de generar el plan.")
            return

        transfer_requests = {}
        if self.transfer_enabled_var.get() == 1:
            try:
                for worker_type, entry in self.transfer_entries.items():
                    count = int(entry.get() or 0)
                    if count < 0: raise ValueError
                    if count > 0: transfer_requests[worker_type] = count
            except (ValueError, TypeError):
                messagebox.showerror("Error de Configuración",
                                     "La cantidad de trabajadores a transferir debe ser un número entero positivo (o 0).")
                return

        all_tasks_for_scheduler = []
        task_id_counter, last_task_in_dept_phase = 0, {}
        department_order = ["Electrónica", "Mecánica", "Montaje"]

        for dept_name in department_order:
            if dept_name not in self.department_plans: continue
            tasks_in_this_dept = self.department_plans[dept_name].get("task_order", [])
            last_task_id_in_sequence = None
            for task_data in tasks_in_this_dept:
                dependencies = []
                if dept_name == 'Montaje':
                    if 'Mecánica' in last_task_in_dept_phase: dependencies.append(last_task_in_dept_phase['Mecánica'])
                    if 'Electrónica' in last_task_in_dept_phase: dependencies.append(
                        last_task_in_dept_phase['Electrónica'])
                elif dept_name == 'Mecánica':
                    if 'Electrónica' in last_task_in_dept_phase: dependencies.append(
                        last_task_in_dept_phase['Electrónica'])
                if last_task_id_in_sequence: dependencies.append(last_task_id_in_sequence)

                if task_data["tiene_subfabricaciones"] and task_data["sub_partes"]:
                    first_sub = True
                    for sub_task_data in task_data["sub_partes"]:
                        task_id = f"T-{task_id_counter}"
                        current_deps = list(dependencies) if first_sub else [last_task_id_in_sequence]
                        new_task = Task(task_id, f"({task_data['codigo']}) {sub_task_data['descripcion']}",
                                        sub_task_data["tiempo"] * 1.20 * units, dept_name,
                                        sub_task_data["tipo_trabajador"], current_deps)
                        all_tasks_for_scheduler.append(new_task)
                        first_sub = False;
                        task_id_counter += 1;
                        last_task_id_in_sequence = new_task.id
                else:
                    task_id = f"T-{task_id_counter}"
                    new_task = Task(task_id, f"({dept_name[0]}) {task_data['codigo']}",
                                    task_data["tiempo_optimo"] * 1.20 * units, dept_name, task_data["tipo_trabajador"],
                                    list(dependencies))
                    all_tasks_for_scheduler.append(new_task)
                    last_task_id_in_sequence = new_task.id;
                    task_id_counter += 1
            if last_task_id_in_sequence: last_task_in_dept_phase[dept_name] = last_task_id_in_sequence

        try:
            global_start_date = min(
                plan['start_date'] for plan in self.department_plans.values() if 'start_date' in plan)
        except ValueError:
            messagebox.showerror("Error", "No se ha definido una fecha de inicio para las fases planificadas.");
            return

        resource_manager = ResourceManager(self.department_plans)
        if transfer_requests:
            for worker_type, count in transfer_requests.items():
                resource_manager.transfer_workers('Mecánica', 'Montaje', worker_type, count)

        # --- LÍNEA CORREGIDA AQUÍ ---
        scheduler = Scheduler(all_tasks_for_scheduler, resource_manager, global_start_date, self.WORKDAY_MINUTES)

        self.final_planned_tasks = scheduler.run_simulation()

        if not self.final_planned_tasks:
            messagebox.showerror("Error de Simulación",
                                 "La simulación no produjo ningún resultado. Revise la configuración.");
            return

        summary_lines = [f"RESUMEN DE PLANIFICACIÓN AVANZADA PARA {units} UNIDADES", "=" * 60]
        project_start_time = min(t["Inicio"] for t in self.final_planned_tasks);
        project_end_time = max(t["Fin"] for t in self.final_planned_tasks)
        total_workdays = count_workdays(project_start_time, project_end_time)
        summary_lines.insert(2, f"\nDuración Total Estimada: {total_workdays:.2f} días laborables")
        summary_lines.insert(2, f"Fecha de Fin del Proyecto:   {project_end_time.strftime('%d-%m-%Y %H:%M')}")
        summary_lines.insert(2, f"Fecha de Inicio del Proyecto: {project_start_time.strftime('%d-%m-%Y %H:%M')}")

        self.results_textbox.configure(state="normal");
        self.results_textbox.delete("1.0", "end")
        self.results_textbox.insert("1.0", "\n".join(summary_lines));
        self.results_textbox.configure(state="disabled")
        self.export_button.configure(state="normal")

        gantt_fig = create_gantt_chart(self.final_planned_tasks, units)

        if gantt_fig:
            filepath = filedialog.asksaveasfilename(title="Guardar Diagrama de Gantt como...", defaultextension=".html",
                                                    filetypes=[("HTML files", "*.html")])
            if filepath:
                gantt_fig.write_html(filepath)
                messagebox.showinfo("Plan Generado",
                                    f"El plan se ha calculado y el diagrama se ha guardado en:\n{filepath}")

        del gantt_fig, all_tasks_for_scheduler, resource_manager, scheduler
        gc.collect()

    def export_to_excel(self):
        if self.final_planned_tasks is None:
            messagebox.showerror("Error", "Primero debe generar un plan completo.");
            return
        filepath = filedialog.asksaveasfilename(title="Exportar Plan a Excel", defaultextension=".xlsx",
                                                filetypes=[("Excel files", "*.xlsx")])
        if not filepath: return
        try:
            df = pd.DataFrame(self.final_planned_tasks)
            summary_df = df.groupby("Departamento")["Duracion (min)"].sum().reset_index()
            summary_df["Duracion (horas)"] = round(summary_df["Duracion (min)"] / 60, 2)
            summary_df["Duracion (jornadas)"] = round(summary_df["Duracion (min)"] / self.WORKDAY_MINUTES, 2)
            with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
                df_export = df.copy()
                df_export["Inicio"] = pd.to_datetime(df_export["Inicio"]).dt.strftime("%d-%m-%Y %H:%M")
                df_export["Fin"] = pd.to_datetime(df_export["Fin"]).dt.strftime("%d-%m-%Y %H:%M")
                df_export.to_excel(writer, sheet_name="Plan Detallado", index=False)
                summary_df.to_excel(writer, sheet_name="Resumen por Departamento", index=False)
            messagebox.showinfo("Éxito", f"El plan detallado ha sido exportado a:\n{filepath}")
        except Exception as e:
            logging.error(f"Error al exportar a Excel: {e}")
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo Excel:\n{e}")
# =================================================================================
# CLASE PARA LA PANTALLA "¿CÓMO FUNCIONA?"
# =================================================================================
class HelpFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(self, corner_radius=10, wrap="word")
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        help_text = """
GUÍA DE USO DE LA APLICACIÓN

Añadir Productos:
- Usa esta sección para dar de alta cada componente o producto individual.
- Rellena todos los campos. Si un producto no tiene sub-partes, introduce su tiempo de fabricación en 'Tiempo Óptimo'.
- Si un producto se compone de varios pasos, activa '¿Tiene subfabricaciones?' y añádelos uno a uno en la ventana emergente.

Crear Fabricación:
- Aquí se define un "kit" o ensamblaje final, que agrupa varios productos.
- Dale un código y descripción al kit.
- Busca los productos que has añadido previamente y especifica la cantidad necesaria de cada uno para el kit.

Editar / Visualizar:
- Permite buscar y modificar cualquier producto o fabricación que ya exista en la base de datos.
- También puedes eliminar elementos desde aquí. Ten cuidado, esta acción es permanente.

Calcular Tiempos:
- La herramienta principal. Selecciona una fabricación, indica cuántas unidades finales quieres producir y elige un método de cálculo.
- Por Tiempo: Introduce los días que tienes y te dirá cuántos trabajadores de cada tipo necesitas.
- Por Trabajadores: Introduce los operarios que tienes y te dirá cuántos días tardarás.
- Exportar a Excel: Genera un informe detallado con los resultados del cálculo.

Configuración:
- Permite exportar (hacer una copia de seguridad) e importar (restaurar) la base de datos completa.
- También puedes indicar una nueva ubicación para el archivo de la base de datos. Se requerirá reiniciar la app.
"""
        self.textbox.insert("1.0", help_text)
        self.textbox.configure(state="disabled")


# =================================================================================
# CLASE PARA LA PANTALLA DE CONFIGURACIÓN
# =================================================================================
class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.app_instance = app_instance
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Configuración de la Aplicación", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0,
                                                                                                                 column=0,
                                                                                                                 padx=20,
                                                                                                                 pady=(
                                                                                                                     20,
                                                                                                                     10))

        db_frame = ctk.CTkFrame(self)
        db_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        db_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(db_frame, text="Gestión de la Base de Datos", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0,
                                                                                                                  column=0,
                                                                                                                  padx=10,
                                                                                                                  pady=(
                                                                                                                      10,
                                                                                                                      5),
                                                                                                                  sticky="w")

        self.db_path_label = ctk.CTkLabel(db_frame, text=f"Ubicación actual: {self.app_instance.db_path}",
                                          wraplength=500, justify="left")
        self.db_path_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.change_path_button = ctk.CTkButton(db_frame, text="Seleccionar o Cambiar Archivo de Base de Datos",
                                                command=self.change_db_path)
        self.change_path_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        backup_frame = ctk.CTkFrame(self)
        backup_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        backup_frame.grid_columnconfigure(0, weight=1)
        backup_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(backup_frame, text="Copias de Seguridad (Backup)", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        self.export_button = ctk.CTkButton(backup_frame, text="Exportar Base de Datos Actual", command=self.export_db)
        self.export_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.import_button = ctk.CTkButton(backup_frame, text="Importar Base de Datos desde un Backup",
                                           command=self.import_db)
        self.import_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    def export_db(self):
        dest_path = filedialog.asksaveasfilename(title="Guardar copia de seguridad como...", defaultextension=".db",
                                                 filetypes=[("Database files", "*.db"), ("All files", "*.*")])
        if dest_path:
            try:
                shutil.copy(self.app_instance.db_path, dest_path)
                messagebox.showinfo("Éxito", f"Copia de seguridad guardada en:\n{dest_path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar la copia de seguridad:\n{e}")

    def import_db(self):
        if not messagebox.askyesno("Confirmar Importación",
                                   "ADVERTENCIA:\nEsto reemplazará tu base de datos actual con el archivo que selecciones.\n¿Deseas continuar?"):
            return
        source_path = filedialog.askopenfilename(title="Seleccionar base de datos para importar",
                                                 filetypes=[("Database files", "*.db")])
        if source_path:
            try:
                self.app_instance.db_manager.close()
                shutil.copy(source_path, self.app_instance.db_path)
                messagebox.showinfo("Éxito",
                                    "Base de datos importada. La aplicación se reiniciará para aplicar los cambios.")
                self.app_instance.restart_app()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo importar la base de datos:\n{e}")

    def change_db_path(self):
        initial_dir = os.path.dirname(self.app_instance.db_path)
        new_path = filedialog.askopenfilename(title="Seleccionar archivo de base de datos (.db)",
                                              initialdir=initial_dir,
                                              filetypes=[("Database files", "*.db"), ("All files", "*.*")])

        if new_path and os.path.exists(new_path):
            logging.info(f"El usuario ha seleccionado una nueva ruta para la BD: {new_path}")
            try:
                self.app_instance.config.set("Database", "path", new_path)

                # Utiliza la ruta del config.ini guardada en la app principal
                with open(self.app_instance.config_path, "w") as configfile:
                    self.app_instance.config.write(configfile)

                logging.info("El archivo config.ini ha sido actualizado con la nueva ruta.")
                messagebox.showinfo("Cambio Exitoso",
                                    "La ubicación de la base de datos ha sido actualizada.\nLa aplicación se reiniciará para aplicar los cambios.")
                self.app_instance.restart_app()
            except Exception as e:
                logging.error(f"Error al intentar cambiar la ruta de la base de datos: {e}")
                messagebox.showerror("Error", f"No se pudo cambiar la ruta de la base de datos:\n{e}")

# =================================================================================
# CLASE PRINCIPAL DE LA APLICACIÓN
# =================================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        logging.info("Iniciando App.__init__...")

        self.title("Calculadora de Tiempos de Montaje")
        self.geometry("1100x720")

        try:
            self.config_path = resource_path("config.ini")
            self.config = configparser.ConfigParser()
            self.config.read(self.config_path)
            if "Database" not in self.config:
                self.config["Database"] = {"path": "montaje.db"}
                with open(self.config_path, "w") as configfile:
                    self.config.write(configfile)
            db_filename = self.config["Database"]["path"]
            self.db_path = resource_path(db_filename)
            self.db_manager = DatabaseManager(db_path=self.db_path)
            logging.info("Configuración y base de datos cargadas con éxito.")

        except Exception as e:
            logging.critical(f"ERROR CRÍTICO CAPTURADO EN __init__: {e}", exc_info=True)
            messagebox.showerror("Error Crítico de Configuración",
                                 f"No se pudo inicializar la configuración o la base de datos:\n{e}\n\nConsulte app.log para más detalles.")
            self.destroy()
            return

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.navigation_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(6, weight=1)
        ctk.CTkLabel(self.navigation_frame, text="  Menú Principal", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=20)

        self.buttons = {}
        button_info = [("Inicio", "home"), ("Añadir Productos", "add_product"),
                       ("Crear Fabricación", "create_fabrication"), ("Editar / Visualizar", "edit"),
                       ("Calcular Tiempos", "calculate")]
        for i, (text, name) in enumerate(button_info):
            button = ctk.CTkButton(self.navigation_frame, text=text,
                                   command=lambda n=name: self.select_frame_by_name(n))
            button.grid(row=i + 1, column=0, padx=20, pady=10)
            self.buttons[name] = button

        self.help_button = ctk.CTkButton(self.navigation_frame, text="¿Cómo funciona?",
                                         command=lambda: self.select_frame_by_name("help"))
        self.help_button.grid(row=7, column=0, padx=20, pady=10)
        self.settings_button = ctk.CTkButton(self.navigation_frame, text="Configuración",
                                             command=lambda: self.select_frame_by_name("settings"))
        self.settings_button.grid(row=8, column=0, padx=20, pady=20)

        self.frames = {
            "home": HomeFrame(self),
            "add_product": AddProductFrame(self, self.db_manager),
            "create_fabrication": CreateFabricacionFrame(self, self.db_manager),
            "edit": EditFrame(self, self.db_manager),
            "calculate": CalculateTimesFrame(self, self.db_manager),
            "help": HelpFrame(self),
            "settings": SettingsFrame(self, self)
        }
        self.select_frame_by_name("home")
        logging.info("App.__init__ completado con éxito.")

    def select_frame_by_name(self, name):
        for btn in self.buttons.values():
            btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.help_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.settings_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

        for frame in self.frames.values():
            frame.grid_forget()

        if name in self.frames:
            self.frames[name].grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        active_button = self.buttons.get(name) or (
            self.help_button if name == "help" else self.settings_button if name == "settings" else None)
        if active_button:
            active_button.configure(fg_color="#1F618D")

    def on_closing(self):
        if self.db_manager and self.db_manager.conn:
            self.db_manager.close()
        self.destroy()

    def restart_app(self):
        self.on_closing()
        os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == "__main__":
    logging.info("Bloque __main__ alcanzado. Creando instancia de App.")
    app = App()
    if app.winfo_exists(): # Solo ejecutar si la ventana no fue destruida por un error
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        logging.info("Iniciando mainloop de la aplicación.")
        app.mainloop()
    else:
        logging.warning("La instancia de la app fue destruida durante __init__. No se iniciará mainloop.")