# Trade Tracker

A local-only web application designed to run on a laptop and be accessible from other devices (like mobile phones or tablets) on the same network. This application is used to track Nifty Cash stock trades.

## Features

- **Autocomplete Stock Names**: Uses an internal cache pre-loaded into SQLite for Nifty Cash.
- **Custom Formatting**: Automatically formats the "Buy Date" and "Sell Date" fields with slashes (mm/dd/yyyy) and rounds prices to 0 decimal places.
- **Local Database**: All information is stored locally in a SQLite database (`database.db`). No external web access is required.

## Prerequisites

- Python 3
- Flask

You can install Flask by running:
```bash
pip3 install flask
```

## Setup & Running the Application

1. **Initialize the Database**: First, you must run the initialization script to generate the SQLite database and pre-load it with the Nifty Cash stock list cache.
   ```bash
   python3 init_db.py
   ```

2. **Start the Web Server**: Once the database is initialized, start the Flask web server.
   ```bash
   python3 app.py
   ```

3. **Access the Application**:
   - From the laptop running the server: Open your web browser and go to `http://localhost:5000` or `http://127.0.0.1:5000`.
   - From other devices on the network: Find your laptop's local IP address (e.g., `192.168.1.x`) and navigate to `http://<YOUR-LAPTOP-IP>:5000` on their web browsers.