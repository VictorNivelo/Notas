import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QMenu,
    QAction,
    QLabel,
    QLineEdit,
    QColorDialog,
    QFontDialog,
    QFileDialog,
    QShortcut,
    QCalendarWidget,
    QDialog,
    QTabWidget,
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon, QTextCharFormat, QColor, QKeySequence
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtWidgets import QStyle
from PyQt5.QtCore import QSize


class TagDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Etiquetas")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Nueva etiqueta...")
        self.tag_list = QListWidget()
        add_button = QPushButton("Agregar")
        remove_button = QPushButton("Eliminar")
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        layout.addWidget(self.tag_input)
        layout.addLayout(button_layout)
        layout.addWidget(self.tag_list)
        add_button.clicked.connect(self.add_tag)
        remove_button.clicked.connect(self.remove_tag)

    def add_tag(self):
        tag = self.tag_input.text().strip()
        if tag and not self.tag_list.findItems(tag, Qt.MatchExactly):
            self.tag_list.addItem(tag)
            self.tag_input.clear()

    def remove_tag(self):
        current_item = self.tag_list.currentItem()
        if current_item:
            self.tag_list.takeItem(self.tag_list.row(current_item))

    def get_tags(self):
        return [self.tag_list.item(i).text() for i in range(self.tag_list.count())]


