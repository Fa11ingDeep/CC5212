from confluent_kafka import Producer
from confluent_kafka import Consumer
import threading
import time
import sys
import datetime

topic = sys.argv[1]


def consume():
    c = Consumer({
        'bootstrap.servers': 'c1:9092',
        'group.id': 'default_consumer_group',
        'auto.offset.reset': 'earliest'
    })

    c.subscribe([topic])

    while True:
        msg = c.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue

        print('{} [{}] offset={}, key={}, value=\"{}\"\n'.format(msg.topic(),msg.partition(), msg.offset(), msg.key(), msg.value().decode('utf-8')))

def produce():

    p = Producer({'bootstrap.servers': 'c1:9092'})

    def delivery_report(err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            print('Message delivery failed: {}'.format(err))
        else:
            print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

    i = 0;
    while True:
        d = datetime.datetime.now()
        # Trigger any available delivery report callbacks from previous produce() calls
        p.poll(0)
        
        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        p.produce(topic=topic, partition=0, key=str(i), value=d.strftime("%d-%b-%Y (%H:%M:%S.%f)"), callback=delivery_report)
        time.sleep(1)
        i += 1
        
        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        p.flush()

x = threading.Thread(target=produce)
x.start()
consume()
