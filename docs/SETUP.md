# Local development

1. Copy `.env.example` to `.env`; set a long random MEDIA_TOKEN.
2. Install Docker with Compose and run `docker compose up --build`.
3. Test health: `curl http://127.0.0.1:8080/health`.
4. Upload an image: `curl -H "Authorization: Bearer $MEDIA_TOKEN" -F source=ghost -F file=@photo.jpg http://127.0.0.1:8080/process`.
5. Upload a live video using `-F source=live` (120-second maximum).
6. Retrieve output with the same bearer token using the returned download path.

The service binds only to localhost. Never expose it publicly without HTTPS, authentication, request limits and a job queue.
