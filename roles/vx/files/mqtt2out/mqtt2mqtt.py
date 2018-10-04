#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import datetime
import time
import yaml
import sys


def on_connect(client, userdata, flags, rc):
    print("Publisher broker connected. Result: {}".format(mqtt.connack_string(rc)))

    print("Subscribtion:")
    cfg = userdata
    topics = cfg["publisher"]["topics"]
    for t in topics:
        client.subscribe(t)
        print("- {}".format(t))


def on_disconnect(client, userdata, rc):
    print("Publisher broker DISCONNECTED. Result={}".format(rc))


def on_publish_message(client, userdata, msg):
    receiveTime = datetime.datetime.utcnow()
    print("{}: {} {}".format(str(receiveTime), msg.topic, msg.payload.decode("utf-8")))
    cfg = userdata
    prefix = hostname=cfg["consumer"]["prefix"]
    publish.single( topic="{}{}".format(prefix, msg.topic)
                    , payload=msg.payload
                    , qos=msg.qos
                    , retain=msg.retain
                    , hostname=cfg["consumer"]["mqtt"]["hostname"]
                    , port=cfg["consumer"]["mqtt"]["port"]
                    , client_id=cfg["consumer"]["mqtt"]["client_id"]
                    , keepalive=7
                    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="mqtt -> mqtt gate")
    parser.add_argument('-c', '--cfg', dest='cfg', help='config yaml file', default="mqtt2mqtt.conf")
    args = parser.parse_args()

    with open(args.cfg, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    mqtt_pub = mqtt.Client(client_id=cfg["publisher"]["mqtt"]["client_id"], userdata=(cfg))
    mqtt_pub.on_connect = on_connect
    mqtt_pub.on_disconnect = on_disconnect
    mqtt_pub.on_message = on_publish_message
    connOK = False

    while (connOK == False):
        try:
            mqtt_pub.connect(cfg["publisher"]["mqtt"]["hostname"], cfg["publisher"]["mqtt"]["port"], keepalive=3)
            connOK = True
        except:
            connOK = False
            print("Bad connection to publisher")
            time.sleep(5)

    mqtt_pub.loop_forever()


if __name__ == '__main__':
    try:
        print('-----------------------------------------------')
        main()
    except (SystemExit, KeyboardInterrupt):
        print('-----------------------------------------------')
    except:
        type, value, traceback = sys.exc_info()
        print("Exception: {}".format(value))
