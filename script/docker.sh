docker build -t open-deepwiki:v0.0.18-snapshot .
docker tag open-deepwiki:v0.0.18-snapshot hero-bdc-registry.cn-beijing.cr.aliyuncs.com/business-test/server-feature/open-deepwiki:v0.0.18-snapshot

docker cp .\public deepwiki-open:/app
docker cp .\.next deepwiki-open:/app