from gui import Ui_Form
from PyQt5 import QtWidgets, QtWebEngineWidgets
from PyQt5.QtWebChannel import QWebChannel
import sys
import folium
from folium.plugins import FastMarkerCluster
import io
from datetime import datetime
import pymongo
import redis
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import LinearLocator
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json

LEGEND = {
    "B00300S": ("Temperatura powietrza [°C]"),
    "B00305A": ("Temperatura gruntu [°C]"),
    "B00202A": ("Kierunek wiatru [°]"),
    "B00702A": ("Śr. prędkość wiatru [m/s]"),
    "B00703A": ("Prędkość maksymalna [m/s]"),
    "B00608S": ("Suma opadu [mm]"),
    "B00604S": ("Suma opadu dobowego [mm]"),
    "B00606S": ("Suma opadu godzinowego [mm]"),
    "B00802A": ("Wilgotność względna [%]"),
    "B00714A": ("Największy poryw [m/s]"),
    "B00910A": ("Zapas wody w śniegu [mm]")
}

class InterfaceWidget(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init_plots()
        
        self.log("Uruchomiono aplikację.")

        self.channel = QWebChannel()
        self.channel.registerObject('handler', self)
        self.facilities_data = []

        self.init_map()

        self.B_effacilities.clicked.connect(self.load_effacilities)
        self.B_selectStation.clicked.connect(self.get_ifcid)
        self.B_verify.clicked.connect(self.verify_with_redis)
        self.B_plots.clicked.connect(self.plot_meteo_data)

        combos = [self.C_plot1, self.C_plot2, self.C_plot3]
        for cb in combos:
            for code, name in LEGEND.items():
                cb.addItem(f"{name}", code)
        
        self.C_plot1.setCurrentIndex(0)
        self.C_plot2.setCurrentIndex(1)
        self.C_plot3.setCurrentIndex(2)

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        mes = f"<b>[{now}]</b> {message}"
        self.changelog.append(mes)
        self.changelog.ensureCursorVisible()

    def init_map(self):
        self.m = folium.Map(location=[52.114339, 19.423672], zoom_start=6)
        self.update_map()

    def update_map(self):
        data = io.BytesIO()
        self.m.save(data, close_file=False)
        map_html = data.getvalue().decode()
        
        if not hasattr(self, 'browser'):
            self.browser = QtWebEngineWidgets.QWebEngineView(self.W_map)
            self.browser.page().setWebChannel(self.channel)
            
            layout = QtWidgets.QVBoxLayout(self.W_map)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.browser)
        
        self.browser.setHtml(map_html)

    def load_effacilities(self):
        self.log("Ładowanie stacji z bazy...")
        client = pymongo.MongoClient('mongodb+srv://pag2:haslomongo@effacility.i7mbxbt.mongodb.net/')
        db = client.mongo
        
        facilities = list(db.effacility.find({}, {
            "geometry.coordinates": 1, 
            "properties.name1": 1,
            "properties.ifcid": 1
        }))
        self.facilities_data = facilities
        client.close()
        self.display(facilities)
        
    def display(self, facilities_list):
        self.init_map()
        data = []

        callback = """
            function (row) {
                var marker = L.marker(new L.LatLng(row[0], row[1]));
                marker.bindPopup(row[2]);
                return marker;
            };
        """

        for fac in facilities_list:
            coords = fac.get('geometry', {}).get('coordinates')

            if isinstance(coords, list) and len(coords) >= 2:
                props = fac.get('properties', {})
                name = props.get('name1', 'Brak nazwy')
                ifcid = props.get('ifcid', 'Brak ID')
                
                popup = f"<b>{name}</b><br>(IFCID: {ifcid})"
                data.append([coords[0], coords[1], popup])

        if data:
            FastMarkerCluster(data, callback=callback).add_to(self.m)
            self.update_map()
            self.log(f"Dodawanie zakończone sukcesem.")
            self.log(f"Liczba obiektów: <b>{len(data)}</b>")
        else:
            self.log("Nie znaleziono poprawnych danych do wyświetlenia.")

    def verify_with_redis(self):
        if not hasattr(self, 'facilities_data') or not self.facilities_data:
            self.log("Brak danych z MongoDB")
            return

        try:
            self.log("Weryfikacja z bazą Redis...")
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)

            all_redis_keys = r.keys('meteo:*')

            redis_station_ids = set()
            for key in all_redis_keys:
                parts = key.split(':')
                if len(parts) >= 2:
                    redis_station_ids.add(parts[1])

            filtered_data = []
            for fac in self.facilities_data:
                ifcid = str(fac.get('properties', {}).get('ifcid'))

                if ifcid in redis_station_ids:
                    filtered_data.append(fac)
            
            removed_count = len(self.facilities_data) - len(filtered_data)

            self.display(filtered_data)
            
            self.log(f"Weryfikacja zakończona.")
            self.log(f"Usunięto: <b>{removed_count}</b>.")
            self.log(f"Pozostałe obiekty: <b>{len(filtered_data)}</b>")

        except Exception as e:
            self.log(f"Błąd podczas weryfikacji Redis: {e}")

    def get_ifcid(self):
        self.ifcid = self.E_ifcid.toPlainText().strip()
        if not self.ifcid:
            self.log("Pole IFCID jest puste.")
            return None

        ifcid_coor = None
        if hasattr(self, 'facilities_data'):
            for fac in self.facilities_data:
                if str(fac.get('properties', {}).get('ifcid')) == self.ifcid:
                    coords = fac.get('geometry', {}).get('coordinates')
                    if coords and len(coords) >= 2:
                        ifcid_coor = [coords[0], coords[1]]
                        break
        
        self.m.location = ifcid_coor
        self.m.options['zoom'] = 12 
        self.update_map()
        self.log(f"Ustawiono stację: <b>{self.ifcid}</b>")       
        return self.ifcid
    
    def init_plots(self):
        plot_widgets = [self.W_plot1, self.W_plot2, self.W_plot3]
        self.figures = []
        self.canvases = []

        for widget in plot_widgets:
            fig, ax = plt.subplots(facecolor='#f0f0f0') 
            canvas = FigureCanvas(fig)
            fig.subplots_adjust(left=0.1, bottom=0.2, top=0.85)
            
            layout = widget.layout()
            if layout is None:
                layout = QtWidgets.QVBoxLayout(widget)
            
            layout.setContentsMargins(0, 0, 0, 0) 
            layout.addWidget(canvas)
            
            ax.set_title("Oczekiwanie na dane...", fontsize=10, pad=10)
            ax.tick_params(axis='both', which='major', labelsize=8)
            ax.grid(True, linestyle='--', alpha=0.4)
            
            ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            self.figures.append(fig)
            self.canvases.append(canvas)
    
    def plot_meteo_data(self):
        ifcid = self.get_ifcid()
        if not ifcid: return

        start_dt = datetime.combine(self.DE_dateStart.date().toPyDate(), self.TE_start.time().toPyTime())
        end_dt = datetime.combine(self.DE_dateEnd.date().toPyDate(), self.TE_end.time().toPyTime())

        params_to_plot = [
            self.C_plot1.currentData(),
            self.C_plot2.currentData(),
            self.C_plot3.currentData()
        ]
        
        start_dt = datetime.combine(self.DE_dateStart.date().toPyDate(), self.TE_start.time().toPyTime())
        end_dt = datetime.combine(self.DE_dateEnd.date().toPyDate(), self.TE_end.time().toPyTime())

        self.log(f"Przeszukiwanie danych<br>data początkowa: <b>{start_dt.strftime('%d.%m.%y %H:%M')}</b><br>data końcowa: <b>{end_dt.strftime('%d.%m.%y %H:%M')}</b>")
        plot_data = {p: {"x": [], "y": []} for p in params_to_plot}

        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            current_date = start_dt.date()
            date_limit = end_dt.date()
            
            while current_date <= date_limit:
                redis_key = f"meteo:{ifcid}:{current_date.strftime('%Y-%m-%d')}"
                records = r.lrange(redis_key, 0, -1)
                
                if records:
                    for raw_record in records:
                        data_obj = json.loads(raw_record)
                        param = data_obj.get("ParametrSH")
                        
                        if param in plot_data:
                            try:
                                rec_dt = datetime.strptime(data_obj["Data"], "%Y-%m-%d %H:%M")
                                if start_dt <= rec_dt <= end_dt:
                                    plot_data[param]["x"].append(rec_dt)
                                    plot_data[param]["y"].append(float(data_obj["Wartosc"]))
                            except Exception as e:
                                continue
                
                current_date += timedelta(days=1)

            for i, param in enumerate(params_to_plot):
                ax = self.figures[i].axes[0]
                ax.clear()

                full_name = LEGEND.get(param, (param, ""))
                
                if plot_data[param]["x"]:
                    combined = sorted(zip(plot_data[param]["x"], plot_data[param]["y"]))
                    x_sorted, y_sorted = zip(*combined)
                    
                    ax.plot(x_sorted, y_sorted, color='steelblue', linewidth=1.5, marker='.', markersize=4)

                    ax.set_title(f"{full_name} ({param})", fontsize=10, fontweight='bold')
                    self.figures[i].subplots_adjust(left=0.1, bottom=0.25, top=0.85)
                    
                    ax.xaxis.set_major_locator(LinearLocator(numticks=5))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%d.%m'))
                    
                    ax.tick_params(labelsize=8)
                    ax.grid(True, alpha=0.3, linestyle='--')

                    if param == "B00202A":
                        ax.set_ylim(0, 360)
                else:
                    ax.text(0.5, 0.5, f"Brak danych dla\n{full_name}", ha='center', va='center', color='gray')
                
                self.canvases[i].draw()

            self.log(f"Wykonano wykresy.")

        except Exception as e:
            self.log(f"Błąd: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = InterfaceWidget()
    window.show()
    sys.exit(app.exec_())