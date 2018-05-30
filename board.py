#!/usr/bin/env python3
# coding: utf-8

import sys
import time
import pytz
import json

from datetime import datetime
from influxdb import InfluxDBClient

from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal


class DataStore(object):
    def __init__(self):
        self.client = InfluxDBClient(
            # fill influxdb connection info
            config['influxdb']['host'],
            config['influxdb']['port'],
            config['influxdb']['username'],
            config['influxdb']['password'],
            config['influxdb']['dbname']
        )

    def select_last_temperature(self):
        return self.select_last_point('temperature', {'locationName': 'Home'})

    def select_last_humidity(self):
        return self.select_last_point('humidity', {'locationName': 'Home'})

    def select_last_point(self, measurement, tags):
        result = self.client.query(
            'select mean(value) as value from ' + measurement + ' where time >= now()-24h ' +
            'group by time(5m), locationName fill(previous)'
        )
        return list(result.get_points(measurement=measurement, tags=tags))[-1]


class TicGenerator(QThread):
    tic = pyqtSignal(name='Tic')

    def __init__(self):
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            t = int(time.time())
            if not t % 5 == 0:
                self.sleep(60)
                continue
            self.tic.emit()
            self.sleep(60)


class Form(QtWidgets.QDialog):
    def __init__(self, parent=None):
        self.data_store = DataStore()
        QtWidgets.QDialog.__init__(self, parent)
        self.tic_gen = TicGenerator()
        self.tic_gen.start()

        self.ui = uic.loadUi('ui/dialog.ui', self)
        self.set_values()
        self.tic_gen.Tic.connect(
            lambda: self.set_values()
        )
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.ui.show()

    def set_values(self):
        time_value = self.data_store.select_last_temperature()['time']
        checked_at = datetime.strptime(time_value, '%Y-%m-%dT%H:%M:%SZ')
        checked_at = pytz.utc.localize(checked_at)

        temperature = self.data_store.select_last_temperature()['value']
        humidity = self.data_store.select_last_humidity()['value']
        self.label_temperature_indoor.setText('{} ℃'.format(temperature))
        self.label_humidity_indoor.setText('{} %'.format(humidity))
        self.label_checked_at.setText(
            pytz.timezone('Asia/Seoul')
                .normalize(checked_at)
                .strftime('%Y-%m-%d %H:%M:%S %Z')
        )


if __name__ == '__main__':
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print('config.json file not found.')
        sys.exit(1)

    app = QtWidgets.QApplication(sys.argv)
    w = Form()
    sys.exit(app.exec())
