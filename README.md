# CEDRI - Route Manager for the Cedrinho Robot

Welcome to the Route Manager repository for the Cedrinho robot. Developed at the Polytechnic Institute of Bragança (IPB), this project acts as the orchestrator and bridge between the robot's physical navigation system and the external Artificial Intelligence (Deep Q-Learning) server.

Instead of running heavy neural networks directly on the robot's hardware, this system runs as a lightweight API. It collects real-time telemetry, builds a historical database of the environment, evaluates the robot's efficiency, and requests navigation decisions from the AI server.

---

## 1. How It Works: The Core Cycle

The system operates in a continuous loop of data collection, inference, and reinforcement learning synchronization:

1. **Receive Statistics (Every X seconds):** The robot constantly sends telemetry data (current coordinates, number of people around, moving status, and if it is actively helping someone) to the `/api/models/send-data` endpoint.
   
2. **Accumulate Data (Local State Management):** The `data_receiver` script processes these frequent pings. It filters out transition movements and accumulates the actual "helping time" and "population count" while the robot is stationed at a specific point. This information is saved chronologically in a local SQLite database (`data.db`) as a "Memory".

3. **Route Inference (Every 30-60 minutes):** A background scheduler periodically pauses to ask: *"Where should the robot go next?"* It retrieves the latest location history (a sliding window of the last 5 stops), normalizes the environment data (time of day, day of the week, population density) into a mathematical matrix, and sends an inference request to the AI Server. The AI replies with the next route ID, which is then dispatched to the robot.

4. **Batch Training (Reinforcement Learning Sync):** Periodically (e.g., daily), the system runs a synchronization task (`metrics_sync`). It looks back at the completed routes and calculates a **Reward** based on the robot's efficiency (heavily weighted towards how much time it actually spent helping people vs. staying in empty rooms). It builds experience batches (State -> Action -> Reward -> Next State) and sends them to the AI server so the model can learn from its past decisions and improve over time.

---

## 2. Running the Application

The application is built using FastAPI and Uvicorn. You can start the server using the `main.py` script with various command-line arguments to configure the network connections.

### Basic Execution
```bash
python src/main.py --port 8000 --ipia 192.168.1.100 --portia 8001
```

### Available Arguments
* `-v` or `--verbose`: Activates detailed terminal logging for debugging purposes.
* `--port`: The local port where this Route Manager API will run.
* `--ipia`: The IP address of the external CEDRI IA Manager Server.
* `--portia`: The port of the external CEDRI IA Manager Server.
* `--new`: A flag that ignores previously saved tokens/models and forces the creation of a new AI model from scratch.

---

## 3. API Endpoints

Once the application is running, it exposes a few core REST endpoints to communicate with the robot's internal hardware:

### `GET /api/echo`
A simple health-check endpoint to verify if the Route Manager server is online and reachable.

### `POST /api/models/send-data`
The primary data ingestion endpoint. Expects a JSON payload containing the robot's current telemetry.
**Example Payload:**
```json
{
  "x": 10,
  "y": 25,
  "people": 5,
  "is_helping": true,
  "moving": false,
  "unique_people": ["id_1", "id_2"]
}
```

---

## 4. Project Structure Overview

Based on the `src/` directory, the logic is separated into specific domains:

* **`api/`**: Contains the FastAPI endpoint logic (e.g., `data_receiver.py`) that handles incoming POST requests.
* **`core/`**: Houses utility scripts like `ia_translator.py` (which transforms real-world database metrics into normalized arrays for the Neural Network) and the logging configuration.
* **`database/`**: Manages the SQLite connection, table creation (`repository.py`), and read/write operations for the robot's memories.
* **`tasks/`**: Contains the background jobs managed by the `scheduler.py`, such as asking for new routes (`route_update.py`) and syncing the training data (`metrics_sync.py`).
* **`main.py`**: The application entry point that bootstraps the API, database, and background tasks.

---


## License
This project is licensed under the MIT License.

Creator: **Yan Jardim Leal** <br>Institution: **Polytechnic Institute of Bragança (IPB)**