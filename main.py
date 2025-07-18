# =================================================================================
# APLICACIÓN PRINCIPAL (main.py) - VERSIÓN 4 (Corregida)
# =================================================================================
# Corregida la indentación y estructura de la clase App.
# Añadida la funcionalidad completa de Cálculo de Tiempos, Ayuda y Configuración.
# =================================================================================

import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
import math
import shutil
import configparser
import sys
import os
import random
import requests  # <-- Añadir esta
import json  # <-- Añadir esta
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
        welcome_label = ctk.CTkLabel(
            self,
            text="Bienvenido a la Calculadora de Tiempos",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        welcome_label.grid(row=0, column=0, padx=30, pady=(30, 10))

        quote_frame = ctk.CTkFrame(self, corner_radius=15)
        quote_frame.grid(row=1, column=0, padx=30, pady=30, sticky="nsew")
        quote_frame.grid_columnconfigure(0, weight=1)

        quote_text = ctk.CTkLabel(
            quote_frame,
            text=f"« {quote} »",
            font=ctk.CTkFont(size=20, slant="italic"),
            wraplength=700,
        )
        quote_text.pack(expand=True, padx=40, pady=(40, 10))

        author_text = ctk.CTkLabel(
            quote_frame, text=f"— {author}", font=ctk.CTkFont(size=16, weight="bold")
        )
        author_text.pack(expand=True, anchor="e", padx=40, pady=(0, 40))

    def get_quote_from_api(self):
        """Obtiene una frase del día desde la API web."""
        # URL de la API que has proporcionado
        url = "https://frasedeldia.azurewebsites.net/api/phrase"

        try:
            # Hacemos la llamada a la API con un tiempo de espera de 5 segundos
            response = requests.get(url, timeout=5)
            # Esto genera un error si la respuesta no es exitosa (ej: 404, 500)
            response.raise_for_status()

            # Convertimos la respuesta JSON en un diccionario de Python
            data = response.json()

            # Devolvemos la frase y el autor
            return data.get("phrase", "No se pudo cargar la frase."), data.get(
                "author", "Sistema"
            )

        except requests.exceptions.RequestException as e:
            # Si hay cualquier error de red (sin internet, API caída, etc.)
            print(f"Error al contactar la API: {e}")
            # Devolvemos una frase por defecto para que la app no falle
            return (
                "La única forma de hacer un gran trabajo es amar lo que haces.",
                "Steve Jobs",
            )


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

        if not data["codigo"] or not data["descripcion"]:
            messagebox.showerror(
                "Error de Validación", "El código y la descripción son obligatorios."
            )
            return

        if data["tiene_subfabricaciones"] == 0:
            try:
                data["tiempo_optimo"] = float(
                    self.tiempo_optimo_entry.get().replace(",", ".")
                )
                data["tipo_trabajador"] = min(
                    s["tipo_trabajador"] for s in self.subfabricaciones_data
                )
                sub_data = None
            except ValueError:
                messagebox.showerror(
                    "Error de Validación", "El tiempo óptimo debe ser un número válido."
                )
                return
        else:
            if not self.subfabricaciones_data:
                messagebox.showerror(
                    "Error de Validación",
                    "Si marca 'Tiene subfabricaciones', debe añadir al menos una parte.",
                )
                return
            data["tiempo_optimo"] = sum(s["tiempo"] for s in self.subfabricaciones_data)
            data["tipo_trabajador"] = max(
                s["tipo_trabajador"] for s in self.subfabricaciones_data
            )
            sub_data = self.subfabricaciones_data

        if self.db_manager.add_product(data, sub_data):
            messagebox.showinfo(
                "Éxito", f"Producto '{data['codigo']}' guardado correctamente."
            )
            self.codigo_entry.delete(0, "end")
            self.descripcion_entry.delete(0, "end")
            self.donde_textbox.delete("1.0", "end")
            self.tiempo_optimo_entry.delete(0, "end")
            self.subfabricaciones_data = []
            self.sub_info_label.configure(text="No se han añadido subfabricaciones.")
        else:
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

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(
            self,
            text="Crear Nueva Fabricación",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))

        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(
            row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew"
        )
        self.top_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.top_frame, text="Código Fabricación:").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        self.fab_codigo_entry = ctk.CTkEntry(
            self.top_frame, placeholder_text="Ej: KIT-01"
        )
        self.fab_codigo_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.top_frame, text="Descripción:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.fab_desc_entry = ctk.CTkEntry(
            self.top_frame, placeholder_text="Ej: Kit de Montaje Final PC"
        )
        self.fab_desc_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.top_frame, text="─" * 80).grid(
            row=2, column=0, columnspan=2, pady=5
        )

        ctk.CTkLabel(self.top_frame, text="Buscar Producto:").grid(
            row=3, column=0, padx=10, pady=5, sticky="w"
        )
        self.search_entry = ctk.CTkEntry(
            self.top_frame,
            placeholder_text="Escriba código o descripción del producto...",
        )
        self.search_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.update_search_results)

        self.search_results_frame = ctk.CTkScrollableFrame(
            self.top_frame, label_text="Resultados de Búsqueda"
        )
        self.search_results_frame.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.search_results_labels = []

        ctk.CTkLabel(self.top_frame, text="Cantidad:").grid(
            row=5, column=0, padx=10, pady=5, sticky="w"
        )
        self.cantidad_entry = ctk.CTkEntry(self.top_frame, placeholder_text="1")
        self.cantidad_entry.grid(row=5, column=1, padx=(10, 150), pady=5, sticky="ew")

        self.add_product_button = ctk.CTkButton(
            self.top_frame,
            text="Añadir Producto a la Lista",
            command=self.add_product_to_list,
        )
        self.add_product_button.grid(row=6, column=1, padx=10, pady=10, sticky="e")
        self.selected_product_code = None

        self.content_list_frame = ctk.CTkFrame(self)
        self.content_list_frame.grid(
            row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew"
        )

        self.content_textbox = ctk.CTkTextbox(
            self.content_list_frame, state="disabled", font=("Consolas", 12)
        )
        self.content_textbox.pack(expand=True, fill="both", padx=10, pady=10)

        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(
            row=3, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew"
        )

        self.clear_button = ctk.CTkButton(
            self.bottom_frame,
            text="Limpiar Lista",
            command=self.clear_list,
            fg_color="#D35400",
            hover_color="#E67E22",
        )
        self.clear_button.pack(side="left", padx=10, pady=10)
        self.save_button = ctk.CTkButton(
            self.bottom_frame, text="Guardar Fabricación", command=self.save_fabricacion
        )
        self.save_button.pack(side="right", padx=10, pady=10)

    def update_search_results(self, event=None):
        query = self.search_entry.get()
        for label in self.search_results_labels:
            label.destroy()
        self.search_results_labels.clear()
        self.selected_product_code = None
        if len(query) < 2:
            return
        results = self.db_manager.search_products(query)
        for codigo, descripcion in results:
            text = f"{codigo} - {descripcion}"
            label = ctk.CTkLabel(
                self.search_results_frame, text=text, cursor="hand2", anchor="w"
            )
            label.pack(fill="x", padx=5)
            label.bind(
                "<Button-1>", lambda e, c=codigo, t=text: self.select_product(c, t)
            )
            self.search_results_labels.append(label)

    def select_product(self, codigo, text):
        self.selected_product_code = codigo
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, text)
        for label in self.search_results_labels:
            label.destroy()
        self.search_results_labels.clear()

    def add_product_to_list(self):
        if not self.selected_product_code:
            messagebox.showerror(
                "Error", "Debe seleccionar un producto de la lista de búsqueda."
            )
            return
        try:
            cantidad = int(self.cantidad_entry.get() or 1)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Error", "La cantidad debe ser un número entero positivo."
            )
            return

        for item in self.contenido_actual:
            if item["producto_codigo"] == self.selected_product_code:
                item["cantidad"] += cantidad
                break
        else:
            self.contenido_actual.append(
                {
                    "producto_codigo": self.selected_product_code,
                    "producto_texto": self.search_entry.get(),
                    "cantidad": cantidad,
                }
            )

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
        if messagebox.askyesno(
            "Confirmar", "¿Está seguro de que desea limpiar la lista de productos?"
        ):
            self.contenido_actual.clear()
            self.update_content_textbox()

    def save_fabricacion(self):
        fab_codigo = self.fab_codigo_entry.get().strip()
        fab_desc = self.fab_desc_entry.get().strip()
        if not fab_codigo or not fab_desc:
            messagebox.showerror(
                "Error",
                "El código y la descripción de la fabricación son obligatorios.",
            )
            return
        if not self.contenido_actual:
            messagebox.showerror(
                "Error", "La fabricación debe contener al menos un producto."
            )
            return
        if self.db_manager.add_fabricacion(fab_codigo, fab_desc, self.contenido_actual):
            messagebox.showinfo(
                "Éxito", f"Fabricación '{fab_codigo}' guardada correctamente."
            )
            self.clear_form()
        else:
            messagebox.showerror(
                "Error de Base de Datos",
                f"No se pudo guardar la fabricación. ¿Quizás el código '{fab_codigo}' ya existe?",
            )

    def clear_form(self):
        self.fab_codigo_entry.delete(0, "end")
        self.fab_desc_entry.delete(0, "end")
        self.search_entry.delete(0, "end")
        self.cantidad_entry.delete(0, "end")
        self.contenido_actual.clear()
        self.update_content_textbox()


