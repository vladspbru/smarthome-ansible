#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import datetime
import time
from influxdb import InfluxDBClient
import yaml
import sys


class InfluxDbWriter(object):
    def __init__(self, cfg):
        self.addr = cfg["influxdb_address"]
        self.port = cfg["influxdb_port"]
        self.sch = cfg["influxdb_schema"]
        # self.user = cfg["influxdb_user"]
        # self.pwd = cfg["influxdb_password"]
        self.connect()

    def connect(self):
        if hasattr(self, "influxdb"):
            self.influxdb.close()
        self.influxdb = InfluxDBClient(host=self.addr, port=self.port,
                                       database=self.sch)  # username=self.user, password=self.pwd)
        try:
            version = self.influxdb.ping()
            if version:
                print("InfluxDB version: " + version)
                dblist = self.influxdb.get_list_database()
                count = 0
                for db in dblist:
                    if db["name"] == self.sch:
                        count += 1
                if count == 0:
                    print("Create database: " + self.sch)
                    self.influxdb.create_database(self.sch)
        except:
            print("No InfluxDb connection {}:{}".format(self.addr, self.port))

    def close(self):
        self.influxdb.close()

    def write(self, json_body):
        is_ok = False
        try:
            is_ok = self.influxdb.write_points(json_body)
        except:
            is_ok = False
        if not is_ok:
            print("Error writing to InfluxDB")
            self.connect()
        return is_ok


def on_connect(client, userdata, flags, rc):
    cfg, writer = userdata
    print("Mqtt broker {}:{} connected with result code {}".format(cfg["mqtt_address"],cfg["mqtt_port"], rc))

    print("Mqtt subscribtion:")
    topics = cfg["mqtt_topic"]
    for t in topics:
        client.subscribe(t)
        print("- {}".format(t))


def on_message(client, userdata, msg):
    message = msg.payload.decode("utf-8")
    is_float_value = False
    val = 0.
    try:
        # Convert the string to a float so that it is stored as a number and not a string in the database
        val = float(message)
        is_float_value = True
    except:
        print("Skipping message /no float/\n{}: {} ".format(msg.topic, message))
        is_float_value = False

    if is_float_value:
        # Use utc as timestamp
        receiveTime = datetime.datetime.utcnow()
        json_body = [
            {
                "time": receiveTime,
                "measurement": msg.topic,
                "fields": {
                    "value": val
                }
            }
        ]
        cfg, writer = userdata
        writer.write(json_body)
        print("{} | {} | {} ".format(str(receiveTime), msg.topic, val))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mqtt to InfluxDb gate.")
    parser.add_argument('-c', '--cfg', dest='cfg', help='config yaml file', default="mqtt2influxdb.conf")
    args = parser.parse_args()

    with open(args.cfg, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    writer = InfluxDbWriter(cfg)

    # Initialize the mqtt_cli that should connect to the Mosquitto broker
    mqtt_cli = mqtt.Client(client_id=cfg["mqtt_clientid"], userdata=(cfg, writer))
    mqtt_cli.on_connect = on_connect
    mqtt_cli.on_message = on_message
    connOK = False

    while (connOK == False):
        try:
            mqtt_cli.connect(cfg["mqtt_address"], cfg["mqtt_port"], 60)
            connOK = True
        except:
            connOK = False
            print("Bad connection to broker  {}:{} ".format(cfg["mqtt_address"], cfg["mqtt_port"]))
        time.sleep(3)

    # Blocking loop to the Mosquitto broker
    mqtt_cli.loop_forever()


if __name__ == '__main__':
    try:
        print('-----------------------------------------------')
        main()
    except (SystemExit, KeyboardInterrupt):
        print('-----------------------------------------------')
    except:
        type, value, traceback = sys.exc_info()
        print("Exception: {}".format(value))
