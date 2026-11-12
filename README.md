# Retail-ai

Retail Recommendation & Shopping Assistant

A small Python/FastAPI application that serves a sample retail catalog, product recommendations, and a conversational shopping assistant. The catalog and ranking logic are intentionally in-memory so the project runs locally without a database or external AI service.

Visit `http://localhost:8000` for the responsive storefront. It supports live product search and category filters, with the shopping assistant alongside the collection.

## Features

- Responsive storefront at `/` connected to the product and chat APIs.
- Search and filter a sample catalog by text, category, and price.
- Recommend products by similar item, category, preferences, and budget.
- Chat endpoint that interprets simple shopping requests and returns matching products.
- Liveness/readiness endpoints, container image, and Kubernetes Deployment/Service manifest.
- Interactive API documentation at `/docs`.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.

## Example requests

```powershell
curl.exe http://localhost:8000/api/v1/products
curl.exe "http://localhost:8000/api/v1/recommendations?product_id=p-1001&max_price=100"
curl.exe -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{\"message\":\"Recommend something for travel under 60\"}'
```

## Test

```powershell
pip install -r requirements-dev.txt
pytest
```

## Build and run with Docker

```powershell
docker build -t retail-assistant:latest .
docker run --rm -p 8000:8000 retail-assistant:latest
```

## Deploy to Kubernetes

Build the image in a registry accessible to your cluster and update the image in `k8s/deployment.yaml`:

```powershell
docker build -t <your-registry>/retail-assistant:1.0.0 .
docker push <your-registry>/retail-assistant:1.0.0
kubectl apply -f k8s/deployment.yaml
kubectl get deployments,services
kubectl port-forward service/retail-assistant 8000:80
```

For a local cluster, load the image into that cluster using its image-loading command and leave `imagePullPolicy: IfNotPresent`.

## API overview

- `GET /health/live` and `GET /health/ready`
- `GET /api/v1/products?query=coffee&category=home&max_price=60`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/recommendations?product_id=p-1001&preferences=travel&max_price=100`
- `POST /api/v1/chat` with `{"message":"I need a travel bag under 100"}`

The chat implementation is a lightweight rule-based demo, not a hosted LLM. Replace the in-memory catalog and recommendation ranking with a persistent catalog, event/user profile data, and an evaluated recommendation model before production use.