# =================================================================================
# CLASE PARA LA PANTALLA "EDITAR / VISUALIZAR"
# =================================================================================
class EditFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_app = parent

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.search_frame.grid_columnconfigure(1, weight=1)

        self.search_type_var = ctk.StringVar(value="Productos")
        self.search_type_selector = ctk.CTkSegmentedButton(
            self.search_frame,
            values=["Productos", "Fabricaciones"],
            variable=self.search_type_var,
            command=self.clear_search,
        )
        self.search_type_selector.grid(row=0, column=0, padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(
            self.search_frame, placeholder_text="Buscar por código o descripción..."
        )
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.update_search_results)

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=2, uniform="group1")
        self.content_frame.grid_columnconfigure(1, weight=3, uniform="group1")
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.results_frame = ctk.CTkScrollableFrame(
            self.content_frame, label_text="Resultados"
        )
        self.results_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.edit_area_frame = ctk.CTkFrame(self.content_frame)

    def clear_search(self, value=None):
        self.search_entry.delete(0, "end")
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.edit_area_frame.grid_forget()

    def update_search_results(self, event=None):
        query = self.search_entry.get()
        search_type = self.search_type_var.get()
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.edit_area_frame.grid_forget()
        if len(query) < 2:
            return
        results = (
            self.db_manager.search_products(query)
            if search_type == "Productos"
            else self.db_manager.search_fabricaciones(query)
        )
        for codigo, descripcion in results:
            text = f"{codigo} | {descripcion}"
            label = ctk.CTkLabel(
                self.results_frame, text=text, cursor="hand2", anchor="w"
            )
            label.pack(fill="x", padx=5, pady=2)
            label.bind("<Button-1>", lambda e, c=codigo: self.load_item_for_edit(c))

    def load_item_for_edit(self, codigo):
        for widget in self.edit_area_frame.winfo_children():
            widget.destroy()
        search_type = self.search_type_var.get()
        if search_type == "Productos":
            self.create_product_edit_form(codigo)
        else:
            self.create_fabricacion_edit_form(codigo)
        self.edit_area_frame.grid(row=0, column=1, padx=(20, 0), pady=0, sticky="nsew")

    # Reemplaza este método DENTRO de la clase EditFrame en main.py
    def create_product_edit_form(self, codigo):
        product_data, sub_data_raw = self.db_manager.get_product_details(codigo)
        if not product_data:
            messagebox.showerror("Error", "No se encontró el producto.")
            return

        # Adaptar los datos para la UI
        data = {
            "codigo": product_data[0],
            "descripcion": product_data[1],
            "departamento": product_data[2],
            "tipo_trabajador": product_data[3],
            "donde": product_data[4],
            "tiene_subfabricaciones": product_data[5],
            "tiempo_optimo": product_data[6],
        }
        self.subfabricaciones_data = [
            {"descripcion": s[2], "tiempo": s[3], "tipo_trabajador": s[4]}
            for s in sub_data_raw
        ]

        form = self.edit_area_frame
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form, text="Editando Producto", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=10)

        # Campo Código
        ctk.CTkLabel(form, text="Código:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.p_codigo_entry = ctk.CTkEntry(form)
        self.p_codigo_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.p_codigo_entry.insert(0, data["codigo"])

        # Campo Descripción
        ctk.CTkLabel(form, text="Descripción:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        self.p_desc_entry = ctk.CTkEntry(form)
        self.p_desc_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.p_desc_entry.insert(0, data["descripcion"])

        # Campo Departamento
        ctk.CTkLabel(form, text="Departamento:").grid(
            row=3, column=0, padx=10, pady=5, sticky="w"
        )
        self.p_departamento_menu = ctk.CTkOptionMenu(
            form, values=["Mecánica", "Electrónica", "Montaje"]
        )
        self.p_departamento_menu.set(data["departamento"])
        self.p_departamento_menu.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        # Campo "Dónde"
        ctk.CTkLabel(form, text="Dónde se ubica:").grid(
            row=5, column=0, padx=10, pady=5, sticky="nw"
        )
        self.p_donde_textbox = ctk.CTkTextbox(form, height=80)
        self.p_donde_textbox.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        self.p_donde_textbox.insert("1.0", data["donde"] or "")

        # --- Lógica de Subfabricaciones ---
        self.p_sub_frame = ctk.CTkFrame(form, fg_color="transparent")
        self.p_sub_frame.grid(
            row=6, column=0, columnspan=2, padx=10, pady=5, sticky="ew"
        )
        self.p_sub_frame.grid_columnconfigure(1, weight=1)

        # Switch y sus componentes
        self.p_tiene_sub_var = ctk.IntVar(value=data["tiene_subfabricaciones"])
        self.p_sub_switch = ctk.CTkSwitch(
            self.p_sub_frame,
            text="¿Tiene subfabricaciones?",
            variable=self.p_tiene_sub_var,
            command=self._p_toggle_sub_mode,
        )
        self.p_sub_switch.grid(row=0, column=0, padx=10)

        self.p_tiempo_optimo_label = ctk.CTkLabel(
            self.p_sub_frame, text="Tiempo Óptimo (min):"
        )
        self.p_tiempo_optimo_entry = ctk.CTkEntry(self.p_sub_frame)
        self.p_tiempo_optimo_entry.insert(0, str(data["tiempo_optimo"]))

        self.p_trabajador_menu = ctk.CTkOptionMenu(
            self.p_sub_frame, values=["Tipo 1", "Tipo 2", "Tipo 3"]
        )
        self.p_trabajador_menu.set(f"Tipo {data['tipo_trabajador']}")

        self.p_add_sub_button = ctk.CTkButton(
            self.p_sub_frame,
            text="Añadir/Editar Subfabricaciones",
            command=self._p_open_sub_window,
        )
        self.p_sub_info_label = ctk.CTkLabel(
            self.p_sub_frame, text="", text_color="gray"
        )

        self._p_toggle_sub_mode()  # Llamar para establecer el estado inicial correcto

        # --- Botones de Acción ---
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.grid(row=10, column=0, columnspan=2, pady=20, sticky="e")

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Guardar Cambios",
            command=lambda: self.save_product_changes(codigo),
        )
        save_btn.pack(side="left", padx=5)
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="Eliminar",
            fg_color="#E74C3C",
            hover_color="#C0392B",
            command=lambda: self.delete_product(codigo),
        )
        delete_btn.pack(side="left", padx=5)

    def _p_toggle_sub_mode(self):
        if self.p_tiene_sub_var.get() == 0:
            self.p_tiempo_optimo_label.grid(
                row=1, column=0, padx=10, pady=5, sticky="w"
            )
            self.p_tiempo_optimo_entry.grid(
                row=1, column=1, padx=10, pady=5, sticky="ew"
            )
            self.p_trabajador_menu.configure(state="normal")
            self.p_add_sub_button.grid_remove()
            self.p_sub_info_label.grid_remove()
        else:
            self.p_tiempo_optimo_label.grid_remove()
            self.p_tiempo_optimo_entry.grid_remove()
            self.p_trabajador_menu.configure(state="disabled")
            self.p_add_sub_button.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
            self.p_sub_info_label.grid(row=2, column=1, padx=10, sticky="w")
            count = len(self.subfabricaciones_data)
            total_time = sum(s["tiempo"] for s in self.subfabricaciones_data)
            self.p_sub_info_label.configure(
                text=f"{count} parte(s). Tiempo total: {total_time:.2f} min."
            )

    def _p_open_sub_window(self):
        sub_window = SubfabricacionesWindow(
            self, existing_subfabricaciones=self.subfabricaciones_data
        )

        # Usamos el mismo método de espera aquí
        self.wait_window(sub_window)

        # Recogemos los datos actualizados al cerrar
        self.subfabricaciones_data = sub_window.subfabricaciones
        self._p_toggle_sub_mode()

    def save_product_changes(self, original_codigo):
        new_data = {
            "codigo": self.p_codigo_entry.get().strip(),
            "descripcion": self.p_desc_entry.get().strip(),
            "departamento": self.p_departamento_menu.get(),
            "donde": self.p_donde_textbox.get("1.0", "end-1c").strip(),
            "tiene_subfabricaciones": self.p_tiene_sub_var.get(),
        }
        sub_data = self.subfabricaciones_data
        if not new_data["codigo"] or not new_data["descripcion"]:
            messagebox.showerror(
                "Error de Validación", "El código y la descripción son obligatorios."
            )
            return
        if new_data["tiene_subfabricaciones"] == 0:
            try:
                new_data["tiempo_optimo"] = float(
                    self.p_tiempo_optimo_entry.get().replace(",", ".")
                )
                new_data["tipo_trabajador"] = int(
                    self.p_trabajador_menu.get().split(" ")[1]
                )
            except (ValueError, IndexError):
                messagebox.showerror(
                    "Error de Validación", "El tiempo óptimo debe ser un número válido."
                )
                return
        else:
            if not sub_data:
                messagebox.showerror(
                    "Error de Validación",
                    "Si marca 'Tiene subfabricaciones', debe añadir al menos una parte.",
                )
                return
            new_data["tiempo_optimo"] = sum(s["tiempo"] for s in sub_data)
            new_data["tipo_trabajador"] = min(s["tipo_trabajador"] for s in sub_data)
        if self.db_manager.update_product(original_codigo, new_data, sub_data):
            messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
            self.clear_search()
        else:
            messagebox.showerror("Error", "No se pudo actualizar el producto.")

    def delete_product(self, codigo):
        if messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar el producto '{codigo}'?\nEsta acción no se puede deshacer.",
            icon="warning",
        ):
            if self.db_manager.delete_product(codigo):
                messagebox.showinfo("Éxito", "Producto eliminado correctamente.")
                self.clear_search()
            else:
                messagebox.showerror("Error", "No se pudo eliminar el producto.")

    def create_fabricacion_edit_form(self, codigo):
        fab_data, contenido_raw = self.db_manager.get_fabricacion_details(codigo)
        if not fab_data:
            messagebox.showerror("Error", "No se encontró la fabricación.")
            return
        data = {"codigo": fab_data[0], "descripcion": fab_data[1]}
        self.contenido_actual = [
            {
                "producto_codigo": c[0],
                "producto_texto": f"{c[0]} - {c[1]}",
                "cantidad": c[2],
            }
            for c in contenido_raw
        ]
        form = self.edit_area_frame
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form, text="Editando Fabricación", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=10)
        ctk.CTkLabel(form, text="Código:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.f_codigo_entry = ctk.CTkEntry(form)
        self.f_codigo_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.f_codigo_entry.insert(0, data["codigo"])
        ctk.CTkLabel(form, text="Descripción:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        self.f_desc_entry = ctk.CTkEntry(form)
        self.f_desc_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.f_desc_entry.insert(0, data["descripcion"])
        ctk.CTkLabel(form, text="Contenido:").grid(
            row=3, column=0, padx=10, pady=5, sticky="nw"
        )
        self.f_content_textbox = ctk.CTkTextbox(form, height=200)
        self.f_content_textbox.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.update_fab_content_textbox()
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")
        save_btn = ctk.CTkButton(
            btn_frame,
            text="Guardar Cambios",
            command=lambda: self.save_fabricacion_changes(codigo),
        )
        save_btn.pack(side="right", padx=10)
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="Eliminar",
            fg_color="#E74C3C",
            hover_color="#C0392B",
            command=lambda: self.delete_fabricacion(codigo),
        )
        delete_btn.pack(side="right", padx=10)

    def update_fab_content_textbox(self):
        self.f_content_textbox.configure(state="normal")
        self.f_content_textbox.delete("1.0", "end")
        for item in self.contenido_actual:
            line = f"CANT: {item['cantidad']:<5} | {item['producto_texto']}\n"
            self.f_content_textbox.insert("end", line)
        self.f_content_textbox.configure(state="disabled")

    def save_fabricacion_changes(self, original_codigo):
        new_data = {
            "codigo": self.f_codigo_entry.get(),
            "descripcion": self.f_desc_entry.get(),
        }
        if self.db_manager.update_fabricacion(
            original_codigo, new_data, self.contenido_actual
        ):
            messagebox.showinfo("Éxito", "Fabricación actualizada correctamente.")
            self.clear_search()
        else:
            messagebox.showerror("Error", "No se pudo actualizar la fabricación.")

    def delete_fabricacion(self, codigo):
        if messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar la fabricación '{codigo}'?",
            icon="warning",
        ):
            if self.db_manager.delete_fabricacion(codigo):
                messagebox.showinfo("Éxito", "Fabricación eliminada.")
                self.clear_search()
            else:
                messagebox.showerror("Error", "No se pudo eliminar la fabricación.")


