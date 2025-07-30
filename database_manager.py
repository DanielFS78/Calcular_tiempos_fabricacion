# =================================================================================
# GESTOR DE LA BASE DE DATOS (database_manager.py)
# =================================================================================
# Este módulo se encarga de toda la interacción con la base de datos SQLite.
# Contiene la clase DatabaseManager con métodos para crear las tablas y
# realizar operaciones CRUD (Crear, Leer, Actualizar, Borrar) sobre los datos
# de productos, subfabricaciones y fabricaciones completas.
# =================================================================================

import sqlite3
import logging


class DatabaseManager:
    """
    Gestiona todas las operaciones de la base de datos SQLite para la aplicación.
    """

    def __init__(self, db_path="montaje.db"):
        """
        Inicializa el gestor y se conecta a la base de datos.
        Crea las tablas si no existen.
        """
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self.create_tables()
            logging.info(f"Conexión exitosa a la base de datos en: {db_path}")
        except sqlite3.Error as e:
            logging.critical(f"CRITICAL: Error al conectar con la base de datos: {e}")
            self.conn = None

    def create_tables(self):
        """Crea las tablas necesarias en la base de datos si no existen previamente."""
        if not self.conn:
            return
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    codigo TEXT PRIMARY KEY,
                    descripcion TEXT NOT NULL,
                    departamento TEXT NOT NULL,
                    tipo_trabajador INTEGER NOT NULL,
                    donde TEXT,
                    tiene_subfabricaciones INTEGER NOT NULL,
                    tiempo_optimo REAL
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS subfabricaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_codigo TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    tiempo REAL NOT NULL,
                    tipo_trabajador INTEGER NOT NULL,
                    FOREIGN KEY (producto_codigo) REFERENCES productos (codigo) ON DELETE CASCADE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS fabricaciones (
                    codigo TEXT PRIMARY KEY,
                    descripcion TEXT NOT NULL
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS fabricacion_contenido (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fabricacion_codigo TEXT NOT NULL,
                    producto_codigo TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    FOREIGN KEY (fabricacion_codigo) REFERENCES fabricaciones (codigo) ON DELETE CASCADE,
                    FOREIGN KEY (producto_codigo) REFERENCES productos (codigo) ON DELETE CASCADE
                )
            """)
            self.conn.commit()
            logging.info("Tablas de la base de datos verificadas/creadas con éxito.")
        except sqlite3.Error as e:
            logging.error(f"Error al crear las tablas de la BD: {e}")

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self.conn:
            self.conn.close()
            logging.info("Conexión a la base de datos cerrada.")

    def add_product(self, data, subfabricaciones=None):
        """Añade un nuevo producto y sus subfabricaciones si las tiene."""
        if not self.conn: return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            product_sql = """
                          INSERT INTO productos (codigo, descripcion, departamento, tipo_trabajador, donde, \
                                                 tiene_subfabricaciones, tiempo_optimo)
                          VALUES (?, ?, ?, ?, ?, ?, ?) \
                          """
            product_values = (
                data["codigo"], data["descripcion"], data["departamento"], data["tipo_trabajador"],
                data["donde"], data["tiene_subfabricaciones"], data["tiempo_optimo"]
            )
            self.cursor.execute(product_sql, product_values)

            if data["tiene_subfabricaciones"] == 1 and subfabricaciones:
                sub_sql = """
                          INSERT INTO subfabricaciones (producto_codigo, descripcion, tiempo, tipo_trabajador)
                          VALUES (?, ?, ?, ?) \
                          """
                for sub in subfabricaciones:
                    sub_values = (data["codigo"], sub["descripcion"], sub["tiempo"], sub["tipo_trabajador"])
                    self.cursor.execute(sub_sql, sub_values)

            self.conn.commit()
            logging.info(f"Producto '{data['codigo']}' añadido con éxito a la BD.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error de BD al añadir el producto '{data['codigo']}': {e}")
            return False

    def search_products(self, query):
        """Busca productos por código o descripción."""
        if not self.conn: return []
        try:
            sql = "SELECT codigo, descripcion FROM productos WHERE codigo LIKE ? OR descripcion LIKE ?"
            self.cursor.execute(sql, (f"%{query}%", f"%{query}%"))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error de BD al buscar productos con query '{query}': {e}")
            return []

    def get_product_details(self, codigo):
        """Obtiene todos los detalles de un producto por su código."""
        if not self.conn: return None, []
        try:
            self.cursor.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,))
            producto_data = self.cursor.fetchone()
            if not producto_data: return None, []

            self.cursor.execute("SELECT * FROM subfabricaciones WHERE producto_codigo = ?", (codigo,))
            subfabricaciones_data = self.cursor.fetchall()
            return producto_data, subfabricaciones_data
        except sqlite3.Error as e:
            logging.error(f"Error de BD al obtener detalles del producto '{codigo}': {e}")
            return None, []

    def update_product(self, codigo_original, data, subfabricaciones=None):
        """Actualiza un producto existente y sus subfabricaciones."""
        if not self.conn: return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            sql_update = """
                         UPDATE productos \
                         SET codigo                 = ?, \
                             descripcion            = ?, \
                             departamento           = ?, \
                             tipo_trabajador        = ?, \
                             donde                  = ?, \
                             tiene_subfabricaciones = ?, \
                             tiempo_optimo          = ?
                         WHERE codigo = ? \
                         """
            update_values = (
                data["codigo"], data["descripcion"], data["departamento"], data["tipo_trabajador"],
                data["donde"], data["tiene_subfabricaciones"], data["tiempo_optimo"], codigo_original
            )
            self.cursor.execute(sql_update, update_values)

            self.cursor.execute("DELETE FROM subfabricaciones WHERE producto_codigo = ?", (codigo_original,))

            if data["tiene_subfabricaciones"] == 1 and subfabricaciones:
                sub_sql = """
                          INSERT INTO subfabricaciones (producto_codigo, descripcion, tiempo, tipo_trabajador)
                          VALUES (?, ?, ?, ?) \
                          """
                for sub in subfabricaciones:
                    self.cursor.execute(sub_sql,
                                        (data["codigo"], sub["descripcion"], sub["tiempo"], sub["tipo_trabajador"]))

            self.conn.commit()
            logging.info(f"Producto '{codigo_original}' actualizado a '{data['codigo']}' con éxito.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error de BD al actualizar el producto '{codigo_original}': {e}")
            return False

    def delete_product(self, codigo):
        """Elimina un producto de la base de datos."""
        if not self.conn: return False
        try:
            self.cursor.execute("DELETE FROM productos WHERE codigo = ?", (codigo,))
            self.conn.commit()
            logging.info(f"Producto '{codigo}' eliminado con éxito de la BD.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error de BD al eliminar el producto '{codigo}': {e}")
            return False

    def add_fabricacion(self, codigo, descripcion, contenido):
        """Añade una nueva fabricación y su contenido a la base de datos."""
        if not self.conn: return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            self.cursor.execute("INSERT INTO fabricaciones (codigo, descripcion) VALUES (?, ?)", (codigo, descripcion))
            sql_contenido = "INSERT INTO fabricacion_contenido (fabricacion_codigo, producto_codigo, cantidad) VALUES (?, ?, ?)"
            for item in contenido:
                self.cursor.execute(sql_contenido, (codigo, item["producto_codigo"], item["cantidad"]))
            self.conn.commit()
            logging.info(f"Fabricación '{codigo}' añadida con éxito a la BD.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error de BD al añadir la fabricación '{codigo}': {e}")
            return False

    def search_fabricaciones(self, query):
        """Busca fabricaciones por código o descripción."""
        if not self.conn: return []
        try:
            sql = "SELECT codigo, descripcion FROM fabricaciones WHERE codigo LIKE ? OR descripcion LIKE ?"
            self.cursor.execute(sql, (f"%{query}%", f"%{query}%"))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error de BD al buscar fabricaciones con query '{query}': {e}")
            return []

    def get_fabricacion_details(self, codigo):
        """Obtiene los detalles y el contenido de una fabricación."""
        if not self.conn: return None, []
        try:
            self.cursor.execute("SELECT * FROM fabricaciones WHERE codigo = ?", (codigo,))
            fab_data = self.cursor.fetchone()
            if not fab_data: return None, []

            sql = """
                  SELECT fc.producto_codigo, p.descripcion, fc.cantidad
                  FROM fabricacion_contenido fc
                           JOIN productos p ON fc.producto_codigo = p.codigo
                  WHERE fc.fabricacion_codigo = ? \
                  """
            self.cursor.execute(sql, (codigo,))
            contenido_data = self.cursor.fetchall()
            return fab_data, contenido_data
        except sqlite3.Error as e:
            logging.error(f"Error de BD al obtener detalles de la fabricación '{codigo}': {e}")
            return None, []

    def update_fabricacion(self, codigo_original, data, contenido):
        """Actualiza una fabricación existente y su contenido."""
        if not self.conn: return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            sql_update = "UPDATE fabricaciones SET codigo = ?, descripcion = ? WHERE codigo = ?"
            self.cursor.execute(sql_update, (data["codigo"], data["descripcion"], codigo_original))
            self.cursor.execute("DELETE FROM fabricacion_contenido WHERE fabricacion_codigo = ?", (codigo_original,))
            sql_contenido = "INSERT INTO fabricacion_contenido (fabricacion_codigo, producto_codigo, cantidad) VALUES (?, ?, ?)"
            for item in contenido:
                self.cursor.execute(sql_contenido, (data["codigo"], item["producto_codigo"], item["cantidad"]))
            self.conn.commit()
            logging.info(f"Fabricación '{codigo_original}' actualizada a '{data['codigo']}' con éxito.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Error de BD al actualizar la fabricación '{codigo_original}': {e}")
            return False

    def delete_fabricacion(self, codigo):
        """Elimina una fabricación de la base de datos."""
        if not self.conn: return False
        try:
            self.cursor.execute("DELETE FROM fabricaciones WHERE codigo = ?", (codigo,))
            self.conn.commit()
            logging.info(f"Fabricación '{codigo}' eliminada con éxito de la BD.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error de BD al eliminar la fabricación '{codigo}': {e}")
            return False

    def get_data_for_calculation(self, fabricacion_codigo):
        """Recopila todos los datos necesarios para el cálculo de tiempos de una fabricación."""
        if not self.conn: return []
        try:
            self.cursor.execute(
                "SELECT producto_codigo, cantidad FROM fabricacion_contenido WHERE fabricacion_codigo = ?",
                (fabricacion_codigo,))
            contenido = self.cursor.fetchall()
            calculation_data = []
            for prod_codigo, cantidad in contenido:
                self.cursor.execute("SELECT * FROM productos WHERE codigo = ?", (prod_codigo,))
                prod_details = self.cursor.fetchone()
                if not prod_details: continue

                prod_dict = {
                    "codigo": prod_details[0], "descripcion": prod_details[1], "departamento": prod_details[2],
                    "tipo_trabajador": prod_details[3], "donde": prod_details[4],
                    "tiene_subfabricaciones": prod_details[5],
                    "tiempo_optimo": prod_details[6], "cantidad_en_kit": cantidad, "sub_partes": []
                }
                if prod_dict["tiene_subfabricaciones"] == 1:
                    self.cursor.execute(
                        "SELECT descripcion, tiempo, tipo_trabajador FROM subfabricaciones WHERE producto_codigo = ?",
                        (prod_codigo,))
                    sub_partes_raw = self.cursor.fetchall()
                    for sub_raw in sub_partes_raw:
                        prod_dict["sub_partes"].append(
                            {"descripcion": sub_raw[0], "tiempo": sub_raw[1], "tipo_trabajador": sub_raw[2]})
                calculation_data.append(prod_dict)
            return calculation_data
        except sqlite3.Error as e:
            logging.error(f"Error de BD al recopilar datos para el cálculo de '{fabricacion_codigo}': {e}")
            return []

# --- Bloque de prueba ---
if __name__ == "__main__":
    # Este bloque solo se ejecuta si corres 'python database_manager.py' directamente.
    # Es útil para probar que la clase funciona.
    print("Iniciando prueba del DatabaseManager...")
    db = DatabaseManager(
        "montaje_test.db"
    )  # Usa una BD de prueba para no ensuciar la real

    # Prueba de añadir producto simple
    producto_simple = {
        "codigo": "TOR-001",
        "descripcion": "Tornillo M5x20",
        "departamento": "Mecánica",
        "tipo_trabajador": 1,
        "donde": "Caja 5, Estante A",
        "tiene_subfabricaciones": 0,
        "tiempo_optimo": 0.5,  # 30 segundos
    }
    db.add_product(producto_simple)

    # Prueba de añadir producto complejo
    subfabricaciones_cpu = [
        {"descripcion": "Inspección visual PCB", "tiempo": 2, "tipo_trabajador": 2},
        {"descripcion": "Montaje disipador", "tiempo": 5, "tipo_trabajador": 1},
        {"descripcion": "Test de arranque", "tiempo": 3, "tipo_trabajador": 3},
    ]
    tiempo_total_cpu = sum(s["tiempo"] for s in subfabricaciones_cpu)

    producto_complejo = {
        "codigo": "CPU-01",
        "descripcion": "Unidad de Control Principal",
        "departamento": "Electrónica",
        "tipo_trabajador": 3,
        "donde": "Sala limpia",
        "tiene_subfabricaciones": 1,
        "tiempo_optimo": tiempo_total_cpu,
    }
    db.add_product(producto_complejo, subfabricaciones_cpu)

    # Prueba de búsqueda
    resultados = db.search_products("TOR")
    print(f"Resultados de búsqueda para 'TOR': {resultados}")

    resultados = db.search_products("Unidad")
    print(f"Resultados de búsqueda para 'Unidad': {resultados}")

    db.close()
    print("Prueba finalizada.")
