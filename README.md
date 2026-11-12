# Retail-ai

A Python retail storefront, shopping assistant, and recommendation system split into five independently deployable FastAPI microservices. MongoDB persists the product catalog and customer preferences. Gemini is optional for AI-generated chat and recommendation ranking.

## Architecture

| Microservice | Responsibility | Data/dependencies |
|---|---|---|
| Gateway | Serves the storefront and proxies the public API | Catalog, recommendation, chatbot, customer services |
| Catalog | Product search and details | MongoDB `retail_catalog` |
| Recommendation | Product ranking by item, category, budget, and customer preferences | Catalog and customer services; optional Gemini |
| Chatbot | Conversational shopping responses | Catalog and recommendation services; optional Gemini |
| Customer | Stores customer shopping preferences | MongoDB `retail_profiles` |

MongoDB is a supporting database, not a sixth application microservice. Catalog and customer data are stored in separate databases so each service owns its data.

## Run locally with Docker Compose

Docker Compose starts the five Python services and MongoDB. From PowerShell:

```powershell
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000) for the storefront or [http://localhost:8000/docs](http://localhost:8000/docs) for the gateway API. Compose stores MongoDB data in the `mongo-data` volume. The local Compose MongoDB instance is for development and is not exposed outside the Compose network.

To enable Gemini, add your key to the ignored root `.env` file:

```dotenv
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Compose passes `.env` to the chatbot and recommendation services. Without a key, both use their local ranking/rule-based behavior. Never commit or share `.env`.

Stop the services with `Ctrl+C`, then run `docker compose down`. Add `-v` only when you intentionally want to erase the local MongoDB data.

## Run tests

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

The tests use fake repositories and mocked inter-service calls; they do not require a running MongoDB or Gemini key.

## API examples

```powershell
curl.exe http://localhost:8000/api/v1/products
curl.exe "http://localhost:8000/api/v1/recommendations?category=home&max_price=60"
curl.exe -X PUT http://localhost:8000/api/v1/customers/customer-1 `
  -H "Content-Type: application/json" `
  -d '{\"preferences\":[\"travel\",\"coffee\"]}'
curl.exe -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{\"message\":\"I need a travel bag under 100\",\"user_id\":\"customer-1\"}'
```

## Build and deploy to Kubernetes

Build and push one image containing the service code:

```powershell
docker build -t <your-registry>/retail-assistant:1.0.0 .
docker push <your-registry>/retail-assistant:1.0.0
```

Update `image: retail-assistant:latest` in `k8s/deployment.yaml` to the pushed image. Create the required MongoDB credentials Secret; use a URL-safe password:

```powershell
kubectl create secret generic mongodb-credentials `
  --from-literal=username=retail `
  --from-literal=password="$([guid]::NewGuid().ToString('N'))"
```

Optionally create a Gemini Secret:

```powershell
kubectl create secret generic retail-assistant-secrets `
  --from-literal=gemini-api-key="$env:GEMINI_API_KEY"
```

Apply the StatefulSet, five application Deployments, and Services:

```powershell
kubectl apply -f k8s/deployment.yaml
kubectl get deployments,statefulsets,services,pods
kubectl port-forward service/retail-gateway 8000:80
```

The cluster needs a default StorageClass for MongoDB's persistent volume claim. The sample MongoDB StatefulSet is a single-node deployment; production should use an appropriately secured and highly available MongoDB setup, managed credentials, backups, and network policies.
