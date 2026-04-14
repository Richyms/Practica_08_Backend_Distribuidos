import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from zeep import Client
import threading

CATEGORIAS_GEEK = [
    "Lego", "Figuras de Anime (Scale)", "Funkos", "Gunpla (Modelos Armables)", 
    "Nendoroids", "TCG Pokemon", "TCG Yu-Gi-Oh!", "TCG Magic The Gathering",
    "Albumes Kpop", "Lightsticks Oficiales", "Photocards de Coleccion",
    "Mangas y Manhwas", "Perifericos Gamer (Teclados/Mouse)",
    "Videojuegos Fisicos", "Consolas Retro", "Juegos de Mesa", 
    "Ropa y Cosplay", "Peluches y Mascotas"
]

WSDL_URL = 'http://127.0.0.1:8000/?wsdl'

class ClienteTiendaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Punto de Venta - Tienda Geek & K-Pop (Cliente SOAP)")
        self.root.geometry("650x450")
        self.root.configure(bg="#f4f4f9")
        self.cliente_wsdl = None
        self.crear_interfaz()

    def crear_interfaz(self):
        frame_form = tk.LabelFrame(self.root, text="Detalles del Artículo", bg="#f4f4f9", font=("Arial", 10, "bold"), pady=10, padx=10)
        frame_form.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(frame_form, text="Categoría:", bg="#f4f4f9").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.combo_categoria = ttk.Combobox(frame_form, values=CATEGORIAS_GEEK, width=35, state="readonly")
        self.combo_categoria.set("Selecciona un artículo...")
        self.combo_categoria.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(frame_form, text="Precio Base ($):", bg="#f4f4f9").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_precio = tk.Entry(frame_form, width=15)
        self.entry_precio.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)

        tk.Label(frame_form, text="Operación:", bg="#f4f4f9").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.var_operacion = tk.StringVar(value="ahorro")
        
        frame_radios = tk.Frame(frame_form, bg="#f4f4f9")
        frame_radios.grid(row=2, column=1, sticky=tk.W, padx=10)
        tk.Radiobutton(frame_radios, text="Calcular Ahorro/Descuento", variable=self.var_operacion, value="ahorro", bg="#f4f4f9").pack(side=tk.LEFT)
        tk.Radiobutton(frame_radios, text="Calcular Costo de Envío", variable=self.var_operacion, value="envio", bg="#f4f4f9").pack(side=tk.LEFT, padx=10)

        btn_procesar = tk.Button(frame_form, text="Conectar y Calcular", command=self.iniciar_peticion, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        btn_procesar.grid(row=3, column=0, columnspan=2, pady=15)

        tk.Label(self.root, text="Recibo del Servidor:", bg="#f4f4f9", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=15)
        self.consola = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=10, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00")
        self.consola.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self.imprimir_consola("Bienvenido al sistema cliente. Esperando peticiones...\n")

    def imprimir_consola(self, mensaje):
        self.consola.insert(tk.END, mensaje + "\n")
        self.consola.yview(tk.END)

    def iniciar_peticion(self):
        categoria = self.combo_categoria.get()
        precio_texto = self.entry_precio.get()

        if categoria == "Selecciona un artículo...":
            messagebox.showwarning("Faltan datos", "Por favor, selecciona una categoría del catálogo.")
            return
        
        try:
            precio = float(precio_texto)
        except ValueError:
            messagebox.showwarning("Error de formato", "El precio debe ser un número válido.")
            return

        operacion = self.var_operacion.get()
        
        self.imprimir_consola("-" * 50)
        self.imprimir_consola("Enviando petición SOAP...")
        self.imprimir_consola(f"-> Artículo: {categoria} | Precio: ${precio} | Op: {operacion}")
        
        threading.Thread(target=self._hilo_comunicacion, args=(categoria, precio, operacion)).start()

    def _hilo_comunicacion(self, categoria, precio, operacion):
        try:
            if self.cliente_wsdl is None:
                self.root.after(0, self.imprimir_consola, "Descargando contrato WSDL del servidor...")
                self.cliente_wsdl = Client(WSDL_URL)

            if operacion == "ahorro":
                respuesta = self.cliente_wsdl.service.calcular_ahorro(categoria, precio)
            else:
                respuesta = self.cliente_wsdl.service.calcular_envio(categoria, precio)

            mensaje_exito = f"RESPUESTA DEL SERVIDOR:\n   {respuesta}"
            self.root.after(0, self.imprimir_consola, mensaje_exito)

        except Exception as e:
            error_msg = f"ERROR DE RED: No se pudo conectar al servidor SOAP.\nDetalle: {str(e)}"
            self.root.after(0, self.imprimir_consola, error_msg)
            self.cliente_wsdl = None

if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteTiendaGUI(root)
    root.mainloop()