# =================================================================================
# CLASE PARA LA PANTALLA "CALCULAR TIEMPOS"
# =================================================================================
class CalculateTimesFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.WORKDAY_MINUTES = 465

        self.grid_columnconfigure(0, weight=1)

        self.selection_frame = ctk.CTkFrame(self)
        self.selection_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.selection_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.selection_frame, text="Fabricación:").grid(
            row=0, column=0, padx=10, pady=10
        )
        self.fab_search_entry = ctk.CTkEntry(
            self.selection_frame, placeholder_text="Buscar fabricación a calcular..."
        )
        self.fab_search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.fab_search_entry.bind("<KeyRelease>", self.update_fab_search_results)
        self.selected_fab_code = None

        self.fab_search_results_frame = ctk.CTkFrame(self.selection_frame)
        self.fab_search_results_frame.grid(row=1, column=1, padx=10, sticky="ew")

        ctk.CTkLabel(self.selection_frame, text="Unidades a Fabricar:").grid(
            row=2, column=0, padx=10, pady=10
        )
        self.units_entry = ctk.CTkEntry(self.selection_frame)
        self.units_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        self.calc_frame = ctk.CTkFrame(self)
        self.calc_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.calc_frame.grid_columnconfigure(0, weight=1)

        self.calc_type_var = ctk.StringVar(value="Por Tiempo")
        self.calc_type_selector = ctk.CTkSegmentedButton(
            self.calc_frame,
            values=["Por Tiempo", "Por Trabajadores"],
            variable=self.calc_type_var,
            command=self.toggle_calc_mode,
        )
        self.calc_type_selector.grid(
            row=0, column=0, columnspan=4, padx=10, pady=10, sticky="ew"
        )

        self.time_label = ctk.CTkLabel(self.calc_frame, text="Tiempo (días):")
        self.time_entry = ctk.CTkEntry(self.calc_frame)

        self.w1_label = ctk.CTkLabel(self.calc_frame, text="Trabajadores T1:")
        self.w1_entry = ctk.CTkEntry(self.calc_frame, placeholder_text="0")
        self.w2_label = ctk.CTkLabel(self.calc_frame, text="Trabajadores T2:")
        self.w2_entry = ctk.CTkEntry(self.calc_frame, placeholder_text="0")
        self.w3_label = ctk.CTkLabel(self.calc_frame, text="Trabajadores T3:")
        self.w3_entry = ctk.CTkEntry(self.calc_frame, placeholder_text="0")

        self.toggle_calc_mode("Por Tiempo")

        self.results_frame = ctk.CTkFrame(self)
        self.results_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)

        self.results_textbox = ctk.CTkTextbox(
            self.results_frame, state="disabled", font=("Consolas", 14)
        )
        self.results_textbox.pack(expand=True, fill="both", padx=10, pady=10)

        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=4, column=0, padx=20, pady=10, sticky="e")

        self.calc_button = ctk.CTkButton(
            self.action_frame, text="Calcular Tiempos", command=self.perform_calculation
        )
        self.calc_button.pack(side="left", padx=10)
        self.export_button = ctk.CTkButton(
            self.action_frame, text="Exportar a Excel", command=self.export_to_excel
        )
        self.export_button.pack(side="left", padx=10)

    def update_fab_search_results(self, event=None):
        query = self.fab_search_entry.get()
        for widget in self.fab_search_results_frame.winfo_children():
            widget.destroy()
        if len(query) < 1:
            return
        results = self.db_manager.search_fabricaciones(query)
        for codigo, descripcion in results:
            text = f"{codigo} - {descripcion}"
            label = ctk.CTkLabel(
                self.fab_search_results_frame, text=text, cursor="hand2", anchor="w"
            )
            label.pack(fill="x", padx=5)
            label.bind(
                "<Button-1>", lambda e, c=codigo, t=text: self.select_fabricacion(c, t)
            )

    def select_fabricacion(self, codigo, texto):
        self.selected_fab_code = codigo
        self.fab_search_entry.delete(0, "end")
        self.fab_search_entry.insert(0, texto)
        for widget in self.fab_search_results_frame.winfo_children():
            widget.destroy()

    def toggle_calc_mode(self, value):
        self.time_label.grid_forget()
        self.time_entry.grid_forget()
        self.w1_label.grid_forget()
        self.w1_entry.grid_forget()
        self.w2_label.grid_forget()
        self.w2_entry.grid_forget()
        self.w3_label.grid_forget()
        self.w3_entry.grid_forget()
        if value == "Por Tiempo":
            self.time_label.grid(row=1, column=0, padx=10, pady=5)
            self.time_entry.grid(row=1, column=1, padx=10, pady=5)
        else:
            self.w1_label.grid(row=1, column=0, padx=10, pady=5)
            self.w1_entry.grid(row=1, column=1, padx=10, pady=5)
            self.w2_label.grid(row=2, column=0, padx=10, pady=5)
            self.w2_entry.grid(row=2, column=1, padx=10, pady=5)
            self.w3_label.grid(row=3, column=0, padx=10, pady=5)
            self.w3_entry.grid(row=3, column=1, padx=10, pady=5)

    def get_and_validate_inputs(self):
        if not self.selected_fab_code:
            messagebox.showerror("Error", "Debe seleccionar una fabricación.")
            return None
        try:
            units = int(self.units_entry.get())
            if units <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror(
                "Error", "El número de unidades debe ser un entero positivo."
            )
            return None
        self.calculation_data = self.db_manager.get_data_for_calculation(
            self.selected_fab_code
        )
        if not self.calculation_data:
            messagebox.showerror(
                "Error", "No se pudieron cargar los datos para el cálculo."
            )
            return None
        self.minutes_per_unit = {1: 0, 2: 0, 3: 0}
        for prod in self.calculation_data:
            if prod["tiene_subfabricaciones"]:
                for sub in prod["sub_partes"]:
                    tiempo_real = sub["tiempo"] * 1.20
                    self.minutes_per_unit[sub["tipo_trabajador"]] += (
                        tiempo_real * prod["cantidad_en_kit"]
                    )
            else:
                tiempo_real = prod["tiempo_optimo"] * 1.20
                self.minutes_per_unit[prod["tipo_trabajador"]] += (
                    tiempo_real * prod["cantidad_en_kit"]
                )
        self.total_minutes = {k: v * units for k, v in self.minutes_per_unit.items()}
        return units

    def perform_calculation(self):
        units = self.get_and_validate_inputs()
        if not units:
            return
        calc_type = self.calc_type_var.get()
        self.results_textbox.configure(state="normal")
        self.results_textbox.delete("1.0", "end")
        header = (
            f"CÁLCULO PARA {units} UNIDAD(ES) DE '{self.selected_fab_code}'\n"
            + "=" * 50
            + "\n"
        )
        self.results_textbox.insert("end", header)
        if calc_type == "Por Tiempo":
            try:
                days = float(self.time_entry.get().replace(",", "."))
                if days <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror(
                    "Error", "El tiempo en días debe ser un número positivo."
                )
                return
            total_available_minutes_per_worker = days * self.WORKDAY_MINUTES
            w1_needed = math.ceil(
                self.total_minutes[1] / total_available_minutes_per_worker
            )
            w2_needed = math.ceil(
                self.total_minutes[2] / total_available_minutes_per_worker
            )
            w3_needed = math.ceil(
                self.total_minutes[3] / total_available_minutes_per_worker
            )
            self.results_textbox.insert(
                "end", f"Para terminar en {days} días, necesitará:\n"
            )
            self.results_textbox.insert(
                "end", f"  - Trabajadores Tipo 1: {w1_needed}\n"
            )
            self.results_textbox.insert(
                "end", f"  - Trabajadores Tipo 2: {w2_needed}\n"
            )
            self.results_textbox.insert(
                "end", f"  - Trabajadores Tipo 3: {w3_needed}\n"
            )
        else:
            try:
                w1 = int(self.w1_entry.get() or 0)
                w2 = int(self.w2_entry.get() or 0)
                w3 = int(self.w3_entry.get() or 0)
            except ValueError:
                messagebox.showerror(
                    "Error", "El número de trabajadores debe ser un entero."
                )
                return
            days1 = (
                (self.total_minutes[1] / (w1 * self.WORKDAY_MINUTES)) if w1 > 0 else 0
            )
            days2 = (
                (self.total_minutes[2] / (w2 * self.WORKDAY_MINUTES)) if w2 > 0 else 0
            )
            days3 = (
                (self.total_minutes[3] / (w3 * self.WORKDAY_MINUTES)) if w3 > 0 else 0
            )
            total_days = max(days1, days2, days3)
            self.results_textbox.insert(
                "end", f"Con {w1}T1, {w2}T2, {w3}T3, necesitará:\n"
            )
            self.results_textbox.insert(
                "end", f"  - Tiempo total: {total_days:.2f} días\n"
            )
        self.results_textbox.configure(state="disabled")

    # Reemplaza este método completo en la clase CalculateTimesFrame
    def export_to_excel(self):
        units = self.get_and_validate_inputs()
        if not units:
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")]
        )
        if not filepath:
            return

        # --- Hoja Resumen ---
        total_jornadas = sum(self.total_minutes.values()) / self.WORKDAY_MINUTES
        summary_data = {
            "Concepto": [
                "Fabricación",
                "Unidades Totales",
                "Minutos Reales T1",
                "Minutos Reales T2",
                "Minutos Reales T3",
                "TOTAL MINUTOS REALES",
                "TOTAL JORNADAS LABORALES",
            ],
            "Valor": [
                self.selected_fab_code,
                units,
                f"{self.total_minutes[1]:.2f}",
                f"{self.total_minutes[2]:.2f}",
                f"{self.total_minutes[3]:.2f}",
                f"{sum(self.total_minutes.values()):.2f}",
                f"{total_jornadas:.2f}",
            ],
        }
        df_summary = pd.DataFrame(summary_data)

        # --- Hojas por departamento (sin 'cantidad_en_kit' y con totales) ---
        df_mec = pd.DataFrame(
            [p for p in self.calculation_data if p["departamento"] == "Mecánica"]
        )
        df_ele = pd.DataFrame(
            [p for p in self.calculation_data if p["departamento"] == "Electrónica"]
        )
        df_mon = pd.DataFrame(
            [p for p in self.calculation_data if p["departamento"] == "Montaje"]
        )

        # CAMBIO: Eliminamos la columna 'cantidad_en_kit' de las hojas de departamento
        for df in [df_mec, df_ele, df_mon]:
            if "cantidad_en_kit" in df.columns:
                df.drop(columns=["cantidad_en_kit"], inplace=True)
            # NUEVO: Añadimos la fila de totales (sumando solo el tiempo)
            if not df.empty:
                df.loc["Total"] = pd.Series(
                    df["tiempo_optimo"].sum(), index=["tiempo_optimo"]
                )

        # --- Hoja de Desglose (sin 'cantidad_en_kit') ---
        all_parts = []
        for p in self.calculation_data:
            if p["tiene_subfabricaciones"]:
                for s in p["sub_partes"]:
                    # CAMBIO: Se elimina p["cantidad_en_kit"] de la lista
                    all_parts.append(
                        [
                            p["codigo"],
                            s["descripcion"],
                            s["tiempo"],
                            s["tiempo"] * 1.20,
                            s["tipo_trabajador"],
                        ]
                    )
            else:
                # CAMBIO: Se elimina p["cantidad_en_kit"] de la lista
                all_parts.append(
                    [
                        p["codigo"],
                        p["descripcion"],
                        p["tiempo_optimo"],
                        p["tiempo_optimo"] * 1.20,
                        p["tipo_trabajador"],
                    ]
                )

        # CAMBIO: Se elimina "Cant. en Kit" de las columnas
        df_detail = pd.DataFrame(
            all_parts,
            columns=[
                "Producto Padre",
                "Descripción Parte",
                "Tiempo Óptimo",
                "Tiempo Real",
                "Tipo Trab.",
            ],
        )

        # --- Escribir el archivo Excel ---
        with pd.ExcelWriter(filepath) as writer:
            # NUEVO: Se añade el título de la fabricación en la hoja de resumen
            pd.DataFrame([self.fab_search_entry.get()]).to_excel(
                writer, sheet_name="Resumen", startrow=0, header=False, index=False
            )
            df_summary.to_excel(writer, sheet_name="Resumen", startrow=2, index=False)

            df_mec.to_excel(writer, sheet_name="Mecanica", index=True)
            df_ele.to_excel(writer, sheet_name="Electronica", index=True)
            df_mon.to_excel(writer, sheet_name="Montaje", index=True)
            df_detail.to_excel(writer, sheet_name="Desglose Completo", index=False)

        messagebox.showinfo("Éxito", f"Informe exportado a\n{filepath}")


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
        ctk.CTkLabel(
            self,
            text="Configuración de la Base de Datos",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=20)
        self.db_path_label = ctk.CTkLabel(
            self, text=f"Ubicación actual: {self.app_instance.db_path}", wraplength=400
        )
        self.db_path_label.grid(row=1, column=0, padx=20, pady=10)
        self.export_button = ctk.CTkButton(
            self, text="Exportar Base de Datos (Backup)", command=self.export_db
        )
        self.export_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.import_button = ctk.CTkButton(
            self, text="Importar Base de Datos (Restaurar)", command=self.import_db
        )
        self.import_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

    def export_db(self):
        dest_path = filedialog.asksaveasfilename(
            title="Guardar copia de seguridad como...",
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
        )
        if dest_path:
            try:
                shutil.copy(self.app_instance.db_path, dest_path)
                messagebox.showinfo(
                    "Éxito", f"Copia de seguridad guardada en:\n{dest_path}"
                )
            except Exception as e:
                messagebox.showerror(
                    "Error", f"No se pudo guardar la copia de seguridad:\n{e}"
                )

    def import_db(self):
        if not messagebox.askyesno(
            "Confirmar Importación",
            "ADVERTENCIA:\nEsto reemplazará tu base de datos actual con el archivo que selecciones.\n¿Deseas continuar?",
        ):
            return
        source_path = filedialog.askopenfilename(
            title="Seleccionar base de datos para importar",
            filetypes=[("Database files", "*.db")],
        )
        if source_path:
            try:
                self.app_instance.db_manager.close()
                shutil.copy(source_path, self.app_instance.db_path)
                messagebox.showinfo(
                    "Éxito",
                    "Base de datos importada. La aplicación se reiniciará para aplicar los cambios.",
                )
                self.app_instance.restart_app()
            except Exception as e:
                messagebox.showerror(
                    "Error", f"No se pudo importar la base de datos:\n{e}"
                )


