# Project Overview
- The main goal of this program is to create an application in python that computes the cost of gas when traveling places
- this is for a hackathon

# Project outline
- this app will be divided into the following sections:
- Trip route and distance: takes stating point and destination from user and computes the distance
- Interactive map: make an interactive map of the distance between the 2 locations
- Gas prices: get regional averages of gas around starting point (using API data), and has fuel efficiency customizable and considered for total cost
- Carpool: allow user to choose how many ways the cost of gas is split
- Display: displays total cost of gas needed for the trip and individual shares
- API will likely be used in getting data for relevant distances or data


# Rules
- always ask before installing packages
- Keep components modular
- handle loading/error states on every API call
- do not use placeholder dummy data

# Security & API Keys
- **Never hardcode secrets:** Never write API keys, tokens, passwords, or credentials directly into source code files. Always load them via environment variables (e.g., `process.env.API_KEY` or `os.getenv("API_KEY")`).
- **Protect `.env` files:** Never read, print, log, or display the contents of `.env` or `.env.*` files in chat responses or terminal outputs.
- **Maintain `.gitignore`:** Ensure `.env`, `.env.local`, `.env.*`, and any secret key files (like `*.pem` or `credentials.json`) are always listed in `.gitignore`. If a `.gitignore` file does not exist, create one before adding environment files.
- **Use `.env.example`:** When adding a new environment variable, add a placeholder name (without the real secret) to `.env.example` so others know what keys are required.