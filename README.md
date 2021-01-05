# A webapp for submitting email and student id

```
PROJECTID=$(gcloud config get-value project)
```

```
docker build . -t gcr.io/$PROJECTID/signin
```

Test locally
```
docker run --rm -p 8080:8080 gcr.io/$PROJECTID/signin:latest
```

Push image to Google Registry
```
gcloud auth configure-docker
docker push gcr.io/$PROJECTID/signin
```

Alternatively, ultilize Googld Builds to build image
```
gcloud builds submit --tag gcr.io/$PROJECTID/signin
```

Deploy to Google Cloud Run
```
gcloud run deploy --image gcr.io/$PROJECTID/signin --platform managed --max-instances 1
```
