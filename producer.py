from kafka import KafkaProducer
import json
import time
import pandas as pd

# create a Kafka producer to send messages to Kafka topics
producer = KafkaProducer(bootstrap_servers='localhost:9092',
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Read sensor data from a CSV file
df = pd.read_csv('sensor_data.csv')

# Define a mapping of sensor names to room names
room_map = {
    'S1': 'Living Room',
    'S2': 'Bedroom',
    'S3': 'Kitchen',
    'S4': 'Office'
}

# Iterate through the DataFrame and send messages to Kafka topics
for _, row in df.iterrows():
    for idx, (sensor, room_name) in enumerate(room_map.items(), start=1):
        # Construct the topic name based on the sensor index
        producer.send('temperature-readings', {'room': room_name, 'value': row[f'{sensor}_Temp']})
        producer.send('co2-readings', {'room': room_name, 'ppm': row['S5_CO2']})
        producer.send('motion-readings', {'room': room_name, 'motion': bool(row['S6_PIR'] or row['S7_PIR'])})
        producer.send('light-readings', {'room': room_name, 'lux': row[f'{sensor}_Light']})
        producer.send('sound-readings', {'room': room_name, 'db': row[f'{sensor}_Sound']})
        producer.send('occupancy-readings', {'room': room_name, 'count': int(row['Room_Occupancy_Count'])})

    # Sleep for a short duration to simulate real-time data streaming
    time.sleep(0.7)
