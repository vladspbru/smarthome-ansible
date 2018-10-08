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
                                       database=self.sch, timeout=3,
                                       retries=2)  # username=self.user, password=self.pwd)
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
    print("Mqtt broker {}:{} connected. Result: {}".format(cfg["mqtt_address"], cfg["mqtt_port"],
                                                           mqtt.connack_string(rc)))

    print("Mqtt subscribtion:")
    topics = cfg["mqtt_topics"]
    for t in topics:
        client.subscribe(t)
        print("- {}".format(t))


def on_disconnect(client, userdata, rc):
    cfg, writer = userdata
    print("Mqtt broker {}:{} DISCONNECTED".format(cfg["mqtt_address"], cfg["mqtt_port"]))


def str_is_boolean(v):
    res = None
    if v.lower() in ("yes", "true", "t", "1", "on", "online"):
        res = True
    if v.lower() in ("no", "false", "f", "0", "off", "offline"):
        res = False
    return res


def on_message(client, userdata, msg):
    message = msg.payload.decode("utf-8")

    val = None
    # is number
    try:
        val = float(message)
    except:
        val = None

    # is boolean
    if val == None:
        val = str_is_boolean(message)

    if val != None:
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
    else:
        print("no float, number or boolean\n{} | {} ".format(msg.topic, message))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mqtt to InfluxDb gate.")
    parser.add_argument('-c', '--cfg', dest='cfg', help='config yaml file', default="mqtt2influxdb.conf")
    args = parser.parse_args()

    with open(args.cfg, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    writer = InfluxDbWriter(cfg)

    mqtt_cli = mqtt.Client(client_id=cfg["mqtt_clientid"], userdata=(cfg, writer))
    mqtt_cli.on_connect = on_connect
    mqtt_cli.on_disconnect = on_disconnect
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
