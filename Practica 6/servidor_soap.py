from spyne import Application, rpc, ServiceBase, Unicode, Float
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server

class CalculadoraFintech(ServiceBase):
    
    @rpc(Unicode, Float, _returns=Unicode)
    def calcular_ahorro(ctx, categoria, precio):
        porcentajes = {
            "Lego": 15.0, "Figuras de Anime (Scale)": 15.0, "Funkos": 10.0,
            "Gunpla (Modelos Armables)": 20.0, "Nendoroids": 12.0,
            "TCG Pokemon": 30.0, "TCG Yu-Gi-Oh!": 25.0, "TCG Magic The Gathering": 20.0,
            "Albumes Kpop": 25.0, "Lightsticks Oficiales": 15.0, "Photocards de Coleccion": 35.0,
            "Mangas y Manhwas": 10.0, "Perifericos Gamer (Teclados/Mouse)": 15.0,
            "Videojuegos Fisicos": 10.0, "Consolas Retro": 20.0,
            "Juegos de Mesa": 18.0, "Ropa y Cosplay": 25.0, "Peluches y Mascotas": 30.0
        }
        
        porcentaje = porcentajes.get(categoria, 0.0)
        if porcentaje == 0.0:
            return f"Error: La categoría '{categoria}' no existe en nuestro catálogo geek."
            
        extra = precio * (porcentaje / 100.0)
        return f"Ahorro ({porcentaje}%): ${round(extra, 2)}"

    @rpc(Unicode, Float, _returns=Unicode)
    def calcular_envio(ctx, categoria, precio):
        tarifas = {
            "Lego": 150.0, "Figuras de Anime (Scale)": 200.0, "Lightsticks Oficiales": 120.0,
            "Gunpla (Modelos Armables)": 130.0, "Consolas Retro": 250.0,
            "Albumes Kpop": 100.0, "Funkos": 80.0, "Nendoroids": 90.0,
            "Perifericos Gamer (Teclados/Mouse)": 110.0, "Juegos de Mesa": 140.0,
            "Ropa y Cosplay": 90.0, "Peluches y Mascotas": 85.0,
            "TCG Pokemon": 50.0, "TCG Yu-Gi-Oh!": 50.0, "TCG Magic The Gathering": 50.0,
            "Videojuegos Fisicos": 60.0, "Mangas y Manhwas": 45.0, "Photocards de Coleccion": 30.0
        }
        
        extra = tarifas.get(categoria, -1.0) 
        if extra == -1.0:
            return f"Error: No podemos calcular el envío. '{categoria}' no está registrada."
            
        return f"Envio fijo (por volumen/fragilidad): ${round(extra, 2)}"

app = Application([CalculadoraFintech], 
                  tns='mx.escom.distribuidos.calculadora',
                  in_protocol=Soap11(validator='lxml'),
                  out_protocol=Soap11())

wsgi_app = WsgiApplication(app)

if __name__ == '__main__':
    puerto = 8000
    print(f"Servidor de Servicios Web (SOAP) iniciado en el puerto {puerto}.")
    print(f"El documento WSDL está disponible en: http://127.0.0.1:{puerto}/?wsdl")
    print("Esperando peticiones de clientes...")
    
    server = make_server('127.0.0.1', puerto, wsgi_app)
    server.serve_forever()