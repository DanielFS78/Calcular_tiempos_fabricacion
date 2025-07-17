# =================================================================================
# GESTOR DE LA BASE DE DATOS (database_manager.py)
# =================================================================================
# Este módulo se encarga de toda la interacción con la base de datos SQLite.
# Contiene la clase DatabaseManager con métodos para crear las tablas y
# realizar operaciones CRUD (Crear, Leer, Actualizar, Borrar) sobre los datos
# de productos, subfabricaciones y fabricaciones completas.
# =================================================================================

import sqlite3
import pandas as pd


class DatabaseManager:
    """
    Gestiona todas las operaciones de la base de datos SQLite para la aplicación.
    """

    def __init__(self, db_path="montaje.db"):
        """
        Inicializa el gestor y se conecta a la base de datos.
        Crea las tablas si no existen.

        :param db_path: Ruta al archivo de la base de datos SQLite.
        """
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self.create_tables()
            print(f"Conexión exitosa a la base de datos en: {db_path}")
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos: {e}")
            self.conn = None

    def create_tables(self):
        """
        Crea las tablas necesarias en la base de datos si no existen previamente.
        - productos: Almacena cada producto individual con sus datos principales.
        - subfabricaciones: Almacena las partes o pasos de un producto complejo.
        - fabricaciones: Define un "kit" o fabricación completa que agrupa varios productos.
        - fabricacion_contenido: Tabla de unión para relacionar fabricaciones con sus productos y cantidades.
        """
        if not self.conn:
            return

        try:
            # Tabla de Productos
            self.cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS productos (
                codigo TEXT PRIMARY KEY,
                descripcion TEXT NOT NULL,
                departamento TEXT NOT NULL, -- 'Mecánica', 'Electrónica', 'Montaje'
                tipo_trabajador INTEGER NOT NULL, -- 1, 2, 3
                donde TEXT,
                tiene_subfabricaciones INTEGER NOT NULL, -- 0 para No, 1 para Sí
                tiempo_optimo REAL -- Tiempo total en minutos
            )"""
            )

            # Tabla de Sub-fabricaciones
            self.cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS subfabricaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_codigo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                tiempo REAL NOT NULL,
                tipo_trabajador INTEGER NOT NULL,
                FOREIGN KEY (producto_codigo) REFERENCES productos (codigo) ON DELETE CASCADE
            )"""
            )

            # Tabla de Fabricaciones (Kits de productos)
            self.cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS fabricaciones (
                codigo TEXT PRIMARY KEY,
                descripcion TEXT NOT NULL
            )"""
            )

            # Tabla de Contenido de Fabricaciones (qué productos y en qué cantidad)
            self.cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS fabricacion_contenido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fabricacion_codigo TEXT NOT NULL,
                producto_codigo TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                FOREIGN KEY (fabricacion_codigo) REFERENCES fabricaciones (codigo) ON DELETE CASCADE,
                FOREIGN KEY (producto_codigo) REFERENCES productos (codigo) ON DELETE CASCADE
            )"""
            )

            self.conn.commit()
            print("Tablas creadas o ya existentes.")
        except sqlite3.Error as e:
            print(f"Error al crear las tablas: {e}")

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")

    # --- Métodos para Productos y Subfabricaciones ---

    def add_product(self, data, subfabricaciones=None):
        """
        Añade un nuevo producto y sus subfabricaciones si las tiene.
        Utiliza una transacción para asegurar la integridad de los datos.
        """
        if not self.conn:
            return
        try:
            # Iniciar transacción
            self.cursor.execute("BEGIN TRANSACTION")

            # Insertar el producto principal
            product_sql = """INSERT INTO productos (codigo, descripcion, departamento, tipo_trabajador, donde, tiene_subfabricaciones, tiempo_optimo)
                             VALUES (?, ?, ?, ?, ?, ?, ?)"""
            self.cursor.execute(
                product_sql,
                (
                    data["codigo"],
                    data["descripcion"],
                    data["departamento"],
                    data["tipo_trabajador"],
                    data["donde"],
                    data["tiene_subfabricaciones"],
                    data["tiempo_optimo"],
                ),
            )

            # Si hay subfabricaciones, insertarlas
            if data["tiene_subfabricaciones"] == 1 and subfabricaciones:
                sub_sql = """INSERT INTO subfabricaciones (producto_codigo, descripcion, tiempo, tipo_trabajador)
                             VALUES (?, ?, ?, ?)"""
                for sub in subfabricaciones:
                    self.cursor.execute(
                        sub_sql,
                        (
                            data["codigo"],
                            sub["descripcion"],
                            sub["tiempo"],
                            sub["tipo_trabajador"],
                        ),
                    )

            # Confirmar transacción
            self.conn.commit()
            print(f"Producto {data['codigo']} añadido con éxito.")
            return True
        except sqlite3.Error as e:
            # Revertir cambios si hay un error
            self.conn.rollback()
            print(f"Error al añadir el producto {data['codigo']}: {e}")
            return False

    def search_products(self, query):
        """Busca productos por código o descripción."""
        if not self.conn:
            return []
        try:
            sql = "SELECT codigo, descripcion FROM productos WHERE codigo LIKE ? OR descripcion LIKE ?"
            self.cursor.execute(sql, (f"%{query}%", f"%{query}%"))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error al buscar productos: {e}")
            return []

    def get_product_details(self, codigo):
        """Obtiene todos los detalles de un producto por su código."""
        if not self.conn:
            return None, []
        try:
            # Obtener datos del producto principal
            self.cursor.execute("SELECT * FROM productos WHERE codigo = ?", (codigo,))
            producto_data = self.cursor.fetchone()
            if not producto_data:
                return None, []

            # Obtener subfabricaciones si existen
            self.cursor.execute(
                "SELECT * FROM subfabricaciones WHERE producto_codigo = ?", (codigo,)
            )
            subfabricaciones_data = self.cursor.fetchall()

            return producto_data, subfabricaciones_data
        except sqlite3.Error as e:
            print(f"Error al obtener detalles del producto {codigo}: {e}")
            return None, []

    def update_product(self, codigo_original, data, subfabricaciones=None):
        """Actualiza un producto existente y sus subfabricaciones."""
        if not self.conn:
            return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")

            # Actualizar el producto principal
            sql_update = """UPDATE productos SET 
                            codigo = ?, descripcion = ?, departamento = ?, tipo_trabajador = ?, 
                            donde = ?, tiene_subfabricaciones = ?, tiempo_optimo = ?
                            WHERE codigo = ?"""
            self.cursor.execute(
                sql_update,
                (
                    data["codigo"],
                    data["descripcion"],
                    data["departamento"],
                    data["tipo_trabajador"],
                    data["donde"],
                    data["tiene_subfabricaciones"],
                    data["tiempo_optimo"],
                    codigo_original,
                ),
            )

            # Borrar subfabricaciones antiguas y añadir las nuevas
            self.cursor.execute(
                "DELETE FROM subfabricaciones WHERE producto_codigo = ?",
                (codigo_original,),
            )

            if data["tiene_subfabricaciones"] == 1 and subfabricaciones:
                sub_sql = """INSERT INTO subfabricaciones (producto_codigo, descripcion, tiempo, tipo_trabajador)
                             VALUES (?, ?, ?, ?)"""
                for sub in subfabricaciones:
                    self.cursor.execute(
                        sub_sql,
                        (
                            data["codigo"],
                            sub["descripcion"],
                            sub["tiempo"],
                            sub["tipo_trabajador"],
                        ),
                    )

            self.conn.commit()
            print(f"Producto {data['codigo']} actualizado con éxito.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error al actualizar el producto {codigo_original}: {e}")
            return False

    def delete_product(self, codigo):
        """Elimina un producto de la base de datos (ON DELETE CASCADE se encarga de las subfabricaciones)."""
        if not self.conn:
            return False
        try:
            self.cursor.execute("DELETE FROM productos WHERE codigo = ?", (codigo,))
            self.conn.commit()
            print(f"Producto {codigo} eliminado con éxito.")
            return True
        except sqlite3.Error as e:
            print(f"Error al eliminar el producto {codigo}: {e}")
            return False

    # --- Métodos para Fabricaciones ---

    def add_fabricacion(self, codigo, descripcion, contenido):
        """
        Añade una nueva fabricación y su contenido a la base de datos.
        Usa una transacción para asegurar la integridad.

        :param codigo: Código de la fabricación.
        :param descripcion: Descripción de la fabricación.
        :param contenido: Una lista de diccionarios, ej: [{'producto_codigo': 'P-001', 'cantidad': 5}, ...]
        """
        if not self.conn:
            return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")

            # Insertar la fabricación principal
            self.cursor.execute(
                "INSERT INTO fabricaciones (codigo, descripcion) VALUES (?, ?)",
                (codigo, descripcion),
            )

            # Insertar el contenido
            sql_contenido = "INSERT INTO fabricacion_contenido (fabricacion_codigo, producto_codigo, cantidad) VALUES (?, ?, ?)"
            for item in contenido:
                self.cursor.execute(
                    sql_contenido, (codigo, item["producto_codigo"], item["cantidad"])
                )

            self.conn.commit()
            print(f"Fabricación {codigo} añadida con éxito.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error al añadir la fabricación {codigo}: {e}")
            return False

    def search_fabricaciones(self, query):
        """Busca fabricaciones por código o descripción."""
        if not self.conn:
            return []
        try:
            sql = "SELECT codigo, descripcion FROM fabricaciones WHERE codigo LIKE ? OR descripcion LIKE ?"
            self.cursor.execute(sql, (f"%{query}%", f"%{query}%"))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error al buscar fabricaciones: {e}")
            return []

    def get_fabricacion_details(self, codigo):
        """Obtiene los detalles y el contenido de una fabricación."""
        if not self.conn:
            return None, []
        try:
            # Obtener datos de la fabricación principal
            self.cursor.execute(
                "SELECT * FROM fabricaciones WHERE codigo = ?", (codigo,)
            )
            fab_data = self.cursor.fetchone()
            if not fab_data:
                return None, []

            # Obtener contenido (productos y cantidades)
            sql = """
            SELECT fc.producto_codigo, p.descripcion, fc.cantidad 
            FROM fabricacion_contenido fc
            JOIN productos p ON fc.producto_codigo = p.codigo
            WHERE fc.fabricacion_codigo = ?
            """
            self.cursor.execute(sql, (codigo,))
            contenido_data = self.cursor.fetchall()
            return fab_data, contenido_data
        except sqlite3.Error as e:
            print(f"Error al obtener detalles de la fabricación {codigo}: {e}")
            return None, []

    def update_fabricacion(self, codigo_original, data, contenido):
        """Actualiza una fabricación existente y su contenido."""
        if not self.conn:
            return False
        try:
            self.cursor.execute("BEGIN TRANSACTION")

            # Actualizar fabricación principal
            sql_update = (
                "UPDATE fabricaciones SET codigo = ?, descripcion = ? WHERE codigo = ?"
            )
            self.cursor.execute(
                sql_update, (data["codigo"], data["descripcion"], codigo_original)
            )

            # Borrar contenido antiguo y añadir el nuevo
            self.cursor.execute(
                "DELETE FROM fabricacion_contenido WHERE fabricacion_codigo = ?",
                (codigo_original,),
            )

            sql_contenido = "INSERT INTO fabricacion_contenido (fabricacion_codigo, producto_codigo, cantidad) VALUES (?, ?, ?)"
            for item in contenido:
                self.cursor.execute(
                    sql_contenido,
                    (data["codigo"], item["producto_codigo"], item["cantidad"]),
                )

            self.conn.commit()
            print(f"Fabricación {data['codigo']} actualizada con éxito.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error al actualizar la fabricación {codigo_original}: {e}")
            return False

    def delete_fabricacion(self, codigo):
        """Elimina una fabricación de la base de datos."""
        if not self.conn:
            return False
        try:
            self.cursor.execute("DELETE FROM fabricaciones WHERE codigo = ?", (codigo,))
            self.conn.commit()
            print(f"Fabricación {codigo} eliminada con éxito.")
            return True
        except sqlite3.Error as e:
            print(f"Error al eliminar la fabricación {codigo}: {e}")
            return False

    def get_data_for_calculation(self, fabricacion_codigo):
        """
        Recopila todos los datos necesarios para el cálculo de tiempos de una fabricación.
        Devuelve una lista de diccionarios, donde cada diccionario es un producto
        del ensamblaje con todos sus detalles y sub-partes.
        """
        if not self.conn:
            return []

        # Primero, obtenemos los productos y cantidades de la fabricación
        fab_contenido_sql = """
        SELECT producto_codigo, cantidad FROM fabricacion_contenido WHERE fabricacion_codigo = ?
        """
        self.cursor.execute(fab_contenido_sql, (fabricacion_codigo,))
        contenido = self.cursor.fetchall()

        calculation_data = []
        for prod_codigo, cantidad in contenido:
            # Para cada producto, obtenemos sus detalles completos
            producto_sql = "SELECT * FROM productos WHERE codigo = ?"
            self.cursor.execute(producto_sql, (prod_codigo,))
            prod_details = self.cursor.fetchone()

            if not prod_details:
                continue

            prod_dict = {
                "codigo": prod_details[0],
                "descripcion": prod_details[1],
                "departamento": prod_details[2],
                "tipo_trabajador": prod_details[3],
                "tiene_subfabricaciones": prod_details[5],
                "tiempo_optimo": prod_details[6],
                "cantidad_en_kit": cantidad,
                "sub_partes": [],
            }

            # Si tiene subfabricaciones, las obtenemos también
            if prod_dict["tiene_subfabricaciones"] == 1:
                sub_sql = "SELECT descripcion, tiempo, tipo_trabajador FROM subfabricaciones WHERE producto_codigo = ?"
                self.cursor.execute(sub_sql, (prod_codigo,))
                sub_partes_raw = self.cursor.fetchall()
                for sub in sub_partes_raw:
                    prod_dict["sub_partes"].append(
                        {
                            "descripcion": sub[0],
                            "tiempo": sub[1],
                            "tipo_trabajador": sub[2],
                        }
                    )

            calculation_data.append(prod_dict)

        return calculation_data


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
