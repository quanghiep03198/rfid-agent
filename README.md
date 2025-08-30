## Overview

`RFID Agent` is an IoT application designed to connect web and native applications with the RFID device model SF5004. This project leverages Mosquitto MQTT for seamless communication between the RFID device and client applications.

## Technologies Used

- **Programming Language**: Python
- **Dependencies**:
  - `paho-mqtt` for MQTT communication
  - `uhfReaderApi` for lightweight database management

## Key Features

- Connect and interact with the RFID device model SF5004.
- Publish and subscribe to RFID events using Mosquitto MQTT.
- Store and manage RFID data in a database.
- Provide a web-based interface for monitoring and configuration.
- Support for real-time RFID event handling.

## Installation & Configuration

1. Clone the repository:
   ```pwsh
   git clone https://github.com/your-username/py-rfid-agent.git
   cd py-rfid-agent
   ```
2. Set up a virtual environment:
   ```pwsh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:

   ```pwsh
   pip install -r requirements.txt
   ```

4. Download and install Mosquitto MQTT following below instruction

   4.1 Download Mosquitto from [here](https://mosquitto.org/download/)

   4.2 Get you device IPv4 type A

   ```pwsh
   ipconfig
   -----------------------------------------------------------------
   Ethernet adapter:

   Connection-specific DNS Suffix  . :
   Link-local IPv6 Address . . . . . : xxxx::xxxx:xxxx:xxxx:xxxx%6
   IPv4 Address. . . . . . . . . . . : 10.xx.xxx.xx   # Copy this one
   Subnet Mask . . . . . . . . . . . : 255.xxx.xxx.x
   IPv4 Address. . . . . . . . . . . : 192.xxx.x.xx
   Subnet Mask . . . . . . . . . . . : 255.xxx.xxx.xxx
   Default Gateway . . . . . . . . . : 10.xx.xxx.xxx

   ```

   4.3 Update Mosquitto config:

   Open the folder that you have installed Mosquitto in. Open `mosquitto.conf` and update the configuration like this:

   ```conf
   # MQTT TCP for publisher/subscriber/backend
   listener 1883 <IPv4 Address>

   # MQTT WebSocket for client
   listener 9001 <IPv4 Address>
   protocol websockets
   ```

   4.4 Restart Mosquitto service

   ```pwsh
   net stop mosquitto
   net start mosquitto
   ```

5. Run the application:
   ```pwsh
   python main.py
   ```

## Contribution

Feel free to fork this repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