class AppNotas(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notas")
        self.setMinimumSize(1000, 700)
        self.notas = {}
        self.nota_actual = None
        self.timer_autoguardado = QTimer()
        self.timer_autoguardado.timeout.connect(self.autoguardar)
        self.timer_autoguardado.start(30000)
        self.setup_ui()
        self.cargar_notas()
        self.setup_shortcuts()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.nueva_nota)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.guardar_notas)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            self.barra_busqueda.setFocus
        )
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.imprimir_nota)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.exportar_nota)

    def setup_ui(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout = QHBoxLayout(widget_central)
        panel_izquierdo = QWidget()
        layout_izquierdo = QVBoxLayout(panel_izquierdo)
        self.barra_busqueda = QLineEdit()
        self.barra_busqueda.setPlaceholderText("Buscar notas")
        self.barra_busqueda.textChanged.connect(self.buscar_notas)
        layout_izquierdo.addWidget(self.barra_busqueda)
        self.lista_notas = QListWidget()
        self.lista_notas.itemClicked.connect(self.cargar_nota)
        self.lista_notas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista_notas.customContextMenuRequested.connect(
            self.mostrar_menu_contextual
        )
        layout_izquierdo.addWidget(self.lista_notas)
        layout_botones = QHBoxLayout()
        boton_nueva = QPushButton("Nueva Nota")
        boton_nueva.clicked.connect(self.nueva_nota)
        boton_eliminar = QPushButton("Eliminar Nota")
        boton_eliminar.clicked.connect(self.eliminar_nota)
        boton_tags = QPushButton("Etiquetas")
        boton_tags.clicked.connect(self.gestionar_etiquetas)
        layout_botones.addWidget(boton_nueva)
        layout_botones.addWidget(boton_eliminar)
        layout_botones.addWidget(boton_tags)
        layout_izquierdo.addLayout(layout_botones)
        layout.addWidget(panel_izquierdo, 1)
        panel_derecho = QTabWidget()
        tab_editor = QWidget()
        layout_editor = QVBoxLayout(tab_editor)
        self.titulo_nota = QLineEdit()
        self.titulo_nota.setPlaceholderText("Título de la nota")
        self.titulo_nota.textChanged.connect(self.actualizar_titulo)
        layout_editor.addWidget(self.titulo_nota)
        barra_formato = QHBoxLayout()
        formatos = [
            ("bold", "Negrita (Ctrl+B)", "Negrita"),
            ("italic", "Cursiva (Ctrl+I)", "Cursiva"),
            ("underline", "Subrayado (Ctrl+U)", "Subrayado"),
        ]
        for formato, tooltip, texto in formatos:
            boton = QPushButton(texto)
            boton.setProperty("formato", formato)
            boton.setToolTip(tooltip)
            boton.clicked.connect(self.aplicar_formato)
            barra_formato.addWidget(boton)
        boton_color = QPushButton("Color")
        boton_color.clicked.connect(self.cambiar_color_texto)
        boton_fuente = QPushButton("Fuente")
        boton_fuente.clicked.connect(self.cambiar_fuente)
        barra_formato.addWidget(boton_color)
        barra_formato.addWidget(boton_fuente)
        layout_editor.addLayout(barra_formato)
        self.editor = QTextEdit()
        self.editor.textChanged.connect(self.activar_autoguardado)
        layout_editor.addWidget(self.editor)
        panel_derecho.addTab(tab_editor, "Editor")
        calendario = QCalendarWidget()
        calendario.clicked.connect(self.fecha_seleccionada)
        panel_derecho.addTab(calendario, "Calendario")
        layout.addWidget(panel_derecho, 2)
        self.barra_estado = QLabel()
        self.statusBar().addWidget(self.barra_estado)
        self.setup_menu()

    def setup_menu(self):
        barra_menu = self.menuBar()
        menu_archivo = barra_menu.addMenu("Archivo")
        accion_nueva = QAction("Nueva Nota", self)
        accion_nueva.setShortcut("Ctrl+N")
        accion_nueva.triggered.connect(self.nueva_nota)
        accion_guardar = QAction("Guardar", self)
        accion_guardar.setShortcut("Ctrl+S")
        accion_guardar.triggered.connect(self.guardar_notas)
        accion_imprimir = QAction("Imprimir", self)
        accion_imprimir.setShortcut("Ctrl+P")
        accion_imprimir.triggered.connect(self.imprimir_nota)
        accion_exportar = QAction("Exportar", self)
        accion_exportar.setShortcut("Ctrl+E")
        accion_exportar.triggered.connect(self.exportar_nota)
        menu_archivo.addAction(accion_nueva)
        menu_archivo.addAction(accion_guardar)
        menu_archivo.addAction(accion_imprimir)
        menu_archivo.addAction(accion_exportar)

    def gestionar_etiquetas(self):
        if not self.nota_actual:
            QMessageBox.warning(self, "Advertencia", "Selecciona una nota primero")
            return
        dialog = TagDialog(self)
        if self.notas[self.nota_actual].get("tags"):
            for tag in self.notas[self.nota_actual]["tags"]:
                dialog.tag_list.addItem(tag)
        if dialog.exec_():
            self.notas[self.nota_actual]["tags"] = dialog.get_tags()
            self.guardar_notas()

    def mostrar_menu_contextual(self, position):
        menu = QMenu()
        accion_exportar = menu.addAction("Exportar nota")
        accion_imprimir = menu.addAction("Imprimir nota")
        accion = menu.exec_(self.lista_notas.mapToGlobal(position))
        if accion == accion_exportar:
            self.exportar_nota()
        elif accion == accion_imprimir:
            self.imprimir_nota()

    def imprimir_nota(self):
        if not self.nota_actual:
            QMessageBox.warning(
                self, "Advertencia", "Selecciona una nota para imprimir"
            )
            return
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            self.editor.print_(printer)

    def exportar_nota(self):
        if not self.nota_actual:
            QMessageBox.warning(
                self, "Advertencia", "Selecciona una nota para exportar"
            )
            return
        nombre_archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Nota",
            "",
            "Archivos HTML (*.html);;Archivos de Texto (*.txt)",
        )
        if nombre_archivo:
            try:
                with open(nombre_archivo, "w", encoding="utf-8") as f:
                    if nombre_archivo.endswith(".html"):
                        f.write(self.editor.toHtml())
                    else:
                        f.write(self.editor.toPlainText())
                QMessageBox.information(self, "Éxito", "Nota exportada correctamente")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error al exportar la nota: {str(e)}"
                )

    def fecha_seleccionada(self, date):
        fecha_str = date.toString("yyyy-MM-dd")
        self.editor.append(f"\nFecha seleccionada: {fecha_str}")

    def cambiar_fuente(self):
        font, ok = QFontDialog.getFont(self.editor.currentFont(), self)
        if ok:
            self.editor.setCurrentFont(font)

    def nueva_nota(self):
        titulo, ok = QInputDialog.getText(self, "Nueva Nota", "Título de la nota:")
        if ok and titulo:
            if titulo in self.notas:
                QMessageBox.warning(self, "Error", "Ya existe una nota con ese título")
                return
            self.notas[titulo] = {
                "contenido": "",
                "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_modificacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tags": [],
            }
            self.actualizar_lista_notas()
            self.cargar_nota_por_titulo(titulo)

    def eliminar_nota(self):
        if self.nota_actual:
            confirmacion = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Estás seguro de que quieres eliminar la nota '{self.nota_actual}'?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirmacion == QMessageBox.Yes:
                del self.notas[self.nota_actual]
                self.nota_actual = None
                self.actualizar_lista_notas()
                self.editor.clear()
                self.titulo_nota.clear()
                self.guardar_notas()

    def actualizar_lista_notas(self):
        self.lista_notas.clear()
        for titulo in sorted(self.notas.keys()):
            self.lista_notas.addItem(titulo)

    def cargar_nota(self, item):
        titulo = item.text()
        self.cargar_nota_por_titulo(titulo)

    def cargar_nota_por_titulo(self, titulo):
        self.nota_actual = titulo
        self.titulo_nota.setText(titulo)
        self.editor.setHtml(self.notas[titulo]["contenido"])
        self.actualizar_barra_estado()

    def actualizar_titulo(self):
        if self.nota_actual and self.nota_actual != self.titulo_nota.text():
            nuevo_titulo = self.titulo_nota.text()
            if nuevo_titulo in self.notas and nuevo_titulo != self.nota_actual:
                self.titulo_nota.setText(self.nota_actual)
                QMessageBox.warning(self, "Error", "Ya existe una nota con ese título")
                return
            self.notas[nuevo_titulo] = self.notas.pop(self.nota_actual)
            self.nota_actual = nuevo_titulo
            self.actualizar_lista_notas()
            self.guardar_notas()

    def activar_autoguardado(self):
        if self.nota_actual:
            self.notas[self.nota_actual]["contenido"] = self.editor.toHtml()
            self.notas[self.nota_actual][
                "fecha_modificacion"
            ] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.actualizar_barra_estado()

    def autoguardar(self):
        if self.nota_actual:
            self.guardar_notas()
            self.barra_estado.setText(
                f"Autoguardado: {datetime.now().strftime('%H:%M:%S')}"
            )

    def actualizar_barra_estado(self):
        if self.nota_actual:
            nota = self.notas[self.nota_actual]
            tags = ", ".join(nota.get("tags", []))
            estado = f"Creada: {nota['fecha_creacion']} | Modificada: {nota['fecha_modificacion']}"
            if tags:
                estado += f" | Etiquetas: {tags}"
            self.barra_estado.setText(estado)

    def aplicar_formato(self):
        formato = self.sender().property("formato")
        if formato == "bold":
            self.editor.setFontWeight(
                QFont.Normal if self.editor.fontWeight() == QFont.Bold else QFont.Bold
            )
        elif formato == "italic":
            self.editor.setFontItalic(not self.editor.fontItalic())
        elif formato == "underline":
            self.editor.setFontUnderline(not self.editor.fontUnderline())

    def cambiar_color_texto(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.editor.setTextColor(color)

    def buscar_notas(self):
        texto_busqueda = self.barra_busqueda.text().lower()
        for i in range(self.lista_notas.count()):
            item = self.lista_notas.item(i)
            titulo = item.text()
            nota = self.notas[titulo]
            tags = nota.get("tags", [])
            contenido = nota["contenido"].lower()
            mostrar = (
                texto_busqueda in titulo.lower()
                or texto_busqueda in contenido
                or any(texto_busqueda in tag.lower() for tag in tags)
            )
            item.setHidden(not mostrar)

    def guardar_notas(self):
        try:
            with open("notas.json", "w", encoding="utf-8") as f:
                json.dump(self.notas, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar las notas: {str(e)}")

    def cargar_notas(self):
        try:
            if os.path.exists("notas.json"):
                with open("notas.json", "r", encoding="utf-8") as f:
                    self.notas = json.load(f)
                self.actualizar_lista_notas()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar las notas: {str(e)}")

    def closeEvent(self, event):
        self.guardar_notas()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    style_sheet = """
    QMainWindow {
        background-color: #f0f0f0;
    }
    QTextEdit {
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 5px;
    }
    QPushButton {
        background-color: #0078d7;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #005a9e;
    }
    QLineEdit {
        padding: 5px;
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    QListWidget {
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    QLabel {
        color: #666;
    }
    """
    app.setStyleSheet(style_sheet)
    ventana = AppNotas()
    ventana.show()
    sys.exit(app.exec_())
