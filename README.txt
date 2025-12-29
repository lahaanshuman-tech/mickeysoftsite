MickeySoftSite - Local LAN web app
---------------------------------

How to run:
1. Ensure Python 3.8+ is installed on the PC.
2. Place your logo image at: frontend/assets/logo.png (overwrite if exists).
3. Double-click start_server.bat (or open a terminal and run the commands below).

Manual start (optional):
  cd backend
  python server.py

Open in browser (from any device on same Wi-Fi):
  http://192.168.29.222:8000

Admin credentials (hardcoded for LAN demo):
  Username: admin
  Password: adminms123

Notes:
- Uploaded installers are stored in backend/uploads and persist across reboots.
- This is a local LAN demo. Do not expose it to the public internet without adding proper security.
