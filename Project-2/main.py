import sys
import io
import os
import json
from datetime import datetime
from PyQt5 import QtWidgets, QtWebEngineWidgets, QtCore
from PyQt5.QtWebChannel import QWebChannel
import folium
from gui import Ui_Form
from pyproj import Transformer
from gds_functions import target

to_2180 = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
to_4326 = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True)

class Bridge(QtCore.QObject):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    @QtCore.pyqtSlot(float, float)
    def receive_coords(self, lat, lng):
        self.parent.process_coords(lat, lng)

class InterfaceWidget(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.active_target = None
        self.lat_start = self.lng_start = self.lat_end = self.lng_end = None

        self.browser = QtWebEngineWidgets.QWebEngineView()
        layout = QtWidgets.QVBoxLayout(self.W_map)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)

        self.bridge = Bridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject('handler', self.bridge)
        self.browser.page().setWebChannel(self.channel)

        self.B_coordStart.clicked.connect(lambda: self.set_active_target("start"))
        self.B_coordEnd.clicked.connect(lambda: self.set_active_target("end"))

        self.B_run.clicked.connect(self.calculate_route)

        self.init_map()
        self.log("Aplikacja gotowa.")

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.changelog.append(f"<b>[{now}]</b> {message}")
        self.changelog.ensureCursorVisible()

    def set_active_target(self, target):
        self.active_target = target
        self.log(f"Kliknij na mapę, aby wybrać: <b>{target.upper()}</b>")

    def process_coords(self, lat, lng):
        """Logika przypisywania współrzędnych do konkretnych pól"""
        lat_s = f"{lat:.6f}"
        lng_s = f"{lng:.6f}"

        if self.active_target == "start":
            self.E_latStart.setText(lat_s)
            self.E_lonStart.setText(lng_s)
            self.lat_start = lat_s
            self.lng_start = lng_s
            self.log(f"Ustawiono współrzędne początkowe.<br>Szerokość geograficzna: <b>{lat_s}</b><br>Długość geograficzna: <b>{lng_s}</b>")
            self.browser.page().runJavaScript(f"window.placeMarker({lat}, {lng}, 'start');")
        if self.active_target == "end":
            self.E_latEnd.setText(lat_s)
            self.E_lonEnd.setText(lng_s)
            self.lat_end = lat_s
            self.lng_end = lng_s
            self.log(f"Ustawiono współrzędne końcowe.<br>Szerokość geograficzna: <b>{lat_s}</b><br>Długość geograficzna: <b>{lng_s}</b>")
            self.browser.page().runJavaScript(f"window.placeMarker({lat}, {lng}, 'end');")

        self.active_target = None

    def calculate_route(self):
        try:
            if not all([self.lat_start, self.lng_start, self.lat_end, self.lng_end]):
                self.log("<span style='color:orange;'>Wybierz oba punkty!</span>")
                return

            sx, sy = to_2180.transform(float(self.lng_start), float(self.lat_start))
            tx, ty = to_2180.transform(float(self.lng_end), float(self.lat_end))

            self.log("Obliczanie trasy...")
            if self.R_astar.isChecked():
                geojson_str = target(sy, sx, ty, tx, dijkstra=False)
            elif self.R_dijkstra.isChecked():
                geojson_str = target(sy, sx, ty, tx, dijkstra=True)

            if geojson_str:
                data = json.loads(geojson_str)

                feature = data["features"][0]
                trace_2180 = feature["geometry"]["coordinates"]
                cost = feature["properties"]["cost"]
                dist = feature["properties"]["distance"]

                if len(trace_2180) > 1:
                    path_4326 = []
                    for pt in trace_2180:
                        lon, lat = to_4326.transform(pt[0], pt[1])
                        path_4326.append([lat, lon])

                    self.browser.page().runJavaScript(f"window.drawRoute({json.dumps(path_4326)});")
                    self.log(f"Sukces! Dystans: <b>{dist/1000:.2f} km</b>, Koszt: <b>{cost:.2f}</b>")
                else:
                    self.log("<span style='color:orange;'>Punkty zbyt blisko siebie.</span>")
            else:
                self.log("<span style='color:red;'>Nie znaleziono trasy.</span>")

        except Exception as e:
            self.log(f"<span style='color:red;'>Błąd: {str(e)}</span>")

    def init_map(self):
        self.m = folium.Map(location=[49.6089, 19.1725], zoom_start=10)
        
        path_2417 = './powiat_zywiecki/powiat_zywiecki.geojson'
        with open(path_2417, 'r', encoding='utf-8') as f:
            data = json.load(f)
            folium.GeoJson(
                data,
                name='Powiat Żywiecki',
                interactive=False,
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': 'orange',
                    'weight': 4,
                    'fillOpacity': 0.1
                }
            ).add_to(self.m)

        self.log("Wczytano granice powiatu żywieckiego.")
        self.update_map()

    def update_map(self):
        script = f"""
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                var map = {self.m.get_name()};
                var startMarker, endMarker, routeLine;

                new QWebChannel(qt.webChannelTransport, function (channel) {{
                    window.handler = channel.objects.handler;
                }});

                map.on('click', function(e) {{
                    if (window.handler) window.handler.receive_coords(e.latlng.lat, e.latlng.lng);
                }});

                window.placeMarker = function(lat, lng, type) {{
                    var color = (type === 'start') ? 'green' : 'red';
                    var group = L.layerGroup([
                        L.circleMarker([lat, lng], {{radius: 10, fillColor: color, color: color, fillOpacity: 1}}),
                        L.circleMarker([lat, lng], {{radius: 6, fillColor: 'white', color: 'white', fillOpacity: 1}}),
                        L.circleMarker([lat, lng], {{radius: 3, fillColor: 'black', color: 'black', fillOpacity: 1}})
                    ]);
                    if (type === 'start') {{
                        if (startMarker) map.removeLayer(startMarker);
                        startMarker = group.addTo(map);
                    }} else {{
                        if (endMarker) map.removeLayer(endMarker);
                        endMarker = group.addTo(map);
                    }}
                }};

                window.drawRoute = function(coords) {{
                    if (routeLine) map.removeLayer(routeLine);
                    routeLine = L.polyline(coords, {{color: 'blue', weight: 5, opacity: 0.7}}).addTo(map);
                    map.fitBounds(routeLine.getBounds());
                }};
            }});
        </script>
        """
        self.m.get_root().header.add_child(folium.Element(script))
        
        data = io.BytesIO()
        self.m.save(data, close_file=False)
        self.browser.setHtml(data.getvalue().decode())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = InterfaceWidget()
    window.show()
    sys.exit(app.exec_())