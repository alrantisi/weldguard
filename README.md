# WeldGuard

AI-based PPE detection for welders. A detection model processes camera or video input, a FastAPI backend serves data, and a web dashboard provides live monitoring, an incident log, and worker management. Built as a group project across the IoT, Big Data, and Server Technology courses at Universitas Gadjah Mada, and deployed on Kubernetes.

## Structure

```
backend/           FastAPI backend (Dockerfile, main.py, data.json)
dashboard/         Web dashboard (index, live monitoring, incident log, worker management)
inference_engine/  Detection model (best.pt), inference.py, config.py
backend-k8s.yaml   Kubernetes manifest for the backend
dashboard-k8s.yaml Kubernetes manifest for the dashboard
```

## Tech stack

Python, FastAPI, HTML/CSS/JavaScript, Docker, Kubernetes (containerd), Tailscale

## Run the inference engine

```bash
cd inference_engine
pip install -r requirements.txt
python inference.py
```

Settings live in `config.py`: set `CAMERA_MODE` to `"webcam"` or `"video"`, and `ESP32_IP` for the IoT device. The sample video is not included; place your own test video as `inference_engine/sample_video.mp4`.

## Deploy on Kubernetes

The cluster runs on Ubuntu Server 24.04 with containerd and no external image registry, so images are built with Docker and imported directly into containerd:

```bash
docker build -t weldguard-backend ./backend
docker build -t weldguard-dashboard ./dashboard
docker save weldguard-backend | sudo ctr -n k8s.io images import -
docker save weldguard-dashboard | sudo ctr -n k8s.io images import -
kubectl apply -f backend-k8s.yaml -f dashboard-k8s.yaml
```

The backend is exposed on port 30800 and the dashboard on port 30801.

## Notes

- Deployed on a campus-hosted VPS and accessed through Tailscale.
- Troubleshooting notes: WebSocket connectivity (missing `websockets` dependency in `requirements.txt`) and a VPS crash caused by swap, resolved by disabling swap permanently.
