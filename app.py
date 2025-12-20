import faust

# Faust application for processing sensor data streams
app = faust.App(
    'sensor-stream-app',
    broker='kafka://localhost:9092',
    store='memory://'
)


# Define the data models for each sensor reading
class Temperature(faust.Record):
    room: str
    value: float


class CO2(faust.Record):
    room: str
    ppm: int


class Motion(faust.Record):
    room: str
    motion: bool


class Light(faust.Record):
    room: str
    lux: int


class Sound(faust.Record):
    room: str
    db: float


class Occupancy(faust.Record):
    room: str
    count: int


# Topics for each sensor reading
temperature_topic = app.topic('temperature-readings', value_type=Temperature)
co2_topic = app.topic('co2-readings', value_type=CO2)
motion_topic = app.topic('motion-readings', value_type=Motion)
light_topic = app.topic('light-readings', value_type=Light)
sound_topic = app.topic('sound-readings', value_type=Sound)
occupancy_topic = app.topic('occupancy-readings', value_type=Occupancy)

# Tables to store the latest readings and averages
latest_temp = app.Table('latest_temp', default=float)
latest_motion = app.Table('latest_motion', default=bool)
temp_avg = app.Table('temp_avg', default=float)


# 1. Average temperature
@app.agent(temperature_topic)
async def process_temp(stream):
    async for reading in stream:
        temp_avg[reading.room] = (temp_avg[reading.room] + reading.value) / 2 if temp_avg[reading.room] else reading.value
        latest_temp[reading.room] = reading.value
        print(f"Average temperature in {reading.room}: {temp_avg[reading.room]:.2f}°C")


# 2. High CO2 alert
@app.agent(co2_topic)
async def process_co2(stream):
    async for reading in stream:
        if reading.ppm > 1000:
            print(f"ALERT: High CO2 level in {reading.room}: {reading.ppm} ppm")


# 3. Cold room only
@app.agent(temperature_topic)
async def check_cold_room(stream):
    async for reading in stream:
        if reading.value < 18:
            print(f"ALERT: Cold room in {reading.room} - {reading.value:.2f}°C")


# 4. Low-light alert (< 50 lux)
@app.agent(light_topic)
async def check_light(stream):
    async for reading in stream:
        if reading.lux < 50:
            print(f"Low light level in {reading.room}: {reading.lux} lux")


# 5. High-noise alert (> 1.0 dB)
@app.agent(sound_topic)
async def check_sound(stream):
    async for reading in stream:
        if reading.db > 1.0:
            print(f"ALERT: High noise level in {reading.room}: {reading.db:.2f} dB")


# 6. Room overcrowding alert (> 3 people)
@app.agent(occupancy_topic)
async def check_occupancy(stream):
    async for reading in stream:
        if reading.count > 3:
            print(f"Overcrowded room in {reading.room}: {reading.count} people")


if __name__ == '__main__':
    app.main()