# =================================================================================
# CLASE PRINCIPAL DE LA APLICACIÓN
# =================================================================================
class App(ctk.CTk):
    # Reemplaza este método completo en tu clase App
    def __init__(self):
        super().__init__()
        self.title("Calculadora de Tiempos de Montaje")
        self.geometry("1100x720")

        # Lógica de Configuración y BD
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        if "Database" not in self.config:
            self.config["Database"] = {"path": "montaje.db"}
            with open("config.ini", "w") as configfile:
                self.config.write(configfile)
        self.db_path = self.config["Database"]["path"]
        self.db_manager = DatabaseManager(db_path=self.db_path)

        # Layout Principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Barra de Navegación Lateral
        self.navigation_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(6, weight=1)  # Espacio de empuje

        self.navigation_frame_label = ctk.CTkLabel(
            self.navigation_frame,
            text="  Menú Principal",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        # Botones (Añadido "Inicio" y corregido el orden)
        self.buttons = {}
        button_info = [
            ("Inicio", "home"),  # <-- BOTÓN NUEVO
            ("Añadir Productos", "add_product"),
            ("Crear Fabricación", "create_fabrication"),
            ("Editar / Visualizar", "edit"),
            ("Calcular Tiempos", "calculate"),
        ]

        for i, (text, name) in enumerate(button_info):
            button = ctk.CTkButton(
                self.navigation_frame,
                text=text,
                command=lambda n=name: self.select_frame_by_name(n),
            )
            button.grid(row=i + 1, column=0, padx=20, pady=10)
            self.buttons[name] = button

        self.help_button = ctk.CTkButton(
            self.navigation_frame,
            text="¿Cómo funciona?",
            command=lambda: self.select_frame_by_name("help"),
        )
        self.help_button.grid(row=7, column=0, padx=20, pady=10)  # Fila ajustada

        self.settings_button = ctk.CTkButton(
            self.navigation_frame,
            text="Configuración",
            command=lambda: self.select_frame_by_name("settings"),
        )
        self.settings_button.grid(row=8, column=0, padx=20, pady=20)  # Fila ajustada

        # Creación de TODOS los Frames (Añadido home_frame)
        self.home_frame = HomeFrame(self)  # <-- FRAME NUEVO
        self.add_product_frame = AddProductFrame(self, self.db_manager)
        self.create_fabrication_frame = CreateFabricacionFrame(self, self.db_manager)
        self.edit_frame = EditFrame(self, self.db_manager)
        self.calculate_frame = CalculateTimesFrame(self, self.db_manager)
        self.help_frame = HelpFrame(self)
        self.settings_frame = SettingsFrame(self, self)

        # Selección del Frame Inicial
        self.select_frame_by_name("home")  # <-- Empezamos en la pantalla de Inicio

    # Reemplaza este método completo en tu clase App
    def select_frame_by_name(self, name):
        # Resetear colores de botones
        all_buttons = self.buttons.copy()
        all_buttons["help"] = self.help_button
        all_buttons["settings"] = self.settings_button
        for btn in all_buttons.values():
            btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

        # Ocultar todos los frames
        self.home_frame.grid_forget()  # <-- Añadido
        self.add_product_frame.grid_forget()
        self.create_fabrication_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.calculate_frame.grid_forget()
        self.help_frame.grid_forget()
        self.settings_frame.grid_forget()

        # Mostrar el frame seleccionado
        active_button = None
        if name == "home":  # <-- Añadido
            self.home_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
            active_button = self.buttons.get(name)
        elif name == "add_product":
            self.add_product_frame.grid(
                row=0, column=1, padx=20, pady=20, sticky="nsew"
            )
            active_button = self.buttons.get(name)
        elif name == "create_fabrication":
            self.create_fabrication_frame.grid(
                row=0, column=1, padx=20, pady=20, sticky="nsew"
            )
            active_button = self.buttons.get(name)
        elif name == "edit":
            self.edit_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
            self.edit_frame.clear_search()
            active_button = self.buttons.get(name)
        elif name == "calculate":
            self.calculate_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
            active_button = self.buttons.get(name)
        elif name == "help":
            self.help_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
            active_button = self.help_button
        elif name == "settings":
            self.settings_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
            active_button = self.settings_button

        # Resaltar el botón activo
        if active_button:
            active_button.configure(fg_color="#1F618D")

    def on_closing(self):
        """Se ejecuta al cerrar la ventana, guardando la configuración."""
        with open("config.ini", "w") as configfile:
            self.config.write(configfile)
        if self.db_manager and self.db_manager.conn:
            self.db_manager.close()
        self.destroy()

    def restart_app(self):
        """Reinicia la aplicación actual."""
        self.on_closing()
        python = sys.executable
        os.execl(python, python, *sys.argv)


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
