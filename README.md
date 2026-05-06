# CEDRI - AI Manager for the Cedrinho Robot

## Project Logic

* Every hour, the robot requests a new route from the `IA Manager` server;
* The robot proceeds to the assigned route;
* Collects information;
* If performance is too low within the first 30 minutes, it sends an additional request;
* The `IA Manager` can decide to stay in the current location (for the next 30 min) or move to another (which restarts the cycle);
* We aggregate the collected information into a batch every 24h and send it to the `IA Manager` server to train with this new data;

## State Logic

To ensure the robot learns efficiently, we split the data flow into **Sessions per Location**. Every time the robot decides to change its `current_location`, the environment undergoes a "soft reset." This allows the AI to understand the direct impact of its actions at that specific location.

### Reset Cycle
When the `current_location` is changed, the following variables return to **zero**:

* **`location_time`**: Resets to measure how long the new approach takes to take effect.
* **`helping_time`**: Resets so the AI can evaluate its effectiveness exclusively at the new location.
* **`unique_people`**: The counter for new interactions is cleared.
* **`environment_people`**: Updated for the instantaneous census of the new location.

The `helping_time` acts as a reward, but it is also an input for the AI to understand the current situation.

---

### Input Data Structure

| Variable | Type | Transformation | Description |
| :--- | :--- | :--- | :--- |
| **Current Location** | Embedding | Vector(10-14) | Point identity (1 of N). |
| **Time at Point** | Scalar | Normalized | Elapsed time since the last arrival. |
| **Helping Time** | Scalar | Normalized | Accumulated performance in the current session. |
| **Daily Cycle** | Cyclic | Sin/Cos | Time of day to capture routines. |
| **Annual Cycle** | Cyclic | Sin/Cos | Day of the year to capture seasonality. |
| **Population** | Integer | Normalized | Density of people at the location vs. unique people. |

## License
This project is licensed under the MIT License.

Creator: **Yan Jardim Leal** <br>Institution: **Polytechnic Institute of Bragança (IPB)**