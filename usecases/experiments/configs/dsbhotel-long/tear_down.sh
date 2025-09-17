#/bin/bash

set -a
source .env
set +a

cd ~/uview/usecases/blueprint/examples
./deploy-microservices.sh $APP $BUILD_NAME --down